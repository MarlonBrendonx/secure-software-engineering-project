"""Testes de cadastros, lançamentos, aprovação, planilha ERP e auditoria (critérios 7 a 9)."""
import pytest

from app.models import Papel, TipoAcao

from .conftest import logs


@pytest.fixture
def perfis(logado):
    return {
        "admin": logado(Papel.ADMINISTRADOR, "admin"),
        "op": logado(Papel.OPERACIONAL, "op"),
        "gestor": logado(Papel.GESTOR, "gestor"),
        "auditor": logado(Papel.AUDITOR, "auditor"),
    }


@pytest.fixture
def base(perfis):
    """Cadastros mínimos feitos pelo administrador."""
    a = perfis["admin"]
    emp = a.post("/api/cadastros/empresas", json={"nome": "Empresa A", "cnpj": "11.111.111/0001-11"}).json()
    cli = a.post("/api/cadastros/clientes", json={"nome": "Cliente X", "empresa_id": emp["id"]}).json()
    cli2 = a.post("/api/cadastros/clientes", json={"nome": "Cliente Y", "empresa_id": emp["id"]}).json()
    ctr = a.post("/api/cadastros/contratos", json={"nome": "Contrato X", "numero": "C-001", "cliente_id": cli["id"]}).json()
    regra = a.post("/api/cadastros/regras-servico",
                   json={"nome": "Consulta", "contrato_id": ctr["id"], "valor_unitario": "12.50"}).json()
    return {"cliente": cli, "cliente2": cli2, "contrato": ctr, "regra": regra}


def _lancar(op, base, quantidade="10", periodo="2026-09"):
    return op.post("/api/lancamentos", json={"cliente_id": base["cliente"]["id"], "periodo": periodo,
                                             "regra_servico_id": base["regra"]["id"], "quantidade": quantidade})


# --- Cadastros ----------------------------------------------------------------
def test_administrador_cadastra_todas_as_entidades(perfis):
    a = perfis["admin"]
    for slug, corpo in [
        ("segmentos", {"nome": "Saúde"}), ("programas", {"nome": "P1"}), ("grupos-economicos", {"nome": "G1"}),
        ("centros-custo", {"nome": "CC", "codigo": "100"}), ("unidades-negocio", {"nome": "UN"}),
        ("fornecedores", {"nome": "F1"}), ("empresas", {"nome": "E1"}),
    ]:
        r = a.post(f"/api/cadastros/{slug}", json=corpo)
        assert r.status_code == 201, (slug, r.text)
    assert len(a.get("/api/cadastros").json()) == 10


def test_cadastro_recusa_campos_desconhecidos_e_referencias_invalidas(perfis):
    a = perfis["admin"]
    assert a.post("/api/cadastros/empresas", json={"nome": "E", "ativo": False, "id": 99}).status_code == 422
    assert a.post("/api/cadastros/clientes", json={"nome": "C", "empresa_id": 999}).status_code == 422
    assert a.post("/api/cadastros/inexistente", json={}).status_code == 404


def test_cnpj_duplicado_e_conflito(perfis):
    a = perfis["admin"]
    a.post("/api/cadastros/empresas", json={"nome": "E1", "cnpj": "1"})
    assert a.post("/api/cadastros/empresas", json={"nome": "E2", "cnpj": "1"}).status_code == 409


# --- Critério 9: edição e remoção ficam registradas ---------------------------
def test_edicao_e_remocao_de_cadastro_geram_auditoria(perfis, base):
    a = perfis["admin"]
    cid = base["cliente"]["id"]
    corpo = {"nome": "Cliente X Ltda", "empresa_id": base["cliente"]["empresa_id"]}
    assert a.put(f"/api/cadastros/clientes/{cid}", json=corpo).status_code == 200
    assert a.delete(f"/api/cadastros/clientes/{base['cliente2']['id']}").status_code == 204

    edicao = logs(TipoAcao.EDICAO, entidade="clientes", entidade_id=str(cid))[0]
    assert edicao.login == "admin" and edicao.ip and edicao.data_hora
    assert edicao.detalhes["alteracoes"]["nome"] == {"antes": "Cliente X", "depois": "Cliente X Ltda"}
    remocao = logs(TipoAcao.REMOCAO, entidade="clientes")[0]
    assert remocao.detalhes["registro"]["nome"] == "Cliente Y"
    # Remoção lógica: some da lista, mas o registro continua existindo
    nomes = [c["nome"] for c in a.get("/api/cadastros/clientes").json()["itens"]]
    assert "Cliente Y" not in nomes
    assert a.get(f"/api/cadastros/clientes/{base['cliente2']['id']}").json()["ativo"] is False


# --- Critérios 7 e 8: escopos separados e tentativa registrada ---------------
def test_administrador_nao_faz_lancamento_e_a_tentativa_fica_registrada(perfis, base):
    r = _lancar(perfis["admin"], base)
    assert r.status_code == 403
    negado = logs(TipoAcao.ACESSO_NEGADO, login="admin")
    assert negado and negado[0].detalhes["rota"] == "/api/lancamentos" and negado[0].ip


def test_operacional_nao_edita_cadastro_e_a_tentativa_fica_registrada(perfis, base):
    op = perfis["op"]
    assert op.get("/api/cadastros/clientes").status_code == 200  # pode consultar
    r = op.put(f"/api/cadastros/clientes/{base['cliente']['id']}", json={"nome": "hack", "empresa_id": 1})
    assert r.status_code == 403
    assert op.post("/api/cadastros/empresas", json={"nome": "x"}).status_code == 403
    assert op.delete(f"/api/cadastros/clientes/{base['cliente']['id']}").status_code == 403
    assert len(logs(TipoAcao.ACESSO_NEGADO, login="op")) == 3


@pytest.mark.parametrize("perfil,metodo,rota", [
    ("op", "post", "/api/lancamentos/1/aprovar"),
    ("admin", "post", "/api/lancamentos/1/aprovar"),
    ("gestor", "post", "/api/lancamentos"),
    ("gestor", "post", "/api/exportacoes-erp"),
    ("admin", "post", "/api/exportacoes-erp"),
    ("op", "get", "/api/usuarios"),
    ("gestor", "get", "/api/auditoria"),
    ("admin", "get", "/api/auditoria"),
    ("auditor", "post", "/api/cadastros/empresas"),
])
def test_matriz_de_permissoes(perfis, perfil, metodo, rota):
    assert getattr(perfis[perfil], metodo)(rota, **({"json": {}} if metodo == "post" else {})).status_code == 403


# --- Lançamentos e aprovação --------------------------------------------------
def test_valor_e_calculado_no_servidor(perfis, base):
    r = perfis["op"].post("/api/lancamentos", json={
        "cliente_id": base["cliente"]["id"], "periodo": "2026-09", "regra_servico_id": base["regra"]["id"],
        "quantidade": "3", "valor_total": "999999", "valor_unitario": "1"})
    assert r.status_code == 201
    assert r.json()["valor_total"] == "37.50" and r.json()["valor_unitario"] == "12.5000"


def test_regra_de_outro_cliente_e_recusada(perfis, base):
    r = perfis["op"].post("/api/lancamentos", json={"cliente_id": base["cliente2"]["id"], "periodo": "2026-09",
                                                    "regra_servico_id": base["regra"]["id"], "quantidade": "1"})
    assert r.status_code == 422


def test_periodo_invalido_e_duplicidade(perfis, base):
    assert _lancar(perfis["op"], base, periodo="2026-13").status_code == 422
    assert _lancar(perfis["op"], base).status_code == 201
    assert _lancar(perfis["op"], base).status_code == 409


def test_fluxo_lancar_submeter_reprovar_corrigir_aprovar(perfis, base):
    op, g = perfis["op"], perfis["gestor"]
    lid = _lancar(op, base).json()["id"]
    assert op.post(f"/api/lancamentos/{lid}/submeter").json()["status"] == "SUBMETIDO"
    assert op.put(f"/api/lancamentos/{lid}", json={"cliente_id": base["cliente"]["id"], "periodo": "2026-09",
                                                  "regra_servico_id": base["regra"]["id"], "quantidade": "1"}).status_code == 409
    assert [l["id"] for l in g.get("/api/aprovacoes/pendentes").json()] == [lid]

    assert g.post(f"/api/lancamentos/{lid}/reprovar", json={}).status_code == 422  # motivo obrigatório
    assert g.post(f"/api/lancamentos/{lid}/reprovar", json={"observacao": "Quantidade errada"}).json()["status"] == "REPROVADO"

    r = op.put(f"/api/lancamentos/{lid}", json={"cliente_id": base["cliente"]["id"], "periodo": "2026-09",
                                               "regra_servico_id": base["regra"]["id"], "quantidade": "8"})
    assert r.json()["valor_total"] == "100.00" and r.json()["status"] == "RASCUNHO"
    op.post(f"/api/lancamentos/{lid}/submeter")
    assert g.post(f"/api/lancamentos/{lid}/aprovar").json()["status"] == "APROVADO"

    assert op.delete(f"/api/lancamentos/{lid}").status_code == 409  # aprovado não se remove
    hist = op.get(f"/api/lancamentos/{lid}").json()["historico"]
    assert [h["decisao"] for h in hist] == ["REPROVADO", "APROVADO"]
    edicao = logs(TipoAcao.EDICAO, entidade="lancamentos")[0]
    assert edicao.detalhes["alteracoes"]["quantidade"] == {"antes": "10.0000", "depois": "8"}
    assert logs(TipoAcao.APROVACAO, login="gestor") and logs(TipoAcao.REPROVACAO, login="gestor")


def test_remocao_de_rascunho_fica_registrada(perfis, base):
    lid = _lancar(perfis["op"], base).json()["id"]
    assert perfis["op"].delete(f"/api/lancamentos/{lid}").status_code == 204
    assert logs(TipoAcao.REMOCAO, entidade="lancamentos", entidade_id=str(lid))[0].detalhes["registro"]["valor_total"] == "125.00"


# --- Planilha ERP -------------------------------------------------------------
def test_planilha_erp_contem_so_aprovados_e_download_e_registrado(perfis, base):
    op, g, a = perfis["op"], perfis["gestor"], perfis["admin"]
    regra2 = a.post("/api/cadastros/regras-servico", json={"nome": "Exame", "contrato_id": base["contrato"]["id"],
                                                          "valor_unitario": "100"}).json()
    aprovado = _lancar(op, base, "4").json()["id"]
    op.post("/api/lancamentos", json={"cliente_id": base["cliente"]["id"], "periodo": "2026-09",
                                      "regra_servico_id": regra2["id"], "quantidade": "1"})  # fica em rascunho
    op.post(f"/api/lancamentos/{aprovado}/submeter")
    g.post(f"/api/lancamentos/{aprovado}/aprovar")

    assert op.post("/api/exportacoes-erp", json={"periodo": "2026-08"}).status_code == 422
    exp = op.post("/api/exportacoes-erp", json={"periodo": "2026-09"}).json()
    assert exp["quantidade_lancamentos"] == 1 and exp["valor_total"] == "50.00"

    arq = op.get(f"/api/exportacoes-erp/{exp['id']}/arquivo")
    assert arq.status_code == 200 and "attachment" in arq.headers["content-disposition"]
    linhas = arq.text.lstrip("﻿").strip().split("\n")
    assert len(linhas) == 2 and linhas[1].endswith(";50.00") and "C-001" in linhas[1]
    assert logs(TipoAcao.EXPORTACAO_ERP, login="op") and logs(TipoAcao.DOWNLOAD_ERP, login="op")


# --- Auditoria e usuários -----------------------------------------------------
def test_auditor_consulta_filtrando_por_usuario_perfil_e_tipo(perfis, base):
    aud = perfis["auditor"]
    _lancar(perfis["admin"], base)  # gera ACESSO_NEGADO
    r = aud.get("/api/auditoria", params={"tipo_acao": "ACESSO_NEGADO"}).json()
    assert r["total"] == 1 and r["itens"][0]["login"] == "admin"
    assert aud.get("/api/auditoria", params={"papel": "ADMINISTRADOR", "tipo_acao": "CRIACAO"}).json()["total"] == 5
    logins = aud.get("/api/auditoria", params={"tipo_acao": "LOGIN_OK"}).json()
    assert {i["login"] for i in logins["itens"]} == {"admin", "op", "gestor", "auditor"}
    csv = aud.get("/api/auditoria/exportar", params={"login": "admin"})
    assert csv.status_code == 200 and "ACESSO_NEGADO" in csv.text


def test_auditoria_nao_tem_rota_de_alteracao(perfis):
    aud = perfis["auditor"]
    assert aud.delete("/api/auditoria").status_code == 405
    assert aud.put("/api/auditoria", json={}).status_code == 405


def test_gestao_de_usuarios_pelo_administrador(perfis):
    a = perfis["admin"]
    novo = a.post("/api/usuarios", json={"login": "Novo.Usuario", "nome": "Novo", "papel": "OPERACIONAL"})
    assert novo.status_code == 201 and novo.json()["login"] == "novo.usuario"
    assert a.post("/api/usuarios", json={"login": "novo.usuario", "nome": "X", "papel": "GESTOR"}).status_code == 409
    eu = next(u for u in a.get("/api/usuarios").json() if u["login"] == "admin")
    assert a.put(f"/api/usuarios/{eu['id']}", json={"ativo": False}).status_code == 400
    r = a.put(f"/api/usuarios/{novo.json()['id']}", json={"papel": "GESTOR"})
    assert r.json()["papel"] == "GESTOR"
    assert logs(TipoAcao.EDICAO, entidade="usuarios")[0].detalhes["alteracoes"]["papel"] == {"antes": "OPERACIONAL", "depois": "GESTOR"}


def test_mudanca_de_papel_derruba_a_sessao(perfis):
    op, a = perfis["op"], perfis["admin"]
    uid = next(u for u in a.get("/api/usuarios").json() if u["login"] == "op")["id"]
    a.put(f"/api/usuarios/{uid}", json={"papel": "GESTOR"})
    assert op.get("/api/auth/sessao").status_code == 401
