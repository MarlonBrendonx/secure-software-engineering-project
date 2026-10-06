# Etapa 2 — Critérios de avaliação e registro de riscos

## 2. Critérios de avaliação

### 2.1 Critérios de probabilidade

| Valor | Classificação | Critério                                                                                      |
| :---: | ------------- | --------------------------------------------------------------------------------------------- |
|   1   | Baixa         | O evento depende de condições incomuns, acesso muito específico ou grande capacidade técnica. |
|   2   | Média-baixa   | O evento é possível, mas depende de uma vulnerabilidade ou condição específica.               |
|   3   | Média-alta    | O evento é plausível e pode ocorrer em situações comuns de uso ou ataque.                     |
|   4   | Alta          | O evento pode ocorrer com facilidade, frequência ou durante condições previsíveis do sistema. |

A probabilidade de cada risco é calculada e justificada no documento [Justificativa das avaliações](etapa-2-avaliacao-e-priorizacao.md#justificativas-das-avaliações) com base nas caracteristicas do sistema

### 2.2 Critérios de impacto

| Valor | Classificação | Critério                                                                              |
| :---: | ------------- | ------------------------------------------------------------------------------------- |
|   1   | Baixo         | Causa pequeno transtorno e pode ser corrigido rapidamente.                            |
|   2   | Moderado      | Causa interrupção ou inconsistência limitada, com possibilidade de recuperação.       |
|   3   | Alto          | Causa prejuízo relevante aos usuários, ao negócio, à administração ou à privacidade.  |
|   4   | Muito alto    | Pode afetar muitos usuários, comprometer operações críticas ou causar prejuízo grave. |

Por outro lado, na avaliação do impacto foram considerados conforme o contexto do software, ou seja, prejuízo financeiro,
como o valor lançado nos faturamentos, vazamentos de dados de terceiros como CPNJ, anexos, e-mails, conforme a LGPD. Além disso,
a avaliação lida também com quedas e interrupções

### 2.3 Cálculo e classificação

Pontuação = **Probabilidade × Impacto**.

| Pontuação | Nível do risco |
| :-------: | -------------- |
|   1 a 3   | Baixo          |
|   4 a 7   | Médio          |
|  8 a 11   | Alto           |
|  12 a 16  | Crítico        |

## 3. Registro de riscos

Cada risco deriva de uma ou mais ameaças STRIDE da Etapa 1. Quando uma ameaça
tem consequências distintas, ela origina mais de um risco. Por exemplo, o
vazamento de uma chave (T15) e a sua exploração para falsificar tokens (T16)
são riscos separados, R06 e R07, porque têm probabilidade, impacto e tratamento
diferentes.

| ID  | Origem STRIDE                                            | Evento de risco                                                                                                   | Vulnerabilidade ou condição                                                                         |  P  |  I  | Pont. | Nível       |
| --- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | :-: | :-: | :---: | ----------- |
| R01 | Tampering (T01), A1                                      | Usuário com escrita altera ou remove lançamentos e o valor adulterado chega ao ERP como legítimo                  | Perfil `analista`/`admin` com escrita, aprovação pode não detectar a adulteração                    |  3  |  4  |  12   | **Crítico** |
| R02 | Spoofing / EoP (T02), A1, A2, A3                         | Atacante captura conta privilegiada (`admin`/`gestor`) via SSO e opera em nome da vítima                          | Phishing/sessão vazada, ausência de verificação adicional (MFA) e de detecção de sessão anômala     |  3  |  4  |  12   | **Crítico** |
| R03 | Elevation of Privilege (T03,T07,T09,T11), A1, A4, A5, A6 | Usuário lê dados restritos ao seu perfil (lançamentos, anexos, CNPJ, e-mails) por falha de autorização            | Verificação de autorização ausente/inconsistente em rota, endpoint de anexo ou consulta (IDOR/BOLA) |  3  |  3  |   9   | Alto        |
| R04 | Elevation of Privilege (T19), A11                        | Acesso direto aos anexos no storage, fora do controle da aplicação                                                | URL assinada mal configurada (validade longa, sem escopo) ou vazamento de credencial de storage     |  2  |  3  |   6   | Médio       |
| R05 | Information Disclosure (T04,T08,T10,T12), A1, A4, A5, A6 | Exfiltração em volume de dados críticos (lançamentos, anexos, CNPJ, e-mails)                                      | Ator já com leitura (perfil, conta capturada ou R03) e ausência de limite/monitoração de extração   |  2  |  4  |   8   | Alto        |
| R06 | Information Disclosure (T15), A9                         | Vazamento do `JWT_SECRET`                                                                                         | Segredo em repositório, log, imagem ou variável de ambiente exposta, sem cofre/rotação              |  2  |  4  |   8   | Alto        |
| R07 | Spoofing (T16), A9                                       | Uso do `JWT_SECRET` vazado para forjar token e impersonar usuário, inclusive `admin`                              | Assinatura de token depende só do segredo, sem verificação adicional de sessão/dispositivo          |  2  |  4  |   8   | Alto        |
| R08 | Repudiation (T05), A2                                    | Remoção ou adulteração da timeline de auditoria para apagar o rastro                                              | Timeline mutável, operação capaz de remover/alterar registros, sem trilha imutável                  |  2  |  4  |   8   | Alto        |
| R09 | Tampering (T06), A3                                      | Alteração não autorizada de regra de serviço/faixa corrompe todos os cálculos futuros                             | Permissão de escrita em serviços, alteração se propaga de forma silenciosa aos cálculos             |  2  |  4  |   8   | Alto        |
| R10 | Tampering (T13), A7                                      | Adulteração do motor de cálculo via código/pipeline fatura errado em escala                                       | Insider com acesso ao repositório ou cadeia de build comprometida, revisão/testes contornados       |  1  |  4  |   4   | Médio       |
| R11 | Denial of Service (T14), A8                              | Sobrecarga da máquina de estados/guards de autorização paralisa o fluxo de aprovação                              | Endpoints de transição sem limite de requisições, guards custosos por chamada                       |  2  |  2  |   4   | Médio       |
| R12 | Information Disclosure (T17), A10                        | Vazamento do `CELERY_CALLBACK_SECRET`                                                                             | Segredo exposto em repositório/log/config, única barreira dos callbacks internos                    |  2  |  4  |   8   | Alto        |
| R13 | Spoofing (T18), A10                                      | Código malicioso forja callbacks internos com a chave vazada e injeta operações falsas                            | Callback validado só pela chave, sem verificação de origem (mTLS/rede) nem idempotência             |  2  |  3  |   6   | Médio       |
| R14 | Denial of Service (T20), A12                             | Indisponibilidade do PostgreSQL/infra deixa o sistema inoperante                                                  | Carga excessiva, exaustão de conexões ou ataque à infraestrutura, sem limites/isolamento            |  2  |  4  |   8   | Alto        |
| R15 | Spoofing (T21), A13/A14                                  | Envio de e-mails maliciosos em nome da empresa (phishing/fraude de cobrança) com a `EMAIL_SERVICE_API_KEY` vazada | Chave do serviço de e-mail exposta, ausência de proteção de remetente (SPF/DKIM/DMARC)              |  2  |  3  |   6   | Médio       |
| R16 | Denial of Service (T23), A15                             | Sobrecarga do EventBus WebSocket impede a entrega de notificações de faturamento                                  | Conexões/eventos sem limite, sem controle de taxa nem quota por conexão                             |  3  |  2  |   6   | Médio       |
| R17 | Information Disclosure (T22), A15                        | Subscrição indevida no canal `billing:{AAAA-MM}` vaza o estado de faturamento do período                          | Falta de validação de autorização por canal na inscrição do WebSocket                               |  2  |  2  |   4   | Médio       |
