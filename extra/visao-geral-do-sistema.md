# Visão Geral do Sistema - Faturamento de Redes

Documento descritivo do sistema, extraído do código-fonte.

| Campo               | Valor      |
| ------------------- | ---------- |
| Versão do documento | 1.0        |
| Data                | 2026-09-15 |

---

## 1. Identificação do Sistema

| Atributo                   | Valor                                                                              |
| -------------------------- | ---------------------------------------------------------------------------------- |
| **Nome**                   | Network Billing Backend                                                            |
| **Projeto**                | `network-billing-backend`                                                          |
| **Classificação**          | Software proprietário, uso interno corporativo                                     |
| **Tipo**                   | Backend de API (REST)                                                              |
| **Domínio de negócio**     | Faturamento, provisionamento contábil, bases de rede credenciada e analytics       |
| **Prefixo da API**         | `/v1`                                                                              |
| **Runtime**                | Python 3.11+                                                                       |
| **Framework**              | FastAPI + Uvicorn                                                                  |
|                            |
| **Consumidor principal**   | Frontend web de Faturamento (aplicação SPA)                                        |
| **Provedor de identidade** | Keycloak corporativo via OAuth Service .NET; provedor `local` para desenvolvimento |

### Ambientes

Um único banco PostgreSQL compartilhado, segregado por **schema por ambiente**
(`public`, `public_qa`, …), cada schema com sua própria tabela `alembic_version`.
O schema é selecionado por `POSTGRES_SCHEMA`.

---

## 2. Descrição do Sistema

### 2.1 Propósito

O sistema centraliza o ciclo financeiro da plataforma de Network Billing da epharma:

1. **Cadastros (registry)** — empresas, clientes, contratos, segmentos, programas, grupos
   econômicos, centros de custo, unidades de negócio, fornecedores e regras de serviço.
   É a base contratual que determina _como_ cada valor é calculado.
2. **Faturamento (PSP)** — lançamentos por cliente × período × regra de serviço, com
   cálculo autoritativo no servidor, máquina de estados de aprovação, anexos, timeline
   de auditoria e central de aprovações com envio de e-mail ao cliente.
3. **Integração ERP** — geração das cargas em Excel que alimentam o ERP, por categoria
   (faturamento, mensal, entregas, anual, retenção, recuperação, GBM, varejo) e por eixo
   financeiro (contas a pagar / contas a receber).
4. **Provisão financeira** — fechamento contábil mensal com snapshot, ciclo fecha/reabre
   _append-only_ e importação de planilhas.
5. **Bases de rede (network)** — sincronização periódica de dados da rede credenciada
   vindos do Oracle legado para o PostgreSQL, com fluxo próprio de aprovação por eixo
   (pagar/receber): pagar/receber, retido/recuperado, varejo, contraprestações
   (anual, mensal, entregas) e sinistralidade.
6. **Dashboards** — KPIs analíticos lidos diretamente do Oracle, sem persistência local.

### 2.2 Arquitetura

Clean Architecture + DDD em quatro camadas, com a regra de dependência apontando sempre
para dentro (`domain → application → infrastructure/presentation`):

| Camada               | Responsabilidade                                                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `src/domain`         | Entidades (dataclasses puras), value objects, portas (Protocol), exceções, paginação. Zero dependência externa.           |
| `src/application`    | Casos de uso, uma classe por operação, com Command DTO (dataclass) no mesmo arquivo.                                      |
| `src/infrastructure` | Implementações concretas: gateways SQLAlchemy, SQL nativo Oracle, storage, Celery tasks, geração de Excel, clientes HTTP. |
| `src/presentation`   | Rotas FastAPI, schemas Pydantic, middleware, container de injeção de dependências (`deps.py`).                            |
| `src/core`           | configuração, logging, rate limit, autenticação, EventBus WebSocket, app Celery.                                          |

**Pontos arquiteturais que valem atenção:**

- **Persistência híbrida.** PostgreSQL é utilizado nas operações transacionais, com SQLAlchemy 2.0 async e Alembic. O Oracle é somente leitura, acessado via SQL nativo com `oracledb`, atendendo aos dashboards legados e às sincronizações de rede.

- **Mappers obrigatórios.** Gateways devem retornar entidades de domínio, nunca modelos ORM. As conversões ficam centralizadas em `src/infrastructure/persistence/mappers/{entity}_mapper.py`.

- **Cálculos no servidor.** O servidor sempre recalcula os valores recebidos do cliente conforme as regras de negócio. Se houver divergência, retorna um `warning` na resposta, sem interromper a operação.

### 2.3 Superfície exposta

| Interface               | Observação                                                                               |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| Endpoints HTTP públicos | Todos sob `/v1`, com guard de autenticação                                               |
| Callbacks internos      | `internal_router`, sem JWT, protegidos por `X-Callback-Secret`, fora do OpenAPI          |
| WebSocket               | Autenticado pela primeira mensagem; canais `billing:{AAAA-MM}` e `notifications:{email}` |

### 2.4 Processamento assíncrono

**Tarefas Celery** (broker RabbitMQ, result backend RPC) cobrem exportações Excel,
importações em massa, sincronizações de rede, aprovações em lote e sincronização de
usuários do Keycloak. O agendamento não é estático: o `DatabaseBeatScheduler` lê as
expressões cron da tabela `task_schedules` e **recarrega do banco a cada 60 segundos**,
permitindo alterar horários sem reiniciar.

O padrão de conclusão é sempre o mesmo: o worker chama um callback HTTP interno, que
persiste a notificação e publica `task_status_changed` no canal WebSocket do usuário.

---

## 3. Ativos Importantes

### 3.1 Ativos de dados (PostgreSQL)

| Grupo                      | Conteúdo                                                                                                                                                      | Criticidade | Por quê                                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------ |
| **Faturamento**            | Faturamentos por cliente × período, lançamentos, histórico de transições e anexos                                                                             | **Alta**    | Valores financeiros e sua trilha de aprovação. Perda ou adulteração afeta faturamento real ao cliente. |
| **Cadastros contratuais**  | Empresas, clientes, contratos, regras de serviço e suas faixas, programas, grupos econômicos, segmentos, centros de custo, unidades de negócio e fornecedores | **Alta**    | Determinam o cálculo de todo valor. Erro aqui se propaga silenciosamente para o faturamento.           |
| **Bases de rede**          | Pagar/receber, retido/recuperado, varejo, contraprestações (anual, mensal, entregas), sinistralidade e controle de execução dos syncs                         | **Alta**    | Base de pagamento/recebimento da rede credenciada, com estado de aprovação por eixo.                   |
| **Provisão**               | Snapshots do fechamento, histórico de fecha/reabre, lançamentos de emissão, carga histórica estática e histórico de importações                               | **Alta**    | Fechamento contábil. O histórico é _append-only_ por exigência de auditoria.                           |
| **Auditoria e identidade** | Trilha de requisições mutantes, auditoria de mudança de perfil, usuários do provedor local e cache/log de sincronização do Keycloak                           | **Alta**    | Guarda hash bcrypt de senha e é a prova de quem fez o quê.                                             |
| **Operacional**            | Logs de exportação e seus itens, logs de envio de e-mail de aprovação, notificações e agendamentos das tarefas                                                | Média       | O log de e-mail preserva o payload enviado ao cliente inclui destinatários e valores.                  |

**Dados sensíveis identificados:** CNPJ de empresas, fornecedores e estabelecimentos da
rede; valores financeiros por cliente, e-mails corporativos de aprovadores, hash de senha
dos usuários do provedor local. Não há CPF nem dado de paciente no modelo de dados deste
serviço.

### 3.2 Ativos de código

| Ativo                           | Localização                                                                         | Por que é crítico                                                                              |
| ------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Motor de cálculo de valores     | `src/application/use_cases/billing/billing/_shared.py`                              | Autoridade sobre todo valor faturado (`fixed_value`, `multiplication`, `percentage`, `range`). |
| Máquina de estados de aprovação | casos de uso de `change_item_status` + `src/domain/value_objects/billing_status.py` | Define quais transições são legais e quem pode executá-las.                                    |
| Guards de autorização           | `src/presentation/api/routes/infra/auth.py` (`require_any_role`, `require_role`)    | Único ponto entre o token e os dados. Rota nova sem guard é exposição direta.                  |
| Provedores de autenticação      | `src/core/auth/` (`local_provider`, `keycloak_provider`, `factory`)                 | Emissão e validação de token, troca de provedor por configuração.                              |
| SQL nativo Oracle               | `src/infrastructure/persistence/queries/` (dashboard, network, psp)                 | Único lugar com SQL concatenado a mão, superfície de injeção se bindvars não forem usados.     |
| Geradores de carga ERP          | `src/infrastructure/xlsx/` + `routes/billing/_erp_exporters.py`                     | O arquivo gerado é consumido pelo ERP, layout errado vira lançamento contábil errado.          |
| Migrations                      | `alembic/versions/`                                                                 | Migration já aplicada nunca deve ser editada, o CI roda `upgrade head` no ambiente real.       |

### 3.3 Ativos de configuração e chaves

Nenhuma chave é armazenada em hard code, todas chaves são armazenadas em ambiente corporativo de Key Vault

| Segredo                | Variável                                                                   | Uso                                                                       |
| ---------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Assinatura de JWT      | `JWT_SECRET` (mín. 32 bytes)                                               | Sessão de todos os usuários. Vazamento = forja de token com role `admin`. |
| Segredo de callback    | `CELERY_CALLBACK_SECRET`                                                   | Única barreira dos 20 endpoints internos, que não exigem JWT.             |
| Client secret Keycloak | `KEYCLOAK_CLIENT_SECRET`                                                   | Identidade da aplicação no IdP.                                           |
| Credenciais Oracle     | `ORACLE_USER` / `ORACLE_PASSWORD`                                          | Acesso de leitura ao legado corporativo.                                  |
| Credenciais PostgreSQL | `POSTGRES_USER` / `POSTGRES_PASSWORD`                                      | Banco transacional.                                                       |
| Storage                | `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY`, `AZURE_STORAGE_CONNECTION_STRING` | Anexos e planilhas exportadas.                                            |
| Mensageria             | `RABBITMQ_USER` / `RABBITMQ_PASSWORD`, `CELERY_BROKER_URL`                 | Fila de tarefas.                                                          |
| Serviço de e-mail      | `EMAIL_SERVICE_API_KEY`                                                    | Envio de e-mail de aprovação em nome da epharma.                          |
| Monitoramento          | `FLOWER_USER` / `FLOWER_PASSWORD`                                          | Painel do Celery.                                                         |

### 3.4 Ativos de infraestrutura e dependências externas

| Recurso                         | Papel                                        | Efeito da indisponibilidade                                                  |
| ------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------- |
| PostgreSQL 16                   | Banco transacional                           | Sistema inoperante                                                           |
| Oracle 11.2+                    | Leitura analítica e fonte das sincronizações | Dashboards e syncs de rede param; faturamento em PostgreSQL segue            |
| RabbitMQ                        | Broker Celery                                | Exportações, importações e syncs param                                       |
| Azure Blob / MinIO              | Anexos e arquivos gerados                    | Upload e download indisponíveis, o startup tolera e adia a criação do bucket |
| Keycloak + OAuth Service (.NET) | Identidade corporativa                       | Login bloqueado no provedor `keycloak`                                       |
| Serviço de e-mail corporativo   | Envio de aprovação ao cliente                | Central de aprovações não envia                                              |
| Flower                          | Observabilidade de filas                     | Perda de visibilidade, sem impacto funcional                                 |

---

## 4. Segurança Aplicada

A segurança da aplicação foi pensada em diferentes camadas, buscando proteger o acesso, os dados e as operações realizadas pelo sistema.

- **Autenticação em duas vias:** o sistema prioriza o cookie `HttpOnly` `access_token` para autenticar as requisições. Caso ele não esteja presente, também aceita o token enviado pelo cabeçalho `Authorization: Bearer`. Já o cookie de refresh token possui acesso restrito à rota `/v1/auth/refresh`.

- **Controle de acesso por perfil:** existem quatro perfis de usuário (`admin`, `manager`, `analyst` e `none`), cada um com suas permissões. Para acessar as funcionalidades de negócio, é necessário possuir um JWT válido e um perfil diferente de `none`. A única exceção é a rota `POST /v1/access-request`, que permite solicitações de acesso sem autenticação de perfil.

- **Proteção de callbacks internos:** as rotas utilizadas para comunicação interna ficam isoladas em um `internal_router`, sem autenticação JWT. O acesso é protegido por meio do cabeçalho `X-Callback-Secret`, e essas rotas não são exibidas na documentação da API.

- **Limitação de requisições:** a aplicação conta com um controle global de 60 requisições por minuto, por IP. Além disso, algumas operações possuem limites próprios, como login (10/min), criação de lançamentos (30/min) e operações em lote (10/min), reduzindo o risco de uso abusivo.

- **Registro de atividades:** o `AuditMiddleware` registra automaticamente as requisições que alteram dados, armazenando as informações na tabela `audit_logs` em segundo plano. Quando disponível, o usuário responsável pela operação é identificado pelo token. A rota de login é excluída desse processo para evitar o armazenamento de credenciais.

- **Documentação protegida em produção:** as interfaces `/docs` e `/redoc` ficam disponíveis somente quando `DEBUG=true`, evitando a exposição da documentação técnica em ambientes de produção.

- **Validação de arquivos enviados:** os uploads passam por uma verificação conjunta de tipo MIME e extensão, além de respeitarem o limite máximo de 25 MB por arquivo.

- **Revisões de segurança padronizadas:** o projeto mantém no próprio repositório quatro skills versionadas (`sec-route`, `sec-oracle`, `sec-secrets` e `sec-review`). Elas ajudam a revisar novas rotas, consultas SQL Oracle, possíveis exposições de segredos e pontos de atenção relacionados às recomendações da OWASP.

---

## 5. Qualidade e Entrega

| Controle                    | Ferramenta                                                          | Onde roda                 |
| --------------------------- | ------------------------------------------------------------------- | ------------------------- |
| Lint                        | Ruff                                                                | Local + hook              |
| Tipagem                     | Mypy **strict**                                                     | Local + CI                |
| Testes                      | Pytest + pytest-asyncio                                             | Local + CI                |
| Segredos                    | Gitleaks via ferramenta interna                                     | Local + CI                |
| CVEs de imagem              | Trivy                                                               | CI (`Build & Trivy Scan`) |
| DAST                        | Nuclei                                                              | CI (`Nuclei Scan`)        |
| Revisão assistida           | PR-Agent (describe / review / improve) + verificação de self-review | CI, em paralelo           |
| Cooldown de dependências    | ferramenta interna (≥7 dias desde a publicação)                     | CI, mitiga supply-chain   |
| Atualização de dependências | Renovate, com notificação no Teams                                  | CI                        |

Os testes ficam **junto do código** (`src/domain/tests`, `src/application/use_cases/tests`,
`src/infrastructure/tests`), não em um diretório `tests/` na raiz. A concentração maior
está em `src/infrastructure/tests`

---
