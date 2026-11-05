# Prática 2 — Validação de token e MFA

## 1. Risco e requisito relacionados

| Item                     | Descrição                                                                                                                                                                                                                                                         |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Risco                    | R02, captura de conta ou perfil no SSO (Crítico, 3×4), conforme o [plano de tratamento](../etapa-2/etapa-2-plano-e-residual.md)                                                                                                                                   |
| Requisito                | RS02. Quem tem perfil de administrador ou gestor só consegue entrar depois de confirmar um segundo fator no SSO, e a API recusa, nesses perfis, qualquer token que não mostre que o MFA foi concluído. Conforme os [Requisitos](../etapa-3/etapa-3-requisitos.md) |
| Decisão de arquitetura   | D01, exigir o MFA no SSO e conferi-lo também na API. Conforme as [Decisões](../etapa-3/etapa-3-decisoes.md)                                                                                                                                                       |
| Prática de código seguro | Proteção de sessões, com validação completa do token e exigência do segundo fator                                                                                                                                                                                 |

Hoje não existe MFA nem detecção de sessões estranhas. Se alguém descobrir a senha de um administrador ou de um gestor, por phishing ou porque a pessoa reutilizou a senha, essa pessoa passa a controlar as aprovações. Esta prática faz o segundo fator ser exigido no SSO e também conferido pela API. A conferência na API é importante porque um token emitido por outro caminho, sem MFA, passaria pela proteção do SSO sem ser barrado.

## 2. Testes de segurança definidos antes da implementação

Escrevemos os testes antes do código da seção 3. Os dados são fictícios e os caminhos das rotas são só exemplos.

**Cenário.** Um gestor aprova lançamentos. O perfil dele é privilegiado, então exige MFA.

| Teste | Entrada ou ação                                                                                                                                                                   | Resultado esperado                                                                                                                                            |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TS03  | O gestor entra pelo SSO, confirma o segundo fator e usa o token recebido para aprovar um lançamento                                                                               | O token mostra que o MFA foi concluído e tem emissor, audience, prazo e sessão corretos. Permitido, e a aprovação é concluída                                 |
| TS04  | Alguém com a senha do gestor usa um token válido emitido sem o segundo fator, por exemplo por um login mal configurado ou pelo provedor local, e tenta aprovar o mesmo lançamento | A API recusa o pedido como não autenticado e informa que o MFA é necessário. Nada é aprovado, a tentativa fica registrada e tentativas repetidas geram alerta |

Abaixo, um esboço de como esses testes ficariam no código.

```python
def test_ts03_gestor_com_mfa_aprova_lancamento(
    client, token_gestor_com_mfa, lancamento, auditoria
):
    resposta = client.post(
        f"/v1/lancamentos/{lancamento.id}/aprovar", auth=token_gestor_com_mfa
    )
    assert resposta.status_code == 200
    assert lancamento.recarregar().status == "aprovado"  # a aprovação aconteceu de fato
    assert auditoria.ultimo_evento().tipo == "lancamento_aprovado"


def test_ts04_token_de_gestor_sem_mfa_e_recusado(
    client, token_gestor_sem_mfa, lancamento, auditoria
):
    resposta = client.post(
        f"/v1/lancamentos/{lancamento.id}/aprovar", auth=token_gestor_sem_mfa
    )
    assert resposta.status_code == 401
    assert resposta.json()["motivo"] == "mfa_necessario"
    assert lancamento.recarregar().status != "aprovado"
    assert auditoria.ultimo_evento().tipo == "mfa_ausente"
```

Os dois testes usam o mesmo gestor, a mesma rota e o mesmo lançamento. A única diferença é o token, que traz ou não a indicação de MFA. Assim, se um teste passa e o outro não, sabemos que foi o MFA que fez a diferença.

```python
@pytest.fixture
def token_gestor_com_mfa(emitir_token):
    return emitir_token(perfil="gestor", amr=["pwd", "mfa"])


@pytest.fixture
def token_gestor_sem_mfa(emitir_token):
    return emitir_token(perfil="gestor", amr=["pwd"])
```

## 3. Implementação

### 3.1 Configuração no SSO

Este primeiro passo acontece na configuração do Keycloak e não no código da API. Vale confirmar os detalhes com a equipe que cuida do SSO.

1. Criar, no fluxo de login, uma etapa que exige o segundo fator (uma senha de uso único) para os papéis de administrador e gestor.
2. Fazer o SSO colocar no token a lista dos métodos de autenticação usados, no campo `amr`. Esse campo deve conter `mfa` quando o segundo fator for concluído. Pode ser preciso criar um mapeador de claims para isso.
3. Manter o token de acesso com prazo curto e deixar a renovação para o token de atualização. Assim, um token roubado vale por pouco tempo.

### 3.2 Validação completa do token na API

A API não confia só na assinatura. Ela também confere quem emitiu o token, para quem ele foi emitido (a audience) e se ele ainda não expirou, e aceita apenas o algoritmo esperado.

```python
def validar_token(token: str) -> Claims:
    return jwt.decode(
        token,
        key=CONFIG.chave_de_validacao,              # vem do kv corporativo
        algorithms=[CONFIG.algoritmo_do_token],     # lista fixa, nunca "none"
        issuer=CONFIG.emissor_esperado,vem do
        audience=CONFIG.audience_esperada,
        options={"require": ["exp", "iss", "aud", "sub", "sid"]},
    )                                               # qualquer falha vira 401
```

### 3.3 Guard com perfil, sessão e MFA

O guard que já conferia o perfil passa a conferir também a sessão registrada no servidor e, nos perfis privilegiados, se o MFA foi concluído.

```python
PERFIS_PRIVILEGIADOS = {"admin", "gestor"}


def exigir_perfil(*perfis_permitidos):
    def guard(request) -> Usuario:
        claims = validar_token(token_da_requisicao(request))
        usuario = usuarios.buscar(claims["sub"])
        sessao = sessoes.buscar(claims["sid"])

        if sessao is None or sessao.revogada:
            negar(401, motivo="sessao_invalida")

        if usuario.perfil not in perfis_permitidos:
            negar(403, motivo="perfil_sem_permissao")

        if usuario.perfil in PERFIS_PRIVILEGIADOS and not mfa_concluido(claims):
            auditoria.registrar("mfa_ausente", usuario.id, rota=request.url.path)
            registrar_falha_mfa(usuario.id, request.client.host)
            negar(401, motivo="mfa_necessario")

        return usuario

    return guard


def mfa_concluido(claims) -> bool:
    return "mfa" in claims.get("amr", [])
```

### 3.4 Alerta para falhas repetidas

Várias falhas seguidas na segunda etapa podem indicar alguém tentando usar uma senha roubada. Nesse caso, a equipe de segurança recebe um alerta.

```python
def registrar_falha_mfa(usuario_id, origem):
    total = contador.incrementar(f"mfa_falha_{usuario_id}", janela_em_segundos=600)
    if total >= LIMITE_FALHAS_MFA:  # valor inicial definido pela segurança, por exemplo 5
        alertas.disparar("mfa_falhas_repetidas", usuario_id, origem)
```

## 4. Resultado esperado

- O TS03 passa, então o gestor que confirma o segundo fator usa o sistema normalmente.
- O TS04 passa, então um token de perfil privilegiado sem MFA é recusado, mesmo que esteja correto em todo o resto.
- A API só aceita tokens com assinatura, emissor, audience e prazo corretos, ligados a uma sessão registrada que não foi revogada.
- Cada tentativa recusada por falta de MFA fica registrada, e tentativas repetidas geram alerta.
- Quem tem só a senha não consegue uma sessão de administrador ou gestor.
- A probabilidade de R02 cai de 3 para 1. É uma estimativa, que só se confirma quando os testes forem executados.

## 5. Referência da OWASP utilizada

- [Multifactor Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html), que explica como exigir o segundo fator e o que fazer com as falhas repetidas.
- [Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), que trata de ligar o token a uma sessão no servidor e de revogar sessões.
- [REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html), que mostra como validar o token (algoritmo, emissor, audience e prazo).
- OWASP ASVS 5.0, capítulo [V6 (Autenticação)](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x15-V6-Authentication.md), em especial a seção V6.5 sobre autenticação multifator, e capítulo [V7 (Gerenciamento de sessão)](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x16-V7-Session-Management.md).
