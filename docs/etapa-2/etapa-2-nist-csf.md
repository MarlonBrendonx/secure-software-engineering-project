# Etapa 2 — Estratégias de tratamento e NIST CSF 2.0

Este documento define as estratégias de tratamento, apresenta as funções do
**NIST Cybersecurity Framework 2.0** e mapeia cada risco (R01–R23) às funções.

Os ativos citados (A1–A14) são os da
[identificação do sistema](../etapa-1/etapa-1-identificacao-sistema.md).

---

## 6. Estratégias de tratamento

### 6.1 Estratégias possíveis

| Estratégia       | Descrição                                                                        | Quando se aplica neste sistema                                                 |
| ---------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Evitar**       | Eliminar a atividade ou condição que dá origem ao risco.                         | A condição de risco é dispensável (ex.: configuração `local` em produção).     |
| **Reduzir**      | Implementar medidas para diminuir a probabilidade ou o impacto.                  | A função é necessária ao negócio e não pode ser removida (maioria dos riscos). |
| **Compartilhar** | Atribuir parte da operação ou das consequências a um terceiro.                   | Há provedor com responsabilidade contratual (nuvem, e-mail).                   |
| **Aceitar**      | Reconhecer e manter conscientemente o risco, com justificativa e acompanhamento. | Só o que sobra depois do tratamento (risco residual).                          |

### 6.2 Estratégia escolhida por risco

| Risco | Estratégia principal | Justificativa da escolha                                                                                                                       |
| ----- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| R01   | Reduzir              | Escrever lançamentos é função legítima e não se elimina. Reduz-se com mínimo privilégio, aprovação por perfil e detecção de alteração anômala. |

### 6.3 Regra para aceitação de risco

Toda aceitação precisa registrar quatro itens:

| Item                | O que registrar                                                        |
| ------------------- | ---------------------------------------------------------------------- |
| **Motivo**          | Motivo da aceitação do risco                                           |
| **Aprovador**       | Quem decide, líder técnic ou gestão da área de negócio e de segurança. |
| **Condição**        | Em quais circunstâncias a aceitação vale.                              |
| **Data de revisão** | Quando a decisão volta à pauta e deve ser revisada.                    |

---

## 7. Funções do NIST CSF 2.0

### 7.1 Finalidade de cada função neste sistema

| Função       | Finalidade geral                                              | Aplicação neste sistema                                                                                                                                                      |
| ------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Govern**   | Definir políticas, responsabilidades, prioridades e critérios | Definir regras de uso de chaves e senhas, quem pode mudar regras de cálculo e código, como tratar dados pessoais (LGPD) e quem aprova um risco aceito.                       |
| **Identify** | Conhecer ativos, dependências, vulnerabilidades e riscos      | Manter a lista do que existe: dados, chaves, banco, e-mail, as chamadas internas e os pontos que usam SQL direto. Manter o registro de riscos atualizado.                    |
| **Protect**  | Implementar salvaguardas                                      | Exigir MFA no login, checar permissão em cada dado acessado, guardar chaves em cofre, proteger o histórico contra alteração e limitar o número de requisições.               |
| **Detect**   | Identificar eventos suspeitos e falhas                        | Gerar alertas para logins estranhos, regras alteradas, exportações grandes, aprovação do próprio lançamento e excesso de requisições.                                        |
| **Respond**  | Conter, analisar, comunicar e tratar incidentes               | Derrubar sessões, trocar chaves vazadas, bloquear a origem do ataque, isolar anexo suspeito e avisar as áreas envolvidas (e o encarregado de dados, se houver dado pessoal). |
| **Recover**  | Restaurar serviços e dados                                    | Restaurar o banco, refazer cálculos errados, gerar de novo o arquivo do ERP e reconstruir valores a partir do histórico.                                                     |

### 7.2 Categorias do CSF 2.0 usadas no mapeamento

Para evitar o uso genérico da aplicação do NIST, o mapeamento da seção 8 cita a
categoria do CSF 2.0. A lista oficial de funções,
categorias e subcategorias está no documento
[NIST CSWP 29 The NIST Cybersecurity Framework (CSF) 2.0](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf),
e a página do framework fica em
[nist.gov/cyberframework](https://www.nist.gov/cyberframework).

| Função   | Categorias usadas                                                                                                                                                                   |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Govern   | GV.PO (política), GV.RR (papéis e responsabilidades), GV.RM (estratégia de gestão de risco), GV.SC (cadeia de suprimentos), GV.OC (contexto organizacional, ex.: LGPD)              |
| Identify | ID.AM (inventário de ativos), ID.RA (avaliação de risco)                                                                                                                            |
| Protect  | PR.AA (identidade e controle de acesso), PR.DS (segurança de dados), PR.PS (segurança de plataforma e configuração), PR.IR (resiliência da infraestrutura), PR.AT (conscientização) |
| Detect   | DE.CM (monitoração contínua), DE.AE (análise de eventos adversos)                                                                                                                   |
| Respond  | RS.MA (gestão de incidentes), RS.AN (análise), RS.CO (comunicação), RS.MI (mitigação)                                                                                               |
| Recover  | RC.RP (execução do plano de recuperação), RC.CO (comunicação da recuperação)                                                                                                        |

---

## 8. Mapeamento dos riscos para o NIST CSF

### 8.2 Análise de cada relação

Cada linha diz o que a função faz pelo risco. Onde a função não está marcada, a
omissão é intencional (ver 8.3).

| Risco | Govern                                    | Identify | Protect                             | Detect                                    | Respond                                      | Recover                                                    |
| ----- | ----------------------------------------- | -------- | ----------------------------------- | ----------------------------------------- | -------------------------------------------- | ---------------------------------------------------------- |
| R01   | GV.RR: matriz de quem escreve lançamentos | —        | PR.AA: mínimo privilégio na escrita | DE.CM: alerta de alteração fora do padrão | RS.MA: bloquear usuário e congelar o período | RC.RP: recompor valor pela auditoria antes do envio ao ERP |
| R02   | —        | —        |  PR.AA: autenticação de dois fatores (MFA) | DE.CM: alerta para falha no segundo nível de autenticação | RS.MA: bloquear usuário e congelar o período | - | 
| R03   | —        | —        | PR.PS: verificação de autorização, permissões do perfil para cada requisição | —       | —       | —       |
| R04   | —        | —        | PR.PS: URL's de acesso externo com validade curta ou uso único | —       | —       | —       |
| R05   | —        | —        | — | DE.CM: monitoramento ativo das ações de cada usuário | RS.MI: bloqueio temporário do usuário em caso de comportamento anômalo | — |
| R06   | —        | —        | PR.DS: `JWT_SECRET` armazenado no cofre corporativo, uso de gitleaks | — | — | — |
| R07   | —        | —        | — | DE.CM: monitoramento das ações de cada usuário, procurando comportamento anômalo | RS.MA: se confirmado o vazamento do `JWT_SECRET`, gera outro em substituição ao antigo | RC.RP: reverter operações de escrita realizadas com secret vazado |
| R08   | —        | —        | PR.PS: registro read-only de toda operação mutante no sistema | — | — | — | 
| R09   | GV.RR: matriz de quem escreve regras de serviço | — | PR.DS: registro de operação mutante em log read-only | — | — | RC.RP: reverter faturamentos gerados com regras de serviço erradas | 
| R10   | — | — | PR.IR: uso de validadores de código, testes automatizados, ferramentas de qualidade e segurança de código | — | — | — |
| R11   | — | — | PR.IR: uso de rate limiters conforme operação | — | — | — |
| R12   |  —        | —        | PR.DS: `CELERY_CALLBACK_SECRET` armazenado no cofre corporativo, uso de gitleaks | — | — | — |
| R13   | —        | —        | PR.PS: validação de origem nas requisições | DE.CM: monitoramento das requisições, procurando por copmortamento anômalo | RS.MA: se confirmado o vazamento do `CELERY_CALLBACK_SECRET`, gera outro em substituição ao antigo | — |
| R14   | GV.SC: escolha de serviços/software de banco de dados que seja escalável |  —        | PR.IR: adição de múltiplas instâncias espelhadas do banco de dados e uso de balanceameto de carga entre as instâncias | DE.CM: monitoramento da carga nas instâncias do banco de dados | — | — | 
| R15   | —        | —        | PR.DS: `EMAIL_SERVICE_API_KEY` armazenado no cofre corporativo, uso de gitleaks; PR.PS: uso de autenticação de domínio no servidor de e-mails (SPF, DKIM, DMARC) | — | — | — |
| R16   | —        | —        | PR.IR: uso de limites globais de acesso por IP | — | — | — |
| R17   | —        | —        | PR.DS: verificação de permissões/autorização de acesso para inscrição no ws | — | — | — |
| R18   | GV.PO: política que impede que usuário `admin` aprove o próprio lançamento | —        | PR.DS: validação do usuáiro que requisita a aprovação de lançamento | — | — | — |
| R19   | —        | —        | PR.DS: filtros em todas as queries realizadas no banco de dados, buscando prevenir SQL injection |  — | — | — | 
| R20   | —        | —        | PR.IR: verificação de variáveis de controle conforme o ambiente; PR.AT: conscientizar a equipe a verificar as variáveis de controle antes de realizar o deploy |  — | — | — | 
| R21   | —        | —        | PR.IR: separação do schema de produção e testes | — | — | — | 
| R22   | —        | —        | PR.PS: uso de anti-vírus e scanners de conteúdos maliciosos nos anexos | — | RS.MA: report do usuário que anexou material com conteúdo malicioso | — | 
| R23   | —        | —        | PR.PS: validação de dados a serem exportados para o ERP | — | RS.MA: report do usuário que tentou inserir dados maliciosos para os arquivos do ERP | — |