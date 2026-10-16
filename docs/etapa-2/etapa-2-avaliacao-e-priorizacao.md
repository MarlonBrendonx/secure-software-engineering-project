# Etapa 2 — Avaliação e priorização dos riscos

## 4. Justificativas das avaliações

Para cada risco, foram apresentadas as justificativas atribuídas à probabilidade e ao impacto, identificando os ativos, processos ou componentes afetados e explicando como esses fatores fundamentam o nível de risco no contexto analisado.

Os riscos são avaliados como **risco atual**, ou seja, considerando os controles que já existem no sistema. Assim, o risco residual mostra apenas o efeito dos controles novos propostos no plano de tratamento. Os controles já existentes são indicados em cada risco.

### R01 — Alteração/remoção de lançamentos (Crítico, 3×4)

- **Origem:** CA01
- **Probabilidade (3):** o perfil `analista` já possui escrita sobre lançamentos,
  assim como o `admin`, o abuso não exige capacidade técnica especial, apenas má intenção.
- **Impacto (4):** o valor adulterado chega ao ERP e é cobrado do cliente.
  Afeta A1 (lançamentos), o faturamento, pode
  atingir vários clientes e períodos.
- **Contexto:** integridade do valor faturado é o objetivo central do sistema,
  a adulteração ataca a razão de existir do software

### R02 — Captura de conta/perfil SSO (Crítico, 3×4)

- **Origem:** CA02
- **Probabilidade (3):** phishing e reuso de credenciais são plausíveis em
  ambiente corporativo; não há MFA nem a detecção de sessão anômala.
- **Impacto (4):** conta `admin`/`gestor` dá controle total, inclusive aprovar,
  reprovar e encobrir atividade. Afeta A1, A2 e A3 e habilita a maioria dos
  demais abusos.
- **Contexto:** é a principal porta de entrada, pois amplifica quase
  todos os outros riscos.

### R03 — Acesso não autorizado a dados restritos (Alto, 3×3)

- **Origem:** T03, T07, T09, T11, T26 / CA03, CA26.
- **Probabilidade (3):** falhas de autorização nas APIs REST, como
  uma rota, endpoint de anexo ou consulta sem verificação.
- **Impacto (3):** exposição de leitura de lançamentos, anexos, CNPJ e e-mails.
  Prejuízo relevante à privacidade e ao negócio, mas sem alteração direta de valor.
- **Contexto:** é a base para R05, fraude e vazamentos.
- **Controles existentes:** guard `require_role` em todas as rotas; skill `sec-route`.

### R04 — Acesso direto aos anexos no storage (Médio, 2×3)

- **Origem:** T19 / CA03.
- **Probabilidade (2):** depende de condição específica, URL assinada com
  validade longa/sem escopo, ou vazamento das credenciais de storage.
- **Impacto (3):** anexos podem conter comprovantes e dados sensíveis de negócio,
  o acesso ocorre fora do controle e do log da aplicação.
- **Contexto:** pode comprometer a confidencialidade de documentos e dados sensíveis de negócio, sem os controles de autorização e rastreabilidade da aplicação.
- **Controles existentes:** URLs assinadas temporárias.

### R05 — Extração de dados em volume (Alto, 2×4)

- **Origem:** T04, T08, T10, T12 / CA04.
- **Probabilidade (2):** exige que o ator já tenha leitura (perfil, conta
  capturada ou R03) e que não haja limite/monitoração de extração em massa.
- **Impacto (4):** vazamento de dados de terceiros (CNPJ, anexos), risco
  jurídico/LGPD, dano a reputação e muitas pessoas afetadas.
- **Contexto:** consequência de maior gravidade da cadeia de acesso não autorizado

### R06 — Vazamento do `JWT_SECRET` (Alto, 2×4)

- **Origem:** T15 / CA04.
- **Probabilidade (2):** com um bom gerenciamento de chaves, como em keyvault, é quase improvável, mas a exposição por log, repositório, imagem ou variável de ambiente é uma condição específica que pode ocorrer.
- **Impacto (4):** compromete o ativo A9, permite forjar tokens de qualquer perfil, como identificado no risco R07, quebrando a autenticação de todo o sistema.
- **Contexto:** com prioridade elevada por ser pré-condição de R07.
- **Controles existentes:** segredos no cofre corporativo; Gitleaks local e no CI.

### R07 — Falsificar token (Alto, 2×4)

- **Origem:** T16 / CA09.
- **Probabilidade (2):** condicionada ao vazamento da chave (R06). Com a chave em mãos, gerar um token válido é trivial (qualquer biblioteca JWT faz isso).
- **Impacto (4):** acesso total sob identidade falsificada, inclusive `admin`,
  habilitando todos os abusos de acesso, alteração e vazamento, por exemplo.
- **Contexto:** dependente de R06. Com a chave vazada e o token falsificado, o atacante
  contorna todo o controle de autenticação e autorização e age como qualquer
  perfil.

### R08 — Remoção/adulteração da auditoria (Alto, 2×4)

- **Origem:** CA05
- **Probabilidade (2):** exige acesso a operação capaz de remover/alterar
  registros ou ao armazenamento da timeline, condição mais específica.
- **Impacto (4):** perda da capacidade de auditoria e de responsabilização,
  viabiliza ocultar os rastros no R01, R02 e R09.
- **Contexto:** a auditoria é o controle que sustenta a responsabilização de todos os demais riscos, sem ela, R01, R02 e R09 tornam-se mais difíceis de detectar. Não é o primeiro elo de um ataque, mas é o que garante que os outros deixem rastro
- **Controles existentes:** `AuditMiddleware` grava toda requisição mutante.

### R09 — Alteração de regras de serviço (Alto, 2×4)

- **Origem:** CA06
- **Probabilidade (2):** poucos perfis têm escrita em serviços, requer acesso
  específico, mas é uma operação normal do sistema.
- **Impacto (4):** a regra adulterada propaga-se de forma silenciosa a todos
  os cálculos futuros, faturamento errado em escala, sendo difícil de detectar.
- **Contexto:** A prioridade é elevada porque a falha se propaga de forma silenciosa, os dados corrompidos fluem entre módulos sem disparar erros ou alertas, o que atrasa a detecção. Quando o problema é percebido, a alteração já contaminou registros e cálculos derivados, o que dificulta identificar a origem e o alcance do dano.

### R10 — Adulteração do motor de cálculo (Médio, 1×4)

- **Origem:** T13, T37 / CA07, CA24.
- **Probabilidade (1):** exige acesso ao repositório ou cadeia de
  build comprometida, além de contornar revisão e testes, grande capacidade e
  acesso muito específico.
- **Impacto (4):** fatura errado em escala a partir do core, com rastreio
  difícil da possível causa.
- **Contexto:** ataca o núcleo do cálculo, que é usado na aprovação. A probabilidade é baixa, mas a gravidade somada à dificuldade de detecção coloca o R10 à frente de vários riscos
- **Controles existentes:** Mypy strict, ~2.900 testes, PR-Agent, Trivy, cooldown de dependências.

### R11 — DoS no fluxo de autorização (Médio, 2×2)

- **Origem:** T14a / CA08.
- **Probabilidade (2):** requer volume de requisições contra as transições,
  precisa de sessão válida ou endpoint alcançável.
- **Impacto (2):** paralisa temporariamente o fluxo de aprovação, recuperável e
  sem perda de dados
- **Contexto:** risco de disponibilidade, recuperável e sem
  dano ao dado. Tem mais importância se combinado com R14, tendo indisponibilidade de infra
- **Controles existentes:** rate limit de 10/min em operações em lote e 30/min na criação.

### R12 — Vazamento do `CELERY_CALLBACK_SECRET` (Alto, 2×4)

- **Origem:** T17 / CA04.
- **Probabilidade (2):** mesma natureza de R06, exposição por config/log/repo.
- **Impacto (4):** é a única barreira dos callbacks internos, o vazamento
  habilita R13.
- **Contexto:** Mesma classe de R06 (chave
  em cofre/rotação/varredura) e pré-condição de R13.
- **Controles existentes:** segredos no cofre corporativo; Gitleaks local e no CI.

### R13 — Falsificação de callbacks internos (Médio, 2×3)

- **Origem:** CA10
- **Probabilidade (2):** condicionada ao vazamento de A10 com o risco R12.
- **Impacto (3):** injeção de operações/estados falsos no processamento
  assíncrono, mas não concede acesso administrativo completo.
- **Contexto:** risco no callback interno, dependente do vazamento da chave (R12). A
  gravidade é menor que a de R07 porque o alcance se limita ao processamento
  assíncrono, sem privilégio administrativo.

### R14 — Indisponibilidade do banco/infra (Alto, 2×4)

- **Origem:** CA11
- **Probabilidade (2):** por estar na rede corporativa, um ataque vindo de fora é
  difícil. Mas a própria aplicação pode derrubar o banco, abrir mais conexões do
  que ele suporta, ou sobrecarregá-lo com consultas
  pesadas. Esse cenário interno é plausível.
- **Impacto (4):** sem o banco, todo o sistema para. Além da parada, operações em
  andamento durante a sobrecarga podem ficar incompletas e deixar dados
  inconsistentes.
- **Contexto:** todo o sistema depende de um único banco, se ele cai, não há
  alternativa. Esse ponto único de falha justifica o nível Alto.

### R15 — Envio de e-mails maliciosos (Médio, 2×3)

- **Origem:** CA12
- **Probabilidade (2):** depende do vazamento da `EMAIL_SERVICE_API_KEY`.
- **Impacto (3):** phishing/fraude de cobrança contra clientes e aprovadores e
  dano reputacional, o impacto é mais abrangente fora do sistema.
- **Contexto:** o abuso não corrompe dados internos, mas usa um canal legítimo (email) para atacar clientes e funcionários. O dano é externo e relacionado a reputação, difícil de reverter.
- **Controles existentes:** segredos no cofre corporativo; Gitleaks local e no CI.

### R16 — DoS no EventBus WebSocket (Médio, 3×2)

- **Origem:** CA13
- **Probabilidade (3):** endpoints WebSocket costumam ser alcançáveis, abrir
  muitas conexões ou publicar em volume é fácil.
- **Impacto (2):** notificações em tempo real atrasam ou se perdem; o núcleo de
  faturamento continua operando. Médio é adequado.
- **Contexto:** risco de disponibilidade restrito ao canal de notificações. O
  faturamento continua funcionando e o usuário pode recarregar a tela para ver o estado
  atual. Alinha-se a R11 e R14 como risco de disponibilidade, mas com menor alcance.
- **Controles existentes:** rate limit global de 60/min por IP (avaliar se cobre o `/ws`).

### R17 — Subscrição indevida no ws vaza faturamento (Médio, 2×2)

- **Origem:** T22 / CA29.
- **Probabilidade (2):** requer falta de autorização por canal na inscrição do ws.
- **Impacto (2):** vaza o estado de faturamento de um período, informações sensíveis e eventos.
  Porém, não há alteração de dados
- **Contexto:** o risco está associado a exposição não autorizada de informações de faturamento, restrita ao período e ao escopo da inscrição no ws. Embora possa comprometer a confidencialidade dos dados, a ausência de permissões de escrita limita os efeitos do incidente, sem possibilidade de alteração de registros ou interferência no processamento do faturamento.

### R18 — Autoaprovação sem segregação de funções (Crítico, 3×4)

- **Origem:** T24 / CA14.
- **Probabilidade (3):** a regra que impediria o autor do envio de aprovar o
  próprio lançamento não existe, basta uma conta `admin`.
- **Impacto (4):** fraude com trilha aparentemente legítima, o valor segue para o
  ERP como se tivesse passado por um fluxo completo de aprovação.
- **Contexto:** não depende de nenhuma falha técnica, apenas de uma regra de
  negócio ausente (princípio dos quatro olhos).

### R19 — Injeção de SQL no Oracle (Médio, 2×3)

- **Origem:** T25 / CA15.
- **Probabilidade (2):** existe a skill `sec-oracle`, mas SQL cru exige
  disciplina contínua no uso de bindvars.
- **Impacto (3):** o usuário Oracle é somente leitura, a injeção expõe dados
  legados fora do escopo do usuário, sem alteração.
- **Contexto:** `queries/` é o único lugar com SQL concatenado à mão, o que
  concentra a superfície de injeção.

### R20 — Configuração insegura em produção (`local` / `DEBUG`) (Alto, 2×4)

- **Origem:** T28 / CA28.
- **Probabilidade (2):** basta uma variável errada no deploy.
- **Impacto (4):** reabre autenticação local com senha e expõe o mapa completo da
  API em `/docs`.
- **Contexto:** ambos os comportamentos são trocados por variável de ambiente,
  sem barreira adicional.

### R21 — Isolamento insuficiente entre ambientes (Alto, 2×4)

- **Origem:** T32 / CA18.
- **Probabilidade (2):** a instância PostgreSQL é única, o isolamento depende da
  separação de usuários por schema.
- **Impacto (4):** credencial de QA pode alcançar o schema de produção, e testes
  de carga ou migrations de QA disputam recursos com produção.
- **Contexto:** relaciona-se a R14, pois o ambiente de QA também pode derrubar o
  banco de produção.

### R22 — Anexo malicioso contra aprovadores (Médio, 2×3)

- **Origem:** T29 / CA16.
- **Probabilidade (2):** a validação de MIME/extensão não detecta conteúdo
  malicioso.
- **Impacto (3):** pode comprometer a estação de quem tem perfil de aprovação.
- **Contexto:** o alvo são usuários privilegiados, o que pode abrir caminho para
  R02.

### R23 — Adulteração ou injeção de fórmula na carga ERP (Alto, 2×4)

- **Origem:** T30, T31 / CA19, CA20.
- **Probabilidade (2):** campos textuais exportados sem tratamento e arquivo
  armazenado sem hash ou assinatura.
- **Impacto (4):** o ERP confia no arquivo, e um erro vira lançamento contábil.
- **Contexto:** a adulteração ocorre depois do cálculo no servidor, fora da
  autoridade do sistema sobre o valor.

### R24 — Desvio de e-mail de aprovação (Médio, 2×3)

- **Origem:** T36 / CA17.
- **Probabilidade (2):** Usuário com acesso à central pode indicar destinatário não autorizado, sem validação suficiente de vínculo com o cliente. O cenário depende dessas condições específicas.
- **Impacto (3):** Informações financeiras de um cliente são enviadas a terceiro pelo serviço legítimo, comprometendo a confidencialidade e a confiança do cliente.
- **Contexto:** Diferente de R15, não exige chave de e-mail vazada nem falsificação de remetente; explora a funcionalidade normal de envio.
- **Controles existentes:** log de envio preserva destinatários e valores; permite rastrear, mas não impede o vazamento.

### R25 — Reuso de refresh token roubado (Alto, 2×4)

- **Origem:** T33 / CA21.
- **Probabilidade (2):** Atacante obtém refresh token ainda válido e o reuso não é impedido por rotação, revogação ou detecção suficiente; esses controles estão a confirmar. O cenário depende dessas condições específicas.
- **Impacto (4):** Renovação persistente de acesso sob a identidade da vítima; uma conta privilegiada permite exposição e alteração de dados em escala.
- **Contexto:** Complementa R02: avalia a manutenção do acesso pelo endpoint de renovação, mesmo após a expiração do token de acesso.
- **Controles existentes:** cookie de refresh com path restrito a `/v1/auth/refresh`; rotação a confirmar.

### R26 — Perda de auditoria por falha na gravação (Alto, 2×4)

- **Origem:** T34 / CA22.
- **Probabilidade (2):** Operação de negócio é confirmada antes da persistência da auditoria em background, e interrupção pode descartar registros sem recuperação garantida. O cenário depende dessas condições específicas.
- **Impacto (4):** Alterações financeiras permanecem efetivadas sem evidências suficientes para reconstrução e responsabilização, dificultando detectar e investigar fraudes.
- **Contexto:** Diferente de R08, os registros não chegam a ser persistidos; proteger registros existentes contra alteração não resolve essa lacuna.
- **Controles existentes:** `AuditMiddleware` registra requisições mutantes em background.

### R27 — Repúdio de aprovação por evidência insuficiente (Médio, 2×3)

- **Origem:** T35 / CA23.
- **Probabilidade (2):** Aprovação é associada ao usuário do token, mas as evidências disponíveis são insuficientes para esclarecer uma contestação de autoria. O cenário depende dessas condições específicas.
- **Impacto (3):** Dificuldade de responsabilização e de resolução de disputas sobre lançamentos aprovados, mesmo com registro da operação.
- **Contexto:** Diferente de R08 e R26, a evidência existe, mas é insuficiente para investigar a alegação de uso indevido da sessão.
- **Controles existentes:** timeline e `AuditMiddleware` associam a ação ao usuário extraído do token.

### R28 — Contorno de autorização por falha aberta do guard (Alto, 2×4)

- **Origem:** T14b / CA25.
- **Probabilidade (2):** Exceção na verificação de autorização é tratada como permissão, e usuário de privilégios limitados consegue provocar ou aproveitar essa falha. O cenário depende dessas condições específicas.
- **Impacto (4):** Execução de operações privilegiadas, como aprovação indevida ou ação administrativa, com possível comprometimento dos valores faturados.
- **Contexto:** Diferente de R03, o cenário abrange escrita e aprovação; a existência de falha aberta deve ser confirmada na implementação.
- **Controles existentes:** skill `sec-route` e testes automatizados, sem confirmação de cobertura das falhas de autorização.

### R29 — Alteração de lançamento por CSRF (Alto, 2×4)

- **Origem:** T27 / CA27.
- **Probabilidade (2):** Rota mutante aceita cookie de sessão enviado em requisição induzida; SameSite, validação de origem e proteção anti-CSRF são ausentes ou insuficientes, a confirmar. O cenário depende dessas condições específicas.
- **Impacto (4):** Alterações financeiras ou transições indevidas são executadas com as permissões da vítima e atribuídas à sua conta, podendo alcançar o ERP.
- **Contexto:** Complementa R01: a ação parte do navegador de uma vítima autenticada; requer que método, formato e envio do cookie permitam a requisição induzida.
- **Controles existentes:** cookie `HttpOnly`; política `SameSite` e proteção anti-CSRF a confirmar.

---

## 5. Priorização dos riscos

### 5.1 Critérios usados para ordenar

Além da pontuação (Probabilidade × Impacto), a ordem considera:

1. **Gravidade e escala da consequência** — dano financeiro, número de
   clientes/usuários afetados, dificuldade de reverter.
2. **Importância do ativo atingido** — ativos centrais ao propósito do sistema
   pesam mais que ativos periféricos.
3. **Dependências entre riscos** — quando um risco é pré-condição de outro, o
   risco-causa é tratado primeiro.
4. **Efeito habilitador** — riscos que abrem caminho para vários outros sobem
   na fila mesmo com pontuação igual a outros.
5. **Facilidade de detecção e recuperação** — quanto mais silenciosa e mais
   difícil de reverter a consequência, maior a urgência.

### 5.2 Tabela de priorização

| Ordem | Risco                                                | Nível   | Pontuação (P×I) | Critérios de 5.1 aplicados | Por que é tratado nesta posição                                                                                 |
| :---: | ---------------------------------------------------- | ------- | :-------------: | :------------------------: | --------------------------------------------------------------------------------------------------------------- |
|   1   | **R02** — Captura de conta/perfil SSO                | Crítico |    3×4 = 12     | 4                          | Porta de entrada que habilita R01, R03, R05, R08, R09. Crítico e de probabilidade média-alta (sem MFA).         |
|   2   | **R01** — Alteração/remoção de lançamentos           | Crítico |    3×4 = 12     | 1, 2                       | Ataca diretamente o valor faturado, objetivo central do sistema, com prejuízo financeiro imediato.              |
|   3   | **R18** — Autoaprovação sem segregação de funções    | Crítico |    3×4 = 12     | 1, 2, 5                    | Fraude com trilha aparentemente legítima, que depende apenas de uma regra ausente e de uma conta `admin`.       |
|   4   | **R06** — Vazamento do `JWT_SECRET`                  | Alto    |     2×4 = 8     | 3, 4                       | Sozinho não causa dano, mas é pré-condição de R07 (comprometimento total). Trata-se antes de R07.               |
|   5   | **R12** — Vazamento do `CELERY_CALLBACK_SECRET`      | Alto    |     2×4 = 8     | 3                          | Mesma classe de R06 e tratado junto com ele, pois o controle é o mesmo (cofre, rotação, varredura). Pré-condição de R13. |
|   6   | **R07** — Falsificar token                           | Alto    |     2×4 = 8     | 3                          | Consequência direta de R06, concede acesso total sob identidade forjada.                                        |
|   7   | **R03** — Acesso não autorizado a dados restritos    | Alto    |     3×3 = 9     | 4                          | Maior pontuação depois dos críticos e base ampla para R05 e para fraude, com muitas rotas expostas.             |
|   8   | **R09** — Alteração de regras de serviço             | Alto    |     2×4 = 8     | 1, 5                       | Corrompe o cálculo em escala de forma silenciosa, difícil de detectar depois.                                   |
|   9   | **R10** — Adulteração do motor de cálculo            | Médio   |     1×4 = 4     | 1, 5                       | Pontuação baixa (probabilidade baixa), mas gravidade e invisibilidade elevam a prioridade acima de vários Altos. |
|  10   | **R08** — Remoção/adulteração da auditoria           | Alto    |     2×4 = 8     | 4, 5                       | Protege a auditoria para responsabilização R01, R02 e R09. Sem ela, os demais abusos ficam irrastreáveis.       |
|  11   | **R05** — Extração de dados em volume                | Alto    |     2×4 = 8     | 1, 3                       | Maior consequência jurídica/reputacional. Depende de R03/R02, já tratados.                                      |
|  12   | **R23** — Adulteração ou injeção de fórmula na carga ERP | Alto |     2×4 = 8     | 1, 2, 5                    | O ERP confia no arquivo de carga, e a adulteração vira lançamento contábil sem passar pelo cálculo do servidor. |
|  13   | **R20** — Configuração insegura em produção          | Alto    |     2×4 = 8     | 4                          | Uma variável errada no deploy reabre a autenticação local e expõe o mapa da API.                                |
|  14   | **R13** — Falsificação de callbacks internos         | Médio   |     2×3 = 6     | 3                          | Consequência de R12, corrompe o processamento assíncrono.                                                       |
|  15   | **R21** — Isolamento insuficiente entre ambientes    | Alto    |     2×4 = 8     | 3                          | Uma das causas de indisponibilidade do banco de produção, tratado antes de R14.                                 |
|  16   | **R14** — Indisponibilidade do banco/infra           | Alto    |     2×4 = 8     | 5                          | Ponto único de dependência, com parada total, mas rebaixado pela recuperabilidade: é detectado de imediato e recuperável. |
|  17   | **R11** — DoS no fluxo de autorização                | Médio   |     2×2 = 4     | 5                          | Interrompe aprovação, recuperável e sem perda de dado.                                                          |
|  18   | **R16** — DoS no EventBus WebSocket                  | Médio   |     3×2 = 6     | 5                          | Degrada notificações, mas o núcleo segue operando.                                                              |
|  19   | **R22** — Anexo malicioso contra aprovadores         | Médio   |     2×3 = 6     | 4                          | O alvo são usuários com perfil de aprovação, o que pode abrir caminho para R02.                                 |
|  20   | **R04** — Acesso direto aos anexos no storage        | Médio   |     2×3 = 6     | 2                          | Exposição condicionada à má configuração, com escopo limitado.                                                  |
|  21   | **R19** — Injeção de SQL no Oracle                   | Médio   |     2×3 = 6     | 2                          | Usuário Oracle somente leitura, sem alteração de dados.                                                         |
|  22   | **R15** — Envio de e-mails maliciosos                | Médio   |     2×3 = 6     | 1                          | Impacto fora do sistema, mitigável por controle de remetente e do provedor.                                     |
|  23   | **R17** — Subscrição indevida no ws vaza faturamento | Médio   |     2×2 = 4     | 2                          | Escopo e impacto limitados, com correção pontual de autorização de canal.                                       |
| 24 | **R24** — Desvio de e-mail de aprovação | Médio | 2×3 = 6 | 1, 2 | Diferente de R15, não exige chave de e-mail vazada nem falsificação de remetente; explora a funcionalidade normal de envio. |
| 25 | **R25** — Reuso de refresh token roubado | Alto | 2×4 = 8 | 3, 4 | Complementa R02: avalia a manutenção do acesso pelo endpoint de renovação, mesmo após a expiração do token de acesso. |
| 26 | **R26** — Perda de auditoria por falha na gravação | Alto | 2×4 = 8 | 1, 5 | Diferente de R08, os registros não chegam a ser persistidos; proteger registros existentes contra alteração não resolve essa lacuna. |
| 27 | **R27** — Repúdio de aprovação por evidência insuficiente | Médio | 2×3 = 6 | 5 | Diferente de R08 e R26, a evidência existe, mas é insuficiente para investigar a alegação de uso indevido da sessão. |
| 28 | **R28** — Contorno de autorização por falha aberta do guard | Alto | 2×4 = 8 | 1, 4 | Diferente de R03, o cenário abrange escrita e aprovação; a existência de falha aberta deve ser confirmada na implementação. |
| 29 | **R29** — Alteração de lançamento por CSRF | Alto | 2×4 = 8 | 1, 4 | Complementa R01: a ação parte do navegador de uma vítima autenticada; requer que método, formato e envio do cookie permitam a requisição induzida. |

### 5.3 Sequência de tratamento

Vários riscos compartilham o mesmo controle (R06 e R12, por exemplo, se resolvem com o mesmo cofre). Por isso, os riscos são agrupados em estágios de tratamento, evitando tratar duas vezes o mesmo problema.

| Sequência | Tema | Riscos | Controle comum |
| ---- | ---- | ------ | -------------- |
| 1 | Identidade e segredos | R02, R06, R07, R12, R13, R25 | MFA, cofre com rotação, validação de token, HMAC nos callbacks |
| 2 | Integridade do valor faturado | R01, R09, R10, R08, R18,  R26, R27, R28, R29 | Segregação de funções, versionamento de regras, revisão obrigatória, auditoria imutável |
| 3 | Confidencialidade | R03, R05, R04, R17 | Testes de autorização, limites de exportação, URLs de curta duração, autorização por canal, auditoria durável, evidências de aprovação, negação de acesso em falhas |
| 4 | Disponibilidade | R14, R11, R16 | Isolamento do banco, limites de conexão, rate limit por usuário |
| 5 | Canal externo | R15, R24 | Destinatário amarrado ao cadastro, SPF/DKIM/DMARC |

