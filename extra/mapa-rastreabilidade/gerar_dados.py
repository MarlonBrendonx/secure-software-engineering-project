#!/usr/bin/env python3
"""Gera `dados.json` e `index.html` do mapa de rastreabilidade.

Ameaças, riscos, estágios e risco residual são lidos das tabelas dos `.md` em
`docs/`, para o mapa seguir a documentação. Os vínculos entre requisitos,
decisões, controles, verificações, regras de detecção e quality gates não
estão em tabela única, então ficam declarados abaixo, cada um com a fonte.

Uso (a partir da raiz do repositório):
    python3 extra/mapa-rastreabilidade/gerar_dados.py
"""

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
SAIDA = Path(__file__).resolve().parent


def linhas_de_tabela(arquivo: str, cabecalho: str) -> list[list[str]]:
    """Devolve as linhas da primeira tabela cujo cabeçalho começa com `cabecalho`."""
    texto = (RAIZ / arquivo).read_text(encoding="utf-8").splitlines()
    inicio = next(i for i, l in enumerate(texto) if l.startswith(cabecalho))
    linhas = []
    for linha in texto[inicio + 2 :]:
        if not linha.startswith("|"):
            break
        linhas.append([c.strip() for c in linha.strip().strip("|").split("|")])
    return linhas


def limpar(txt: str) -> str:
    return re.sub(r"\*\*|`", "", txt).strip()


# --- Lidos da documentação --------------------------------------------------

def ler_ameacas() -> list[dict]:
    linhas = linhas_de_tabela("docs/etapa-1/etapa-1-ameacas-stride.md", "| ID ")
    return [
        {
            "id": l[0],
            "stride": l[1],
            "ativos": l[3],
            "titulo": limpar(l[4]),
            "entrada": limpar(l[5]),
            "controle_existente": limpar(l[7]),
        }
        for l in linhas
    ]


def ler_riscos() -> list[dict]:
    reg = linhas_de_tabela("docs/etapa-2/etapa-2-criterios-e-registro.md", "| ID  | Origem")
    plano = {
        l[0]: l
        for l in linhas_de_tabela("docs/etapa-2/etapa-2-plano-e-residual.md", "| Risco | Estratégia")
    }
    resid = {
        l[0]: l
        for l in linhas_de_tabela("docs/etapa-2/etapa-2-plano-e-residual.md", "| Risco | Nível inicial")
    }
    riscos = []
    for l in reg:
        rid = l[0]
        origem = re.findall(r"T\d+[ab]?", l[1])
        residual = resid.get(rid)
        riscos.append(
            {
                "id": rid,
                "titulo": limpar(l[2]),
                "condicao": limpar(l[3]),
                "p": int(l[4]),
                "i": int(l[5]),
                "pontuacao": int(l[6]),
                "nivel": limpar(l[7]),
                "ameacas": origem,
                "estrategia": plano[rid][1],
                "estagio": int(plano[rid][2]),
                "responsavel": plano[rid][3],
                "residual": (
                    {"calculo": residual[3].replace(" ", ""), "nivel": residual[4]}
                    if residual
                    else None
                ),
            }
        )
    return riscos


# --- Declarados à mão, com a fonte de cada vínculo --------------------------

# docs/etapa-3/etapa-3-requisitos.md e etapa-3-decisoes.md (D0x atende RS0x)
REQUISITOS = [
    ("RS01", "D01", ["R01", "R18"], "Depois do envio para aprovação, só a máquina de estados muda o lançamento",
     "Decisão D01: tratar a máquina de estados como única via de mudança. Inclui a segregação de funções de R18: quem criou, enviou ou alterou não aprova."),
    ("RS02", "D02", ["R02"], "MFA obrigatório para administrador e gestor, conferido no SSO e na API",
     "Decisão D02: exigir o MFA no SSO e conferi-lo também na API."),
    ("RS03", "D03", ["R03"], "Autorização por recurso no servidor (cliente, período e responsável)",
     "Decisão D03: autorizar por recurso, na camada de casos de uso. Negação devolve 404, igual ao recurso inexistente."),
    ("RS04", "D04", ["R06", "R07"], "Token assinado com chave assimétrica do cofre e validado de forma estrita",
     "Decisão D04: assinar o token de sessão com chave assimétrica guardada no cofre e validar o token de forma estrita."),
    ("RS05", "D05", ["R26"], "Auditoria gravada na mesma transação da operação",
     "Decisão D05: gravar a auditoria na mesma transação e entregar os eventos por uma outbox."),
    ("RS06", "D06", ["R28"], "Guards negam por padrão e toda rota declara sua política",
     "Decisão D06: fazer os guards negarem por padrão e exigir política de acesso declarada em toda rota."),
    ("RS07", "D07", ["R23"], "Carga do ERP com manifesto assinado e campos neutralizados",
     "Decisão D07: assinar a carga do ERP com um manifesto e conferi-la antes da importação."),
    ("RS08", "D08", ["R29"], "Proteção anti-CSRF antes dos guards",
     "Decisão D08: proteger as rotas autenticadas por cookie contra CSRF antes dos guards."),
]

# docs/etapa-3/etapa-3-diagrama.md, seção 2 (controles posicionados no diagrama)
CONTROLES = {
    "C1": "Keycloak e OAuth Service: segundo fator no SSO",
    "C2": "Guards da API: recusa token privilegiado sem MFA",
    "C3": "Casos de uso: permissão sobre o recurso",
    "C4": "Máquina de estados (billing_status)",
    "C5": "Gerador da carga do ERP: só a versão aprovada",
    "C6": "Tabela audit_logs",
    "C7": "Monitoramento e alertas",
    "C8": "Pipeline de CI com testes de segurança",
    "C9": "Emissor do token e cofre (KMS)",
    "C10": "Guards: validação estrita do token",
    "C11": "Auditoria e outbox na mesma transação",
    "C12": "Guards: negar por padrão",
    "C13": "Carga do ERP: manifesto assinado",
    "C14": "Middleware anti-CSRF",
}
# C6, C7 e C8 servem a quase todos os requisitos; o mapa os trata como transversais.
TRANSVERSAIS = {"C6", "C7", "C8"}

# Tabela "Rastreabilidade" do artigo (artigo.tex, Tabela rastreabilidade)
REQ_CONTROLES = {
    "RS01": ["C4", "C5", "C6", "C7", "C8"],
    "RS02": ["C1", "C2", "C7"],
    "RS03": ["C3", "C6", "C7", "C8"],
    "RS04": ["C9", "C10", "C7", "C8"],
    "RS05": ["C11", "C6", "C7", "C8"],
    "RS06": ["C12", "C6", "C7", "C8"],
    "RS07": ["C13", "C5", "C7", "C8"],
    "RS08": ["C14", "C6", "C7", "C8"],
}

# Vulnerabilidade catalogada por requisito (artigo.tex, Tabela vulnerabilidades)
CWE = {
    "RS01": "CWE-841 · OWASP A06 Insecure Design",
    "RS02": "CWE-308 · OWASP A07 Authentication Failures",
    "RS03": "CWE-639, CWE-862 · OWASP A01 Broken Access Control",
    "RS04": "CWE-522, CWE-347 · OWASP A04 Cryptographic Failures",
    "RS05": "CWE-778, CWE-223 · OWASP A09 Logging and Alerting Failures",
    "RS06": "CWE-636, CWE-755 · OWASP A10 Mishandling of Exceptional Conditions",
    "RS07": "CWE-345, CWE-353, CWE-1236 · OWASP A08 Data Integrity Failures",
    "RS08": "CWE-352 · OWASP A01 Broken Access Control",
}

# Verificações: testes do protótipo corrigido e ataques V-01..V-08
# (docs/prototipo-corrigido/verificacao-das-correcoes.md e artigo.tex, Tabela verificacao).
# situacao: ok = passa no protótipo corrigido; parcial; ausente = sem implementação.
VERIFICACOES = [
    ("VF-RS01", "RS01: alteração após o envio", "ok", ["C4"],
     "V-01 PATCH 200→422 · V-02 DELETE 204→422 · V-03 reabrir 422→200",
     "test_rs01_patch_e_delete_apos_envio_sao_recusados, test_rs01_reabrir_exige_novo_envio_e_nova_aprovacao, test_rs01_aprovado_nao_reabre"),
    ("VF-R18", "R18: autoaprovação recusada", "ok", ["C4"],
     "V-04 admin aprova o próprio lançamento 200→403",
     "test_r18_admin_nao_aprova_o_proprio_lancamento, test_r18_lote_com_autoaprovacao_nao_muda_nenhum_item"),
    ("VF-RS02", "RS02: token sem MFA recusado", "ok", ["C1", "C2"],
     "V-06 escrita privilegiada sem MFA: 401",
     "test_ts04_token_de_gestor_sem_mfa_e_recusado, test_claim_mfa_forjado_nao_basta_sem_mfa_na_sessao"),
    ("VF-RS03", "RS03: recurso fora do escopo", "ok", ["C3"],
     "V-05 leitura de cliente fora do escopo: 404",
     "test_rotas_por_cliente_e_faturamento_negam_com_404_identico_ao_inexistente, test_escopo_por_periodo"),
    ("VF-RS04", "RS04: validação do token (chave simétrica)", "parcial", ["C10"],
     "V-07 token com alg none: 401. Assinatura assimétrica e cofre não implementados.",
     "test_token_invalido_e_recusado; test_rs04_assinatura_assimetrica está como xfail"),
    ("VF-RS05", "RS05: auditoria na mesma transação", "ok", ["C11"],
     "Falha simulada na auditoria desfaz a operação (só para lançamentos)",
     "test_rs05_falha_na_auditoria_desfaz_a_operacao, test_rs05_alteracao_grava_item_timeline_e_auditoria_juntos"),
    ("VF-RS06", "RS06: toda rota declara política", "ok", ["C12"],
     "Teste enumera as rotas registradas; guard nega por padrão",
     "test_toda_rota_declara_politica_de_acesso, test_sem_token_e_negado"),
    ("VF-RS07", "RS07: carga do ERP", "ausente", ["C13"],
     "Sem protótipo da carga do ERP", ""),
    ("VF-RS08", "RS08: anti-CSRF", "ausente", ["C14"],
     "V-08 requisição só com cookie, de outra origem: 200 (esperado 403)",
     "test_rs08_requisicao_so_com_cookie_e_origem_externa_e_recusada está como xfail"),
    # Achados do ZAP e do Dependency-Check (docs/etapa-5/etapa-5-retest-autenticado.md)
    ("VF-V01", "Achado V01: refresh token reaceito", "achado", ["C10"],
     "ZAP, retest autenticado: POST /v1/auth/refresh. Correção proposta no código da Etapa 6 (rotação do refresh), ainda não aplicada aos protótipos.", ""),
    ("VF-V02", "Achado V02: access_token no corpo", "achado", ["C10"],
     "ZAP, retest autenticado: POST /v1/auth/login. Correção proposta: token só no cookie HttpOnly.", ""),
    ("VF-V03", "Achado V03: PyJWT com CVE", "achado", [],
     "Dependency-Check: dependência do backend. Correção proposta: atualizar o PyJWT.", ""),
]
# Achados da Etapa 5 ligados às ameaças (etapa-5-verificacao-vulnerabilidades.md)
ACHADO_AMEACA = {"VF-V01": ["T33"], "VF-V02": ["T16"], "VF-V03": ["T37"]}

# Regras de detecção (docs/etapa-6/etapa-6-deteccao-de-intrusoes.md, seções "Situação das
# regras no protótipo" e "Rastreabilidade"). São duas situações diferentes e o mapa não as mistura:
#   prototipo: o que existe hoje nos protótipos
#   proposta:  o que existiria com o código da Etapa 6, que NÃO foi aplicado a nenhum protótipo
# (id, título, riscos, requisito, controle que produz o evento, severidade,
#  situação no protótipo, nota do protótipo, situação com o código proposto)
DETECCOES = [
    ("D01", "Falhas repetidas no segundo fator", ["R02"], "RS02", "C2", "Alta",
     "ok", "SecurityMonitor dispara mfa_falhas_repetidas; teste test_falhas_repetidas_de_mfa_geram_alerta.", "ok"),
    ("D02", "Negações repetidas por escopo", ["R03", "R05"], "RS03", "C3", "Alta",
     "parcial", "Alerta implementado, mas sem teste do alerta.", "ok"),
    ("D03", "Falhas de login repetidas", ["R02"], "RS02", "C1", "Média",
     "ausente", "login_falha é registrado na auditoria, sem regra de alerta.", "ok"),
    ("D04", "Login privilegiado suspeito", ["R02"], "RS02", "C1", "Crítica",
     "ausente", "login_sucesso é registrado, sem regra de alerta.", "ok"),
    ("D05", "Reuso de refresh token", ["R25"], "RS04", "C10", "Alta",
     "ausente", "Evento não gerado: falta a rotação do refresh (achado V01).", "ok"),
    ("D06", "Token recusado ou chave usada fora do emissor", ["R06", "R07"], "RS04", "C10", "Crítica ou Média",
     "ausente", "O sinal fica só na resposta HTTP 401.", "parcial"),
    ("D07", "Alteração após o envio ou autoaprovação", ["R01", "R18"], "RS01", "C4", "Alta",
     "ausente", "No original o evento não é gerado. No corrigido, autoaprovacao_negada é registrada, sem regra de alerta.", "parcial"),
    ("D08", "Regra de serviço alterada", ["R09"], None, None, "Média",
     "ausente", "Os eventos de regra de serviço são registrados, sem correlação.", "parcial"),
    ("D09", "Consulta ou exportação em volume", ["R05"], "RS03", "C3", "Média",
     "ausente", "A leitura não é registrada.", "ausente"),
    ("D10", "Falha na verificação de acesso (503)", ["R28"], "RS06", "C12", "Alta",
     "ausente", "O sinal fica só no log.", "ausente"),
    ("D11", "Falha de auditoria ou da outbox", ["R26", "R08"], "RS05", "C11", "Crítica",
     "ausente", "Não há outbox, então o evento não é gerado.", "ausente"),
    ("D12", "Recusa por origem ou token anti-CSRF", ["R29", "R17"], "RS08", "C14", "Média",
     "ausente", "O sinal fica só no log (WebSocket 4403).", "parcial"),
    ("D13", "Limite de requisições excedido (429)", ["R11", "R16"], None, None, "Baixa",
     "ausente", "O sinal fica só na resposta HTTP 429.", "ok"),
    ("D14", "Divergência na carga do ERP", ["R23"], "RS07", "C13", "Crítica",
     "ausente", "Não há carga do ERP no protótipo.", "ausente"),
]

# Quality gates (docs/etapa-7/etapa-7-devsecops.md). Todos são propostas.
GATES = [
    ("QG1", "Riscos prioritários identificados e com responsável"),
    ("QG2", "Cada requisito rastreado a um risco"),
    ("QG3", "PR aprovado, lint e tipos limpos, sem segredo"),
    ("QG4", "Todos os testes de segurança aprovados"),
    ("QG5", "Sem segredo e sem CVE crítica ou alta sem análise"),
    ("QG6", "Nenhum alerta alto ou crítico sem análise"),
    ("QG7", "QG3 a QG6 aprovados e produção autorizada"),
    ("QG8", "Incidentes tratados e lições registradas"),
]



# Rótulos curtos, só para caber no desenho. O texto completo aparece no painel de detalhe.
ROTULOS = {
    # ameaças (docs/etapa-1/etapa-1-ameacas-stride.md)
    "T01": "Alteração de lançamentos", "T02": "Conta privilegiada capturada",
    "T03": "Leitura sem permissão", "T04": "Vazamento de lançamentos",
    "T05": "Perda do timeline", "T06": "Regra de serviço alterada",
    "T07": "Acesso indevido a anexos", "T08": "Vazamento de anexos",
    "T09": "Acesso indevido a CNPJs", "T10": "Vazamento de CNPJs",
    "T11": "Acesso a e-mails de aprovadores", "T12": "Vazamento de e-mails",
    "T13": "Código de cálculo alterado", "T14a": "Saturação da máquina de estados",
    "T14b": "Guard que falha aberto", "T15": "Vazamento do JWT_SECRET",
    "T16": "Token forjado com o segredo", "T17": "Vazamento da chave interna",
    "T18": "Callback interno forjado", "T19": "Acesso direto ao storage",
    "T20": "Ataque ao PostgreSQL", "T21": "E-mail com remetente falso",
    "T22": "Vazamento pelo WebSocket", "T23": "Sobrecarga do EventBus",
    "T24": "Admin aprova o próprio", "T25": "Injeção de SQL no Oracle",
    "T26": "IDOR em lançamento", "T27": "CSRF em rota mutante",
    "T28": "Provedor local em produção", "T29": "Anexo malicioso",
    "T30": "Injeção de fórmula na carga", "T31": "Carga do ERP adulterada",
    "T32": "Ambientes no mesmo banco", "T33": "Reuso de refresh token",
    "T34": "Auditoria perdida", "T35": "Aprovador nega autoria",
    "T36": "E-mail ao destinatário errado", "T37": "Dependência maliciosa",
    # riscos (docs/etapa-2/etapa-2-criterios-e-registro.md)
    "R01": "Alteração de lançamentos", "R02": "Captura de conta privilegiada",
    "R03": "Acesso a dados restritos", "R04": "Acesso direto aos anexos",
    "R05": "Exfiltração em volume", "R06": "Vazamento do JWT_SECRET",
    "R07": "Token forjado com o segredo", "R08": "Timeline adulterada",
    "R09": "Regra de serviço alterada", "R10": "Motor de cálculo adulterado",
    "R11": "Sobrecarga da máquina", "R12": "Vazamento do segredo Celery",
    "R13": "Callback interno forjado", "R14": "PostgreSQL indisponível",
    "R15": "E-mail malicioso da empresa", "R16": "Sobrecarga do EventBus",
    "R17": "Inscrição indevida no canal", "R18": "Autoaprovação do admin",
    "R19": "Injeção de SQL no Oracle", "R20": "Provedor local em produção",
    "R21": "QA alcança produção", "R22": "Anexo malicioso",
    "R23": "Carga do ERP adulterada", "R24": "Desvio de e-mail de aprovação",
    "R25": "Reuso de refresh token", "R26": "Perda de auditoria",
    "R27": "Repúdio de aprovação", "R28": "Falha aberta do guard",
    "R29": "CSRF em lançamento",
    # requisitos
    "RS01": "Imutável após o envio", "RS02": "MFA em admin e gestor",
    "RS03": "Autorização por recurso", "RS04": "JWT assimétrico e estrito",
    "RS05": "Auditoria transacional", "RS06": "Negar por padrão",
    "RS07": "Carga do ERP assinada", "RS08": "Proteção anti-CSRF",
    # controles
    "C1": "SSO com 2º fator", "C2": "Guard exige MFA", "C3": "Permissão por recurso",
    "C4": "Máquina de estados", "C5": "Carga: versão aprovada", "C6": "audit_logs",
    "C7": "Monitoramento e alertas", "C8": "Testes de segurança",
    "C9": "Emissor e cofre (KMS)", "C10": "Validação do token",
    "C11": "Auditoria e outbox", "C12": "Guard nega por padrão",
    "C13": "Manifesto da carga", "C14": "Anti-CSRF",
    # verificações
    "VF-RS01": "Alteração pós-envio recusada", "VF-R18": "Autoaprovação recusada",
    "VF-RS02": "Token sem MFA recusado", "VF-RS03": "Fora do escopo: 404",
    "VF-RS04": "Validação de token", "VF-RS05": "Falha na auditoria desfaz",
    "VF-RS06": "Rotas com política", "VF-RS07": "Sem verificação",
    "VF-RS08": "CSRF aceito (xfail)", "VF-V01": "Refresh reaceito",
    "VF-V02": "Token no corpo", "VF-V03": "PyJWT com CVE",
    # regras de detecção
    "D01": "Falhas repetidas de MFA", "D02": "Negações repetidas",
    "D03": "Falhas de login repetidas", "D04": "Login privilegiado suspeito",
    "D05": "Reuso de refresh token", "D06": "Token recusado ou chave fora",
    "D07": "Alteração pós-envio", "D08": "Regra de serviço alterada",
    "D09": "Consulta em volume", "D10": "Falha do guard (503)",
    "D11": "Falha de auditoria", "D12": "Recusa de origem ou CSRF",
    "D13": "Limite excedido (429)", "D14": "Divergência na carga",
    # gates
    "QG1": "Riscos prioritários", "QG2": "Requisito rastreado",
    "QG3": "PR, lint e tipos", "QG4": "Testes de segurança",
    "QG5": "Sem segredo ou CVE", "QG6": "Alertas analisados",
    "QG7": "Deploy autorizado", "QG8": "Incidentes tratados",
}


def montar() -> dict:
    ameacas = ler_ameacas()
    riscos = ler_riscos()
    ids_ameaca = {a["id"] for a in ameacas}
    assert all(t in ids_ameaca for r in riscos for t in r["ameacas"]), "ameaça citada e ausente"

    nos, arestas = [], []

    for a in ameacas:
        nos.append({"id": a["id"], "col": "ameaca", **a})
    for r in riscos:
        nos.append({"id": r["id"], "col": "risco", **r})
        for t in r["ameacas"]:
            arestas.append([t, r["id"]])

    riscos_prioritarios = {"R01", "R02", "R03", "R06", "R07", "R18", "R23", "R26", "R28", "R29"}

    for rs, dec, rks, titulo, detalhe in REQUISITOS:
        situacao = next(v[2] for v in VERIFICACOES if v[0] == f"VF-{rs}")
        nos.append({"id": rs, "col": "requisito", "decisao": dec, "titulo": titulo,
                    "detalhe": detalhe, "cwe": CWE[rs], "riscos": rks, "situacao": situacao})
        for rk in rks:
            arestas.append([rk, rs])
        for c in REQ_CONTROLES[rs]:
            arestas.append([rs, c])

    for c, nome in CONTROLES.items():
        nos.append({"id": c, "col": "controle", "titulo": nome, "transversal": c in TRANSVERSAIS})

    for vid, titulo, sit, controles, evidencia, testes in VERIFICACOES:
        nos.append({"id": vid, "col": "evidencia", "tipo": "verificacao", "titulo": titulo,
                    "situacao": sit, "evidencia": evidencia, "testes": testes})
        for c in controles:
            arestas.append([c, vid])
        for t in ACHADO_AMEACA.get(vid, []):
            arestas.append([t, vid])

    for did, titulo, rks, rs, ctrl, sev, sit, nota, sit_prop in DETECCOES:
        nos.append({"id": did, "col": "evidencia", "tipo": "deteccao", "titulo": titulo,
                    "situacao": sit, "nota": nota, "situacao_proposta": sit_prop,
                    "severidade": sev, "riscos": rks, "requisito": rs})
        if ctrl:
            arestas.append([ctrl, did])
        for rk in rks:
            arestas.append([rk, did])

    for gid, titulo in GATES:
        nos.append({"id": gid, "col": "gate", "titulo": titulo})
    # Vínculos do pipeline (etapa-7): qual evidência alimenta cada gate
    for r in riscos_prioritarios:
        arestas.append([r, "QG1"])
    for rs, *_ in REQUISITOS:
        arestas.append([rs, "QG2"])
    for vid, _, sit, *_ in VERIFICACOES:
        if vid in ACHADO_AMEACA:
            arestas.append([vid, "QG5" if vid == "VF-V03" else "QG6"])
        else:
            arestas.append([vid, "QG4"])
    for did, *_ in DETECCOES:
        arestas.append([did, "QG8"])

    for n in nos:
        n["rotulo"] = ROTULOS[n["id"]]

    # remove duplicatas preservando a ordem
    vistos, unicas = set(), []
    for a, b in arestas:
        if (a, b) not in vistos:
            vistos.add((a, b))
            unicas.append([a, b])
    ids = {n["id"] for n in nos}
    assert all(a in ids and b in ids for a, b in unicas), "aresta com nó inexistente"
    return {"nos": nos, "arestas": unicas}


if __name__ == "__main__":
    dados = montar()
    (SAIDA / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    modelo = SAIDA / "modelo.html"
    if modelo.exists():
        html = modelo.read_text(encoding="utf-8").replace(
            "/*__DADOS__*/null", json.dumps(dados, ensure_ascii=False)
        )
        # `modelo.html` é um fragmento (o Artifact acrescenta o esqueleto). Para abrir direto no
        # navegador, `index.html` ganha o doctype e os metas, que evitam o modo de compatibilidade.
        cabeca = ('<!doctype html>\n<meta charset="utf-8">\n'
                  '<meta name="viewport" content="width=device-width, initial-scale=1">\n')
        (SAIDA / "index.html").write_text(cabeca + html, encoding="utf-8")
    print(f"{len(dados['nos'])} nós, {len(dados['arestas'])} arestas")
