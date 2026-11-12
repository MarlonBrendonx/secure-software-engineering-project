# Etapa 6 — Monitoramento, detecção e resposta a incidentes

## Status

Esta etapa parte dos controles de detecção que as etapas anteriores deixaram previstos, mas sem regra própria: o C7 (monitoramento e alertas) da [arquitetura segura](../docs/etapa-3/etapa-3-diagrama.md#2-controles-posicionados-no-diagrama), a coluna Detect do [mapeamento NIST CSF](../docs/etapa-2/etapa-2-nist-csf.md#81-análise-de-cada-relação) e a frase "geram alerta para a equipe de segurança" nos critérios de RS01 a RS08 dos [requisitos](../docs/etapa-3/etapa-3-requisitos.md#requisitos). Também usa os achados V01 a V03 do [retest autenticado](../docs/etapa-5/etapa-5-retest-autenticado.md) da Etapa 5.

O documento propõe 14 regras de detecção (D01 a D14) e um roteiro de resposta. Os identificadores D01 a D14 desta etapa são **regras de detecção** e não se confundem com as decisões de arquitetura D01 a D08 da Etapa 3. Quando uma regra cita uma decisão, ela aparece como "decisão D0x da Etapa 3".

A situação de cada regra no [protótipo](../extra/prototipo-psp/) é esta:

| Situação no protótipo                         | Regras                      | O que existe                                                                                                                                                         |
| --------------------------------------------- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Alerta implementado e testado                 | D01                         | `SecurityMonitor` conta `mfa_invalido` e `mfa_ausente` por usuário e dispara `mfa_falhas_repetidas`. O teste `test_falhas_repetidas_de_mfa_geram_alerta` cobre o caso. |
| Alerta implementado, sem teste do alerta      | D02                         | O mesmo monitor conta `acesso_negado` e dispara `acesso_negado_repetido`. Os testes conferem o registro da negação, mas não o alerta.                                   |
| Evento registrado, sem regra de alerta        | D03, D04, D08               | `login_falha`, `login_sucesso`, `regra_servico_atualizada` e `regra_servico_excluida` ficam na auditoria, mas nada os correlaciona.                                    |
| Sinal só no log ou na resposta HTTP           | D06, D10, D12, D13          | Token recusado (`401`), falha do guard (`503`), WebSocket fechado por origem (`4403`) e limite excedido (`429`) não chegam à auditoria.                                |
| Evento não gerado                             | D05, D07, D09, D11, D14     | Faltam o controle que produz o evento (rotação do refresh, autoaprovação, outbox, carga do ERP) ou o registro da leitura.                                             |

Nada aqui é uma capacidade operacional. O alerta do protótipo é um `logger.warning` mais uma entrada na lista `psp:alerts` do Redis, sem destinatário, sem fila de tratamento e sem plantão.

## Objetivos de monitoramento

O monitoramento proposto deve permitir:

- perceber o uso de uma conta privilegiada capturada (R02) antes que ela aprove ou altere lançamentos, a partir das falhas no segundo fator, das falhas de senha e dos logins fora do padrão;
- perceber a busca de dados fora do escopo (R03) e a extração em volume (R05), que a resposta `404` esconde do atacante, mas não deve esconder da equipe de segurança;
- perceber tentativas de mudar o valor faturado por fora da máquina de estados (R01, R18) e mudanças em regras de serviço (R09), que alteram valores de forma silenciosa;
- perceber o uso de tokens forjados, de sessões revogadas e de refresh tokens reaproveitados (R06, R07, R25 e o achado V01);
- perceber quando os próprios controles falham: guard indisponível (R28), auditoria com lacuna (R26) e carga do ERP divergente (R23);
- reconstruir, depois de um alerta, quem fez o quê, de onde, com qual sessão e sobre qual registro, para conter, corrigir e recompor os valores.

## Eventos mínimos a registrar

Cada evento deve ter estes campos, além do tipo:

| Campo                  | Para que serve                                                    | No protótipo (`AuditEvent`)                                    |
| ---------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------- |
| Data e hora (UTC)      | Ordenar a linha do tempo                                          | `created_at`                                                   |
| Usuário e perfil       | Saber quem agiu e com qual privilégio                             | Só `user`; o perfil não é gravado                              |
| Sessão (`sid`)         | Ligar ações da mesma sessão e revogá-la                           | Não é gravado                                                  |
| Origem (IP)            | Correlacionar contas atacadas pela mesma origem                   | `origin`, só nos eventos de login e de MFA                     |
| Rota e método          | Saber qual operação foi tentada                                   | `route`, só em `mfa_ausente`                                   |
| Recurso e identificador| Saber qual registro foi lido ou alterado                          | `resource` e `resource_id`                                     |
| Operação e resultado   | Distinguir tentativa de efetivação e o motivo da recusa           | Parte em `detail`; o resultado não tem campo próprio           |
| `request_id`           | Ligar o evento ao log da aplicação e à resposta dada ao cliente   | Gerado pelo middleware e devolvido em `X-Request-ID`, mas não gravado no evento |

Os eventos que precisam existir, por grupo:

1. **Autenticação:** login com sucesso (com `amr`), login recusado por credenciais, código MFA recusado, token de perfil privilegiado sem MFA, renovação de sessão, reuso de refresh token, logout e revogação de sessão.
2. **Token e sessão:** token recusado por assinatura, algoritmo, `iss`, `aud`, `exp` ou `kid`, e token recusado por `sid` revogado ou inexistente.
3. **Autorização:** negação por escopo (cliente ou período), negação por perfil (`403`) e negação por falha do guard (`503`).
4. **Integridade do faturamento:** criação, alteração e exclusão de lançamento, cada transição de status, tentativa recusada de alteração após o envio, transição recusada e autoaprovação recusada.
5. **Cadastros:** criação, alteração e exclusão de regra de serviço, com os nomes dos campos alterados.
6. **Leitura e exportação:** consultas e exportações de lançamentos, com o volume devolvido.
7. **Plataforma:** requisição recusada por origem ou por token anti-CSRF, conexão WebSocket recusada, limite de requisições excedido, erro interno (`500`), falha na gravação da auditoria, atraso da outbox e divergência na reconciliação.
8. **Carga do ERP:** geração do arquivo, conferência do manifesto e bloqueio da importação.

Os grupos 1 (exceto renovação, reuso e revogação), 3 (só a negação por escopo), 4 (só as operações efetivadas) e 5 já são gravados pelo protótipo. Os demais dependem de controles ainda não implementados ou do registro de eventos que hoje só aparecem no log ou na resposta HTTP.

O registro não deve conter senha, código OTP, token nem valor de campo sensível. O protótipo já segue essa regra: `regra_servico_atualizada` grava só os nomes dos campos alterados.

## Fontes de dados e cobertura

| Fonte                                       | Eventos principais                                                                                                                         | Uso                                                                                         |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Auditoria da API (`audit_logs`; `psp:audit` no protótipo) | Login, logout, MFA, negação por escopo, mudanças em lançamentos e regras de serviço                                                         | Base das regras D01 a D04, D07 e D08 e da reconstrução da linha do tempo                     |
| Contadores e alertas (`SecurityMonitor`, `psp:alerts`) | Contagem por usuário em janela de 10 minutos e alertas disparados                                                                             | Disparo de D01 e D02; modelo para as demais regras de contagem                               |
| Log da aplicação (`psp.api`, `psp.api.ws`, `psp.security`) | Exceção no guard, erro `500`, fechamento do WebSocket por origem ou autenticação                                                             | D10 e D12 enquanto esses eventos não forem para a auditoria                                  |
| Gateway, APIM ou proxy reverso              | Código de resposta por rota, origem e usuário (`401`, `403`, `404`, `429`), volume por origem                                              | D06, D09 e D13; visão de quem nunca chega a se autenticar                                    |
| SSO corporativo (Keycloak)                  | Login, falha de senha, falha de MFA, bloqueio de conta, novo dispositivo                                                                    | D01, D03 e D04 no sistema real, onde o login mock do protótipo dá lugar ao SSO               |
| Cofre de chaves (KMS)                       | Cada uso da chave de assinatura do token e da chave do gerador da carga                                                                    | D06 (uso da chave fora do emissor, previsto em RS04)                                         |
| Outbox e reconciliação (RS05)               | Atraso de entrega, falha de entrega, lacuna entre versões dos lançamentos e `audit_logs`                                                   | D11                                                                                          |
| Entrega da carga ao ERP (RS07)              | Assinatura inválida, hash divergente, total diferente da soma aprovada                                                                     | D14                                                                                          |
| Pipeline de CI (Gitleaks, Dependency-Check) | Segredo no repositório, dependência com CVE (como o `PyJWT` do V03)                                                                         | Não é detecção em execução; abre incidente quando há segredo exposto ou CVE explorável       |

A auditoria do protótipo fica em uma lista do Redis limitada a 5.000 entradas (`_AUDIT_MAX_ENTRIES`), sem encadeamento por hash. Ela serve para testar as regras, mas não é a trilha protegida de C6 e não guarda histórico suficiente para uma investigação.

## Regras de detecção propostas

As janelas e os limites são valores iniciais, a ajustar com o volume real de uso. D01 e D02 usam os mesmos valores já configurados no `SecurityMonitor` (5 e 10 eventos em 600 segundos).

| ID  | Evento observado                                  | Condição de acionamento                                                                                                                           | Destino        | Ação inicial                                                                                              | Risco         |
| --- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | --------------------------------------------------------------------------------------------------------- | ------------- |
| D01 | `mfa_invalido` e `mfa_ausente`                    | 5 ou mais falhas no segundo fator para o mesmo usuário em 10 minutos                                                                              | Segurança      | Confirmar com o titular por outro canal; se ele não reconhecer, revogar as sessões e bloquear a conta     | R02           |
| D02 | `acesso_negado` (escopo de cliente ou período)    | 10 ou mais negações para o mesmo usuário em 10 minutos                                                                                            | Segurança      | Listar os identificadores pedidos e verificar se são sequenciais ou de outros clientes; revogar a sessão se for enumeração | R03, R05      |
| D03 | `login_falha`                                     | 10 ou mais falhas para o mesmo usuário em 10 minutos, ou falhas em 5 ou mais usuários distintos a partir da mesma origem em 10 minutos             | Segurança      | Bloquear a origem no gateway; avisar os titulares das contas atingidas                                    | R02           |
| D04 | `login_sucesso` de `admin` ou `manager`           | Login com sucesso depois de D03 ter disparado para a mesma conta, ou a partir de origem nunca vista para essa conta nos últimos 30 dias            | Segurança      | Confirmar com o titular; se não reconhecer, revogar a sessão e rever as ações feitas nela                  | R02           |
| D05 | Renovação com refresh token já usado              | Qualquer ocorrência                                                                                                                               | Segurança      | Revogar a sessão (`sid`) e todos os tokens dela; avisar o titular                                        | R25 (V01)     |
| D06 | Token recusado (assinatura, `alg`, `iss`, `aud`, `kid` ou `sid` revogado) | Qualquer token com assinatura válida e `sid` desconhecido; 3 ou mais tokens com assinatura inválida da mesma origem em 10 minutos; uso da chave de assinatura fora do emissor | Segurança      | Bloquear a origem; se a assinatura for válida e o `sid` desconhecido, tratar como vazamento da chave       | R06, R07      |
| D07 | Alteração de lançamento após o envio, transição recusada ou autoaprovação | Qualquer `PATCH` ou `DELETE` recusado em lançamento enviado, qualquer autoaprovação recusada; 3 ou mais transições recusadas do mesmo usuário em 10 minutos | Segurança, Negócio | Verificar se o lançamento foi alterado por outro caminho; congelar o período do cliente se houver dúvida | R01, R18      |
| D08 | `regra_servico_atualizada` e `regra_servico_excluida` | Alteração de campo de cálculo (tipo, valor, faixas) em regra com lançamentos do período aberto, ou 5 ou mais alterações do mesmo usuário em 1 hora | Negócio, Segurança | Confirmar a alteração com o gestor da área; comparar os lançamentos calculados antes e depois             | R09           |
| D09 | Consultas e exportações de lançamentos           | Volume do usuário acima de 3 vezes a sua média dos últimos 30 dias, ou leitura de clientes que ele não consultou nos últimos 30 dias             | Segurança      | Verificar com o gestor do usuário se a consulta tem motivo de negócio; suspender a exportação se não tiver | R05           |
| D10 | Falha na verificação de acesso (`503`)           | 3 ou mais em 5 minutos, ou qualquer `503` seguido de `2xx` na mesma rota e sessão                                                                 | Infraestrutura, Segurança | Verificar Redis, banco e serviço de identidade; se houver `2xx` depois da falha, investigar operações efetivadas | R28           |
| D11 | Auditoria e outbox                                | Qualquer falha de gravação da auditoria, evento parado na outbox por mais de 5 minutos ou divergência na reconciliação                            | Desenvolvimento, Segurança | Suspender as operações de escrita do módulo afetado até a reconciliação fechar                             | R26, R08      |
| D12 | Requisição recusada por origem ou token anti-CSRF; WebSocket fechado com `4403` | 3 ou mais recusas para o mesmo usuário em 10 minutos, ou recusa vinda de origem corporativa conhecida                                             | Segurança      | Identificar a página de origem; revogar a sessão do usuário se a requisição alterou algo                  | R29, R17      |
| D13 | Limite de requisições excedido (`429`)           | Mais de 100 respostas `429` para a mesma origem em 10 minutos                                                                                     | Infraestrutura, Segurança | Bloquear a origem no gateway e verificar se é varredura                                                   | R11, R16      |
| D14 | Conferência da carga do ERP                       | Qualquer divergência de assinatura, hash ou total                                                                                                 | Negócio, Segurança | Manter a importação bloqueada; regenerar a carga a partir das versões aprovadas                         | R23           |

D13 teria disparado durante o active scan do retest da Etapa 5, que recebeu 8.306 respostas `429` do backend. D06 teria disparado nos testes de JWT forjado do mesmo retest (`alg=none`, assinatura trocada e `role=admin` no corpo), que receberam `401` sem deixar registro na auditoria.

Em D02, as negações de período feitas na listagem (`ListBillingsByPeriodUseCase`) gravam `acesso_negado` direto na auditoria, sem passar pelo `SecurityMonitor`, e por isso não entram no contador. A correção é usar o monitor também nesse caso.

## Severidade inicial dos alertas

A severidade segue a escala da [Etapa 2](../docs/etapa-2/etapa-2-criterios-e-registro.md): o impacto do risco de origem e a chance de o alerta indicar um ataque em andamento, e não um erro do usuário.

| Regra | Severidade inicial | Justificativa                                                                |
| ----- | ------------------ | ---------------------------------------------------------------------------- |
| D01   | Alta               | Indica senha já conhecida por terceiro em conta que aprova lançamentos (R02, Crítico). Não é Crítica porque o segundo fator ainda barrou o acesso. |
| D02   | Alta               | A enumeração de identificadores é o primeiro passo de R03 e R05. O `404` impede o acesso, mas confirma que alguém está procurando. |
| D03   | Média              | Falha de senha tem muito ruído de digitação. Sobe para Alta quando a mesma origem atinge vários usuários. |
| D04   | Crítica            | Uma conta privilegiada pode estar em uso por terceiro neste momento.          |
| D05   | Alta               | O reuso só acontece se o refresh foi copiado. É o cenário do V01.            |
| D06   | Crítica (assinatura válida com `sid` desconhecido ou uso da chave fora do emissor); Média (assinatura inválida) | Assinatura válida fora de uma sessão real só é possível com a chave, e a chave vazada permite criar token de `admin` com MFA (R07). Assinatura inválida é tentativa sem sucesso. |
| D07   | Alta               | Tentativa direta de mudar valor já enviado ou de aprovar o próprio lançamento (R01 e R18, Críticos). A máquina de estados recusou, por isso não é Crítica. |
| D08   | Média              | A alteração de regra é função legítima, mas muda valores sem aparecer no lançamento (R09). Sobe para Alta se o gestor não reconhecer. |
| D09   | Média              | Leitura em volume é permitida pelo perfil e tem falsos positivos em fechamento de mês. |
| D10   | Alta               | Indica que o controle de acesso está indisponível. Sobe para Crítica se houver `2xx` depois da falha, o que seria falha aberta (R28). |
| D11   | Crítica            | Sem auditoria as demais regras deixam de ver as operações, e a recomposição de valores fica impossível (R26). |
| D12   | Média              | A recusa mostra que a proteção funcionou. Sobe para Alta se a requisição de outra origem chegou a alterar dado. |
| D13   | Baixa              | O limite já conteve o excesso. Serve para identificar varreduras.            |
| D14   | Crítica            | Valor divergente às portas do ERP vira lançamento contábil se a importação for liberada (R23). |

## Roteiro de resposta a incidentes

### 1. Identificação e registro

Ao receber um alerta:

- abrir um registro de incidente com número, regra, severidade, horário do alerta e responsável pela triagem;
- copiar imediatamente os eventos de auditoria e o trecho de log do período, a partir do `request_id`, do usuário e da origem. No protótipo isso é urgente, porque a lista `psp:audit` descarta as entradas mais antigas depois de 5.000 eventos;
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

- **revogar a sessão** (`sid`) da conta suspeita. O protótipo revoga uma sessão por vez (`SessionGateway.revoke`); a revogação de todas as sessões de um usuário ainda precisa ser criada;
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

- reuso de refresh token (D05, V01): implementar a rotação a cada uso, guardar o identificador do refresh e recusar o reaproveitamento, conforme o plano de R25;
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
- atualizar o [registro de riscos da Etapa 2](../docs/etapa-2/etapa-2-criterios-e-registro.md), revendo a probabilidade do risco envolvido;
- ajustar limites e janelas das regras que dispararam tarde, cedo demais ou não dispararam;
- incluir no CI o teste que reproduz o incidente;
- guardar o registro do incidente e a evidência preservada pelo prazo da política de retenção.

## Responsabilidades

| Papel           | Responsabilidade principal                                                          |
| --------------- | ----------------------------------------------------------------------------------- |
| Segurança       | Mantém as regras e os limites, recebe e faz a triagem dos alertas, coordena a resposta e decide a contenção de contas e origens |
| Desenvolvimento | Gera os eventos que as regras usam, corrige a causa no código, escreve o teste de regressão e apoia a investigação na auditoria |
| Infraestrutura  | Mantém os logs do gateway, do SSO e do cofre, bloqueia origens, troca chaves, restaura backups e responde a D10 e D13 |
| Negócio (gestor da área de faturamento) | Confirma se uma alteração ou consulta é legítima, decide o congelamento do período e valida a recomposição dos valores |
| Encarregado de dados | Avalia o incidente com dado pessoal e conduz a comunicação à ANPD e aos titulares |

## Validação das regras

A aplicação já permite gerar parte dos eventos de entrada. Cada regra ainda precisa de um teste controlado que comprove correlação e alerta, não apenas a negação preventiva da operação.

| Regra | Teste planejado                                                                         | Evidência esperada                        |
| ----- | --------------------------------------------------------------------------------------- | ----------------------------------------- |
| D01   | Cinco chamadas de gestor sem MFA em rota de aprovação (já existe: `test_falhas_repetidas_de_mfa_geram_alerta`) | Cinco `mfa_ausente` na auditoria e um único `mfa_falhas_repetidas` em `psp:alerts` |
| D02   | Analista pede 10 lançamentos de cliente fora do escopo, incluindo listagem por período fora do escopo | Dez `acesso_negado` e um `acesso_negado_repetido`; as negações de período também contadas |
| D03   | Onze logins com senha errada para o mesmo usuário e um login errado para cinco usuários a partir da mesma origem | Alerta por usuário e alerta por origem, sem expor qual usuário existe |
| D04   | Gestor com D03 disparado faz login com sucesso                                         | Alerta Crítico com usuário, origem e `sid` |
| D05   | Renovar a sessão e reapresentar o refresh antigo (o caso do V01)                        | `401` no reuso, sessão revogada, evento de reuso e alerta |
| D06   | Repetir os tokens forjados do retest (`alg=none`, assinatura trocada, `role=admin`) e um token válido com `sid` revogado | Eventos de token recusado com motivo; alerta Médio para assinatura inválida e Crítico para `sid` desconhecido com assinatura válida |
| D07   | `PATCH` e `DELETE` em lançamento aguardando aprovação; transição não permitida; autoaprovação | Recusa, evento com usuário, lançamento, operação e motivo, e alerta |
| D08   | Alterar o tipo e o valor de uma regra com lançamentos no período aberto                 | `regra_servico_atualizada` com os campos e alerta para o Negócio |
| D09   | Analista consulta todos os clientes do escopo em sequência, acima do volume de referência | Evento de leitura com volume e alerta     |
| D10   | Derrubar o Redis durante uma requisição autenticada                                     | `503` sem detalhe interno, nenhuma operação efetivada, evento de falha do guard e alerta |
| D11   | Simular erro na gravação da auditoria durante uma alteração de lançamento               | Operação desfeita, erro ao usuário e alerta de falha de auditoria |
| D12   | Abrir o WebSocket com `Origin` de outro site três vezes; requisição de escrita sem token anti-CSRF | Fechamento `4403` e `403` registrados na auditoria e alerta |
| D13   | Mais de 100 requisições à rota de login da mesma origem                                  | `429` a partir da 11ª no minuto e um alerta de varredura |
| D14   | Alterar o total de um arquivo de carga depois de gerado                                 | Importação bloqueada, alerta e carga regenerada igual à original |

Os testes de D01 e D02 podem rodar já no protótipo. D03, D04, D08 e D13 precisam só da regra, porque os eventos de entrada existem ou são fáceis de gravar. D05, D06, D07, D10 e D12 precisam primeiro gravar o evento na auditoria. D11 e D14 dependem de controles que ainda não existem (outbox e carga do ERP).

## Relação com o NIST CSF 2.0

Esta etapa se relaciona principalmente às funções:

- **Detect:** observação, correlação e identificação de eventos suspeitos;
- **Respond:** triagem, contenção, investigação, comunicação e correção;
- **Recover:** restauração de serviço ou informação e retorno controlado à operação.

As funções estão representadas como planejamento de segurança. A documentação não implica que uma capacidade operacional de SOC, SIEM, IDS ou resposta automatizada já exista.

Nas categorias usadas na [Etapa 2](../docs/etapa-2/etapa-2-nist-csf.md#72-categorias-do-csf-20-usadas-no-mapeamento), as regras D01 a D14 e as fontes de dados correspondem a DE.CM (monitoramento contínuo) e DE.AE (análise de eventos adversos). A triagem e a investigação correspondem a RS.MA e RS.AN, a contenção e a correção a RS.MI, e a comunicação a RS.CO. A recomposição dos valores e a regeneração da carga correspondem a RC.RP, e o aviso ao cliente da rede sobre a correção a RC.CO.

## Limitações

- **Só D01 está implementada e testada.** D02 tem alerta, mas sem teste do alerta. As outras doze regras são propostas.
- **O alerta do protótipo não chega a ninguém.** Ele vai para o log e para uma lista no Redis. Não há SIEM, fila de tratamento nem plantão, e o tempo de resposta não pode ser medido.
- **A auditoria do protótipo não serve como evidência.** Fica no Redis, em lista limitada a 5.000 entradas, sem encadeamento por hash e gravada depois da operação, não na mesma transação. Quem tem acesso ao Redis apaga o próprio rastro, que é exatamente o R08 e o R26.
- **Faltam campos para correlacionar.** O evento não grava perfil, `sid`, `request_id` nem resultado, e a origem só aparece nos eventos de login e de MFA.
- **Os limites não foram calibrados.** Os números das regras são estimativas. Sem histórico de uso real, não se sabe quantos falsos positivos D03, D08 e D09 gerariam.
- **O contador é por usuário e com janela fixa.** O `SecurityMonitor` não pega um ataque espalhado por várias contas nem um ataque lento que fique abaixo do limite em cada janela. D03 e D06 pedem contagem também por origem.
- **O login é simulado.** No sistema real, as falhas de senha e de MFA acontecem no SSO, e D01, D03 e D04 dependem dos eventos do Keycloak, que não foram observados.
- **Não há detecção de rede nem de host.** Esta etapa cobre só eventos da aplicação. Um acesso direto ao banco, ao Redis ou ao storage, fora da API, não é percebido por nenhuma regra.
- **O roteiro de resposta não foi exercitado.** Não houve simulação de incidente, e os papéis da tabela de responsabilidades ainda não têm pessoas nomeadas.
