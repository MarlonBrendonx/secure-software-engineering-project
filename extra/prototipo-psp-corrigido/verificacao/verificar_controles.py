"""Repete, contra uma API em execução, os ataques que motivaram RS01, R18 e RS08.

Roda igual no protótipo original e no corrigido, para comparar o antes e o depois. Também
confere que os controles que já funcionavam (RS02, RS03 e RS04) continuam valendo.

Uso (com a API no ar e o Redis recém-limpo, para o seed começar do zero):

    PSP_PASSWORD=... PSP_OTP=... backend/.venv/bin/python verificacao/verificar_controles.py \
        --base http://localhost:8000 --rotulo corrigido --saida resultado.json

A senha e o OTP vêm do ambiente, nunca da linha de comando. Os dados são os fictícios do seed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx


# Mesmo esquema de ids do seed (src/infrastructure/persistence/redis/seed.py), sem importar o
# código do protótipo: o script não depende de qual das duas versões está instalada.
def demo_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"psp-prototype/{name}")


CLIENT_ALFA = demo_id("client/alfa")
CLIENT_GAMA = demo_id("client/gama")
ALFA_FIXED = demo_id(f"rule/{CLIENT_ALFA}/101")
ALFA_MULT = demo_id(f"rule/{CLIENT_ALFA}/102")
GAMA_FIXED = demo_id(f"rule/{CLIENT_GAMA}/301")


@dataclass
class Resultado:
    id: str
    requisito: str
    ataque: str
    esperado: str
    obtido: int
    atende: bool


def payload(client: UUID, rule: UUID, **extra: Any) -> dict[str, Any]:
    body = {
        "client_uuid": str(client),
        "service_rule_uuid": str(rule),
        "reference_year": 2026,
        "reference_month": 9,
        "billing_year": 2026,
        "billing_month": 9,
        "total_value": "1000.00",
    }
    body.update(extra)
    return body


class Api:
    def __init__(self, base: str, password: str, otp: str) -> None:
        self.base = base.rstrip("/")
        self.password = password
        self.otp = otp

    def login(self, username: str, *, mfa: bool) -> dict[str, str]:
        body = {"username": username, "password": self.password}
        if mfa:
            body["otp"] = self.otp
        # Cliente novo e descartado: o teste usa só o Bearer, sem o cookie de sessão.
        with httpx.Client(base_url=self.base, timeout=10) as c:
            r = c.post("/v1/auth/login", json=body)
        r.raise_for_status()
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def call(self, method: str, path: str, headers: dict[str, str], **kw: Any) -> httpx.Response:
        with httpx.Client(base_url=self.base, timeout=10) as c:
            return c.request(method, path, headers=headers, **kw)

    def create(self, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        r = self.call("POST", "/v1/billing/items", headers, json=body)
        if r.status_code != 201:
            sys.exit(f"Falha ao preparar o cenário (criar lançamento): {r.status_code} {r.text}")
        return r.json()["data"]

    def status(self, item: str, new: str, headers: dict[str, str]) -> int:
        return self.call(
            "PATCH", f"/v1/billing/items/{item}/status", headers, json={"new_status": new}
        ).status_code

    def version(self, item: str, headers: dict[str, str]) -> int:
        return self.call("GET", f"/v1/billing/items/{item}", headers).json()["data"]["version"]


def executar(api: Api) -> list[Resultado]:
    out: list[Resultado] = []
    analyst = api.login("analyst", mfa=False)
    admin = api.login("admin", mfa=True)

    # V-01 e V-02 (RS01): alterar e excluir um lançamento já enviado para aprovação.
    item = api.create(analyst, payload(CLIENT_ALFA, ALFA_FIXED))["uuid"]
    assert api.status(item, "ManagementApproval", analyst) == 200
    r = api.call(
        "PATCH",
        f"/v1/billing/items/{item}",
        analyst,
        json={"version": api.version(item, analyst), "notes": "alterado depois do envio"},
    )
    out.append(Resultado("V-01", "RS01", "PATCH em lançamento enviado para aprovação",
                         "422", r.status_code, r.status_code == 422))
    item2 = api.create(analyst, payload(CLIENT_ALFA, ALFA_MULT, quantity="10"))["uuid"]
    assert api.status(item2, "ManagementApproval", analyst) == 200
    r = api.call("DELETE", f"/v1/billing/items/{item2}", analyst)
    out.append(Resultado("V-02", "RS01", "DELETE em lançamento enviado para aprovação",
                         "422", r.status_code, r.status_code == 422))

    # V-03 (RS01): a mudança legítima passa a ser pela transição "reabrir".
    code = api.status(item, "New", analyst)
    out.append(Resultado("V-03", "RS01", "Reabrir lançamento enviado (status New)",
                         "200", code, code == 200))

    # V-04 (R18): admin cria, envia e tenta aprovar o próprio lançamento.
    own = api.create(admin, payload(CLIENT_GAMA, GAMA_FIXED))["uuid"]
    assert api.status(own, "ManagementApproval", admin) == 200
    code = api.status(own, "FinancialReview", admin)
    out.append(Resultado("V-04", "R18", "Admin aprova o próprio lançamento",
                         "403", code, code == 403))

    # V-05 (RS03, regressão): analista lê lançamento de cliente fora do escopo.
    r = api.call("GET", f"/v1/billing/items/{own}", analyst)
    out.append(Resultado("V-05", "RS03", "Analista lê lançamento de cliente fora do escopo",
                         "404", r.status_code, r.status_code == 404))

    # V-06 (RS02, regressão): admin sem segundo fator tenta escrever regra de serviço.
    admin_pwd = api.login("admin", mfa=False)
    r = api.call("POST", f"/v1/registry/clients/{CLIENT_ALFA}/service-rules", admin_pwd, json={})
    out.append(Resultado("V-06", "RS02", "Admin sem MFA escreve regra de serviço",
                         "401", r.status_code, r.status_code == 401))

    # V-07 (RS04, regressão): token com alg=none.
    header = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0"  # {"alg":"none","typ":"JWT"}
    claims = "eyJzdWIiOiJhZG1pbiIsInNpZCI6IngiLCJ0eXBlIjoiYWNjZXNzIn0"
    r = api.call("GET", "/v1/registry/clients/summary",
                 {"Authorization": f"Bearer {header}.{claims}."})
    out.append(Resultado("V-07", "RS04", "Token com alg=none",
                         "401", r.status_code, r.status_code == 401))

    # V-08 (RS08, não implementado): requisição induzida por outro site, só com o cookie.
    with httpx.Client(base_url=api.base, timeout=10) as browser:
        login = browser.post(
            "/v1/auth/login", json={"username": "analyst", "password": api.password}
        )
        login.raise_for_status()
        data = browser.post(
            "/v1/billing/items", json=payload(CLIENT_ALFA, demo_id(f"rule/{CLIENT_ALFA}/103"),
                                              base_value="1000.00")
        )
        if data.status_code != 201:
            sys.exit(f"Falha ao preparar o cenário V-08: {data.status_code} {data.text}")
        target = data.json()["data"]
        r = browser.patch(
            f"/v1/billing/items/{target['uuid']}",
            json={"version": target["version"], "notes": "csrf"},
            headers={"Origin": "https://site-malicioso.example"},
        )
    out.append(Resultado("V-08", "RS08", "PATCH só com cookie e Origin de outro site",
                         "403", r.status_code, r.status_code == 403))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--rotulo", required=True, help="original ou corrigido")
    parser.add_argument("--saida", required=True)
    args = parser.parse_args()

    password, otp = os.environ.get("PSP_PASSWORD"), os.environ.get("PSP_OTP")
    if not password or not otp:
        sys.exit("Defina PSP_PASSWORD e PSP_OTP no ambiente.")

    resultados = executar(Api(args.base, password, otp))
    relatorio = {
        "prototipo": args.rotulo,
        "base": args.base,
        "executado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "resultados": [asdict(r) for r in resultados],
    }
    with open(args.saida, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

    print(f"Protótipo: {args.rotulo}  ({args.base})")
    for r in resultados:
        marca = "ATENDE" if r.atende else "NÃO ATENDE"
        print(f"  {r.id} {r.requisito:<5} esperado {r.esperado}  obtido {r.obtido}  {marca:<10} {r.ataque}")


if __name__ == "__main__":
    main()
