# Protótipo — Faturamento PSP (lançamentos + regras de serviço + login mock)

Protótipo da engenharia de software seguro. Replica só o que as etapas 1 a 4 abordam: o fluxo de
**lançamentos do PSP**, o cadastro de **serviços e regras** que alimenta o lançamento e o
**login**, mais o aviso em **tempo real** das mudanças no faturamento. O restante do sistema original
(anexos, central de aprovações, ERP, provisão, dashboards e os demais cadastros) ficou de fora.

| Parte | Origem | Aqui |
|---|---|---|
| `backend/` | `network-billing-backend` | FastAPI em DDD + Clean Architecture. **Tudo persiste no Redis.** |
| `frontend/` | `network-billing-dashboard` | Next.js: telas de Faturamento PSP e de Serviços e Regras, mais o login. |

## Como subir

Pré-requisitos: Python 3.11, Node 20+, pnpm, Redis 7 (ou Docker).

```bash
# 1) Redis
docker run --rm -p 6379:6379 redis:7-alpine        # ou redis-server

# 2) Backend  (porta 8000)
cd backend
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env     # preencha JWT_SECRET, MOCK_LOGIN_PASSWORD e MOCK_OTP_CODE
.venv/bin/uvicorn src.presentation.api.main:create_app --factory --port 8000

# 3) Frontend (porta 3000)
cd ../frontend
cp .env.example .env.local && pnpm install && pnpm dev
```

Ou tudo junto: `docker compose up --build` (precisa de `backend/.env`).

Se a 8000 ou a 3000 estiverem ocupadas, mude a porta da API e ajuste `NEXT_PUBLIC_BACKEND_URL`
no front e `CORS_ORIGINS` no backend.

## Usuários de demonstração (fictícios)

A senha e o código OTP são os que você definiu em `MOCK_LOGIN_PASSWORD` e `MOCK_OTP_CODE`.
O campo OTP da tela de login é opcional.

| Usuário | Perfil | Escopo | MFA |
|---|---|---|---|
| `analyst` | analista: cria, edita, envia para a gestão | clientes Alfa e Beta | não exigido |
| `manager` | gestor: aprova e reprova | todos | **exigido** |
| `admin` | admin: todas as transições | todos | **exigido** |

Perfil privilegiado que entra **sem OTP** recebe um token com `amr=["pwd"]`. A tela abre, mas a API
recusa as ações com `401 mfa_necessario`. Isso simula o cenário do TS04 (token emitido por um
caminho sem segundo fator). No SSO real, esse login nem geraria sessão.

## Serviços e regras (`/service-rules`)

Cada serviço lançado em `/psp` vem de uma **regra de serviço** do cliente (valor fixo, percentual,
multiplicação, faixas ou valor variável). A tela `/service-rules` cadastra essas regras: escolha o
cliente e crie, edite ou exclua os serviços dele. Uma regra nova aparece em `/psp` como "Sem
Lançamento" e já pode ser lançada.

| Perfil | Pode |
|---|---|
| `analyst`, `manager` | consultar as regras dos clientes do seu escopo |
| `admin` (com OTP) | criar, editar e excluir regras |

Endpoints (mesmos caminhos do serviço original):

| Método e caminho | Perfil |
|---|---|
| `GET /v1/registry/clients/summary` e `GET /v1/registry/clients?search=` | qualquer perfil, só clientes do escopo |
| `GET /v1/registry/clients/{id}/programs` | qualquer perfil, no escopo |
| `GET /v1/registry/clients/{id}/service-rules` e `.../{rule_id}` | qualquer perfil, no escopo |
| `POST`, `PATCH`, `DELETE` em `/v1/registry/clients/{id}/service-rules` | só `admin`, com limite de requisições |

Regras de negócio, como no original:

- Regra **com lançamento** não pode ser excluída (422), e só o `status` pode mudar. Mexer no
  cálculo reescreveria o passado.
- Nome + conjunto de programas é único por cliente (409). A edição usa `version` (409 se
  defasada). Faixas começam em 0, não se sobrepõem e só a última fica em aberto.
- O `code` da regra é gerado pelo servidor. Nos dados de demo ele vai até 302, e as regras
  criadas pela tela começam em 1001.
- Criar, editar e excluir ficam na auditoria (`regra_servico_*`), só com os nomes dos campos
  alterados.
- Cliente fora do escopo responde 404, igual a cliente inexistente, e registra `acesso_negado`.

Diferenças em relação ao original, de propósito:

- **Sem os campos do ERP** (percentuais de gerenciamento, teleassistência e licenciamento, os três
  códigos e "notas separadas"): o lançamento não os usa, e eles pertencem à carga do ERP.
- **Sem centro de lucro nem contrato.** Os programas vêm de um catálogo por cliente criado no
  seed, e vincular programa é opcional. As regras de demonstração têm programa; uma regra criada
  sem programa aparece em `/psp` no grupo "Sem programa".
- **"Exige aprovação do cliente"** é um campo da regra (RF-PSP-34), porque o protótipo não tem
  contratos que o derivem.
- Com lançamento, o reenvio das mesmas faixas não conta como alteração. O original recusava
  qualquer envio de faixas, o que impedia só inativar uma regra de faixa que já tinha lançamento.

## Arquitetura do backend

```
src/
├── domain/          entidades, value objects, política de acesso, portas (Protocol). Sem dependências.
├── application/     casos de uso (um por operação), Authenticator, ResourceAccessGuard, SecurityMonitor
├── infrastructure/  adaptadores: gateways Redis, JWT, IdP mock, seed
└── presentation/    FastAPI: rotas, schemas, guards, tratamento de erros, raiz de composição
```

A dependência aponta para dentro. Trocar o Redis por outro banco exige novos gateways, não mexe
nos casos de uso.

### Como o Redis substitui o banco relacional

| Garantia do original | No Redis |
|---|---|
| Bloqueio otimista por `version` (409) | `WATCH` na chave do item + `MULTI/EXEC` |
| Lote tudo-ou-nada (RF-PSP-36) | valida tudo antes; grava com uma única `MULTI/EXEC` |
| Único cliente × período × regra | `SET NX` no índice do faturamento |
| Item e timeline juntos | mesmo `MULTI/EXEC` |
| Sessão revogável | chave `psp:session:{sid}` com TTL |
| Limite por IP, falhas de MFA | contador `INCR` + `EXPIRE NX` |

## Práticas da etapa 4 implementadas (e testadas)

| Prática | Onde | Testes |
|---|---|---|
| 1. Autorização por recurso (RS03) | `domain/services/access_policy.py`, `application/access_guard.py`, filtro de escopo nos gateways | TS01, TS02 e variantes |
| 2. Validação de token e MFA (RS02) | `infrastructure/auth/jwt_token_service.py`, `application/authenticator.py`, `security_monitor.py` | TS03, TS04 e variantes |
| Negar por padrão (RS06) | guards em `presentation/api/deps.py`; rota sem política impede a subida | `test_rotas_e_falhas_seguras.py` |

A rota `GET /v1/billing/items/{id}` não existe no original. Foi acrescentada para o TS01 e o TS02.

```bash
cd backend && .venv/bin/python -m pytest -q   # usa fakeredis, não precisa de Redis
```

## Tempo real (`/ws`)

Quando alguém cria, altera, exclui, replica ou muda o status de um lançamento, quem está com o mesmo
mês aberto em `/psp` vê a lista atualizar sozinha.

- O evento é só um **aviso de invalidação** (`billing_changed`, com o cliente). Não leva valores: o
  front refaz o `GET /v1/billing`, que já aplica o escopo. O canal não vira um caminho paralelo
  para ler dados de outro cliente.
- **Autenticação**: o token vai na primeira mensagem (`{"type":"auth","token":...}`), nunca na URL.
  A checagem é a mesma das rotas HTTP: token, sessão, perfil e MFA. Perfil privilegiado sem OTP
  é recusado (fecha com 4003).
- **Origem**: o CORS não vale para WebSocket, então o servidor confere o `Origin` contra
  `CORS_ORIGINS` e nega quando falta.
- **Escopo**: só se inscreve em `billing:AAAA-MM` quem tem o período no escopo, e o aviso só chega
  se o cliente também estiver. O escopo é relido a cada entrega.
- **Revogação**: logout derruba a conexão, a sessão é conferida a cada entrega e a conexão fecha
  quando o token expira (4003). O front renova o token e reconecta.
- **Limites**: 5 conexões por usuário, 12 canais por conexão e mensagens de até 256 bytes.

Limitação: o hub vive em memória de um processo. Com mais de um worker, o aviso só chega a quem
está conectado no mesmo worker; em produção o hub precisaria de um barramento externo (Redis
pub/sub). Em Docker, `NEXT_PUBLIC_BACKEND_URL` já cobre o `ws://` (o CSP deriva dele).

## O que NÃO foi implementado

Fica como trabalho futuro, para não declarar mais do que existe:

- **RS01** (bloquear alteração após o envio): vale a regra do original, só `Approved` é imutável.
- **R18** (quem cria não aprova o próprio lançamento).
- **RS04** completo: o token é HS256 com segredo no ambiente, não chave assimétrica em cofre; sem `kid`.
- **RS05** (auditoria na mesma transação da operação) e outbox: a auditoria é gravada logo depois da
  operação, em chamada separada. A timeline do item, essa sim, é atômica com a mudança.
- **RS07** (carga do ERP) e **RS08** (CSRF com token anti-CSRF e checagem de `Origin`). Há CORS restrito
  e cookie `SameSite=Strict`, mas não o token.
- "Responsável pelo registro" na autorização de escrita; o escopo considera só cliente e período.
- Unicidade de nome + programas das regras sob corrida: a conferência roda sob `WATCH` do índice do
  cliente, mas a renomeação simultânea de **outra** regra do mesmo cliente não é observada.
- Cadastro de programas, clientes, contratos e centros de lucro: o catálogo de programas só é
  lido, vem do seed.
- Rotação de refresh token com detecção de reuso.

A estimativa de risco residual da etapa 4 continua sendo estimativa: os testes cobrem os cenários
descritos, não a produção.

## Dados

Todos os dados são fictícios (clientes, CNPJs, e-mails). O seed roda uma vez na subida da API.
Para recomeçar: `redis-cli FLUSHDB` e reinicie a API.
