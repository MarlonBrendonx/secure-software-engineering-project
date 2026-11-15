# Etapa 6 — Resposta a incidentes

Este documento descreve o roteiro a seguir depois que uma das [regras de detecção](etapa-6-regras-de-deteccao.md) dispara, e quem é responsável por cada parte. O roteiro tem oito passos, da identificação ao pós-incidente.

## Roteiro de resposta

### 1. Identificação e registro

Ao receber um alerta:

- abrir um registro de incidente com número, regra, severidade, horário do alerta e responsável pela triagem;
- copiar imediatamente os eventos de auditoria e o trecho de log do período, a partir do `request_id`, do usuário e da origem. No protótipo isso é urgente, porque a lista `psp:audit` descarta as entradas mais antigas depois de 5.000 eventos. O script `exportar_evidencias.py` do [código proposto](#código-proposto) faz essa cópia;
- guardar a cópia com hash e horário, fora do ambiente afetado, para preservar a evidência caso o incidente envolva quem tem acesso ao servidor;
- não avisar o usuário suspeito antes da triagem, para não destruir evidências.

### 2. Triagem

A equipe de Segurança deve determinar se o evento é:

- **falso positivo:** o padrão tem explicação de negócio confirmada, como um analista consultando muitos clientes no fechamento do mês (D09) ou um gestor que esqueceu o dispositivo do MFA (D01). Fecha-se o registro com a justificativa e avalia-se o ajuste do limite;
- **tentativa sem sucesso:** o controle preventivo funcionou e não há operação efetivada, como as negações de D02 ou os tokens inválidos de D06 com assinatura incorreta. Contenção da origem e acompanhamento;
- **incidente confirmado:** há operação efetivada por quem não deveria, conta usada por terceiro, chave vazada ou dado divergente. Segue para a contenção com a severidade revista;
- **falha de controle:** o próprio mecanismo falhou, como em D10 e D11, mesmo sem atacante identificado. Segue para a contenção, porque durante a falha as demais regras podem não estar vendo nada.

A triagem deve responder também se há dado pessoal envolvido, o que define a comunicação do passo 7.

### 3. Contenção

A contenção deve ser proporcional ao risco e pode incluir:

- **revogar a sessão** (`sid`) da conta suspeita. O protótipo revoga uma sessão por vez (`SessionGateway.revoke`); a revogação de todas as sessões de um usuário ainda precisa ser criada. No reuso de refresh token (D05), o código proposto já revoga a sessão no momento da detecção;
- **bloquear a conta** no SSO até a confirmação do titular;
- **congelar o período** do cliente afetado, impedindo novos envios ao ERP, como previsto no tratamento de R01 e R02 na Etapa 2;
- **bloquear a origem** no gateway ou no APIM;
- **trocar a chave de assinatura do token** quando houver suspeita de vazamento (D06). No protótipo, trocar o `JWT_SECRET` invalida todos os tokens e derruba todas as sessões; com a chave assimétrica da decisão D04 da Etapa 3, a troca é feita por novo `kid`;
- **suspender a escrita** do módulo afetado quando a auditoria não estiver gravando (D11) ou o guard estiver falhando (D10);
- **manter bloqueada a importação** da carga do ERP (D14).

### 4. Investigação

A investigação deve correlacionar:

- os eventos de auditoria da conta e da sessão, em ordem, desde o primeiro login suspeito;
- o `request_id` dos eventos com o log da aplicação e com o log do gateway, para ver a requisição completa e a resposta dada;
- a origem do login com as origens das requisições seguintes, para perceber sessão usada a partir de outro lugar;
- as mudanças de status e de valor de cada lançamento com o histórico do próprio lançamento (`BillingItemHistory`), para achar alterações sem registro de auditoria;
- os eventos do SSO e do cofre de chaves no mesmo intervalo;
- outras contas acessadas pela mesma origem e outros alertas abertos no mesmo período.

O resultado é a lista dos registros lidos ou alterados pelo atacante, que define o que precisa ser corrigido e recomposto.

### 5. Correção

A correção trata a causa, e não só o efeito do incidente. Exemplos ligados aos achados das etapas anteriores:

- reuso de refresh token (D05, V01): implementar a rotação a cada uso, guardar o identificador do refresh e recusar o reaproveitamento, conforme o plano de R25. Está no [código proposto](#código-proposto);
- token também no corpo da resposta (V02): retirar o `access_token` do corpo do login e do refresh;
- biblioteca vulnerável (V03): atualizar o `PyJWT` e confirmar no Dependency-Check;
- regra que não disparou: criar o evento que faltou e um teste que o comprove.

Cada correção entra com um teste automatizado que reproduz o incidente e passa a rodar no CI, para a falha não voltar.

### 6. Recuperação

Quando aplicável:

- recompor o valor dos lançamentos alterados a partir da auditoria e do histórico, e reenviá-los pelo fluxo completo de aprovação;
- reverter as operações feitas pela conta comprometida, depois de validá-las com a área de negócio;
- regenerar a carga do ERP a partir das versões aprovadas e conferir assinatura, hash e total antes de liberar;
- restaurar o banco ou o Redis de backup quando houver dano que a auditoria não permite recompor;
- liberar a conta, o período e as rotas bloqueadas só depois de confirmar que a causa foi corrigida, e acompanhar a conta e a origem por pelo menos 7 dias.

### 7. Comunicação

A comunicação interna vai para Segurança, Desenvolvimento, Infraestrutura e para o gestor da área de faturamento, que decide sobre o congelamento do período e a recomposição dos valores. Quando os valores de um cliente da rede credenciada forem afetados, o gestor da área comunica o cliente antes do reenvio ao ERP.

Se houver dado pessoal envolvido, o encarregado de dados é avisado logo na triagem. Ele avalia se o incidente pode causar risco ou dano relevante aos titulares e, nesse caso, conduz a comunicação à ANPD e aos titulares, no prazo do Regulamento de Comunicação de Incidente de Segurança (Resolução CD/ANPD nº 15/2024).

A comunicação externa sai só pelo encarregado e pela gestão, nunca pela equipe técnica.

### 8. Pós-incidente

Após o encerramento:

- fazer uma revisão sem busca de culpados, com a linha do tempo, o tempo até a detecção e o tempo até a contenção;
- atualizar o [registro de riscos da Etapa 2](../etapa-2/etapa-2-criterios-e-registro.md), revendo a probabilidade do risco envolvido;
- ajustar limites e janelas das regras que dispararam tarde, cedo demais ou não dispararam;
- incluir no CI o teste que reproduz o incidente;
- guardar o registro do incidente e a evidência preservada pelo prazo da política de retenção.

## Responsabilidades

| Papel                                   | Responsabilidade principal                                                                                                      |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Segurança                               | Mantém as regras e os limites, recebe e faz a triagem dos alertas, coordena a resposta e decide a contenção de contas e origens |
| Desenvolvimento                         | Gera os eventos que as regras usam, corrige a causa no código, escreve o teste de regressão e apoia a investigação na auditoria |
| Infraestrutura                          | Mantém os logs do gateway, do SSO e do cofre, bloqueia origens, troca chaves, restaura backups e responde a D10 e D13           |
| Negócio (gestor da área de faturamento) | Confirma se uma alteração ou consulta é legítima, decide o congelamento do período e valida a recomposição dos valores          |
| Encarregado de dados                    | Avalia o incidente com dado pessoal e conduz a comunicação à ANPD e aos titulares                                               |

## Código proposto

O diretório [`etapa-6-resposta-a-incidentes/`](etapa-6-resposta-a-incidentes/) traz a correção do V01, que também gera o evento de D05, e o script do passo 1. Ele depende dos códigos de [objetivos e eventos](etapa-6-objetivos-e-eventos.md#código-proposto) e de [regras de detecção](etapa-6-regras-de-deteccao.md#código-proposto), que devem ser aplicados antes.

| Arquivo                                         | O que muda                                                                                                                                                                         |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/domain/entities/session.py`                | A sessão guarda o `jti` do único refresh token aceito (`refresh_jti`)                                                                                                              |
| `src/application/use_cases/auth/login.py`       | O login grava o `jti` do refresh emitido. A renovação troca o `jti` a cada uso; um refresh com `jti` antigo revoga a sessão e responde `401 refresh_reutilizado`. A renovação não estende o prazo da sessão |
| `src/infrastructure/persistence/redis/codec.py` | Lê e grava o `refresh_jti` da sessão. Inclui a mudança de [objetivos e eventos](etapa-6-objetivos-e-eventos.md#código-proposto) e a substitui                                       |
| `scripts/exportar_evidencias.py` (novo)         | Copia `psp:audit` e `psp:alerts` para um JSON com o hash SHA-256 ao lado, com filtro opcional por usuário, origem ou `request_id`. Só lê o Redis e não sobrescreve cópia anterior |

As sessões abertas antes da troca não têm `refresh_jti`. A primeira renovação delas é aceita e já grava o valor, então ninguém precisa entrar de novo.

Ficaram fora do código:

- **V02 (token no corpo da resposta).** O frontend lê o `access_token` do corpo do login e do refresh, inclusive para autenticar o WebSocket por mensagem. Tirar o token do corpo exige mudar o frontend e a autenticação do WebSocket, o que vai além desta etapa.
- **V03 (`PyJWT` com CVE).** A correção é atualizar a dependência e confirmar no Dependency-Check, não mudar código.
- **Revogação de todas as sessões de um usuário.** Exige indexar as sessões por usuário no `security_gateways.py`, que é diferente no protótipo original e no corrigido. Fica para depois do consenso sobre qual protótipo segue.

---
