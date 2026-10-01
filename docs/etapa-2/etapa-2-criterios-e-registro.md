# Etapa 2 — Riscos e Critérios Avaliados

| ID  | Título |  Caso de Abuso | 
| --- | ------- | ------------- | 
| R01 | Alteração/remoção de lançamentos | CA01 |
| R02 | Captura de conta/perfil SSO | CA02 |
| R03 | Acesso não autorizado a dados restritos | CA03 |
| R04 | Acesso direto aos anexos no storage | CA04 |
| R05 | Extração de dados em volume | CA04 |
| R06 | Vazamento do `JWT_SECRET`  | CA09 |
| R07 | Falsificar token | CA09 |
| R08 | Remoção/adulteração da auditoria | CA05 |
| R09 | Alteração de regras de serviço | CA06 |
| R10 | Adulteração do motor de cálculo | CA07 |
| R11 | DoS no fluxo de autorizaçã | CA08 |
| R12 | Vazamento do `CELERY_CALLBACK_SECRET` | CA10 |
| R13 | Falsificação de callbacks internos | CA10 |
| R14 | Indisponibilidade do banco/infra | CA11 |
| R15 | Envio de e-mails maliciosos | CA12 |
| R16 | DoS no EventBus WebSocket | CA13 |
| R17 | Subscrição indevida no ws vaza faturamento | CA04 |
| R18 | Autoaprovação sem segregação de funções | CA14 |
| R19 | Injeção de SQL no Oracle | CA15 |
| R20 | Configuração insegura em produção (`local` / `DEBUG`) |  |
| R21 | Isolamento insuficiente entre ambientes | CA18 |
| R22 | Anexo malicioso contra aprovadores | CA16 |
| R23 | Adulteração ou injeção de fórmula na carga ERP |  |