# Etapa 2 — Estratégias de tratamento e NIST CSF 2.0

Este documento define as estratégias de tratamento, apresenta as funções do
**NIST Cybersecurity Framework 2.0** e mapeia cada risco (R01–R29) às funções.

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
| R02 | Reduzir | O SSO é necessário ao acesso corporativo. MFA, monitoração de sessões anômalas e bloqueio de contas comprometidas diminuem a captura e o uso indevido de perfis privilegiados. |
| R03 | Reduzir | Consultar dados é função legítima. Verificar perfil e escopo do recurso em cada requisição reduz o acesso indevido, inclusive por troca de identificadores. |
| R04 | Reduzir | O armazenamento externo de anexos é necessário. URLs assinadas de curta duração e escopo restrito, com proteção das credenciais de storage, diminuem o acesso fora do controle da aplicação. |
| R05 | Reduzir | A leitura e a exportação de dados atendem ao negócio. Limites de extração, monitoração das ações e bloqueio de comportamento anômalo reduzem o vazamento em volume. |
| R06 | Reduzir | O segredo é necessário à assinatura dos tokens. Armazenamento em cofre, rotação e varredura com Gitleaks reduzem sua exposição e a possibilidade de exploração em R07. |
| R07 | Reduzir | A autenticação por token é necessária. Prevenir o vazamento em R06, detectar ações anômalas e substituir a chave comprometida limitam a falsificação e permitem conter seus efeitos. |
| R08 | Reduzir | A auditoria é necessária à responsabilização. Proteger os registros contra alteração e remoção reduz a possibilidade de apagar rastros de operações indevidas. |
| R09 | Reduzir | A manutenção de regras de serviço é função legítima. Uma matriz de permissões, versionamento das regras e trilha protegida reduzem alterações indevidas e permitem corrigir os faturamentos afetados. |
| R10 | Reduzir | O motor de cálculo e suas dependências são necessários. Revisão de código, testes, validadores e varredura de dependências reduzem a adulteração pela cadeia de entrega. |
| R11 | Reduzir | As transições de aprovação são necessárias. Limites de requisições por operação reduzem a sobrecarga sem eliminar o fluxo legítimo de autorização. |
| R12 | Reduzir | A chave autentica callbacks necessários ao processamento assíncrono. Cofre, rotação e varredura de segredos reduzem a exposição que habilita R13. |
| R13 | Reduzir | Os callbacks internos são necessários. Validação de origem, proteção da chave, monitoração e substituição do segredo comprometido reduzem chamadas forjadas e permitem contê-las. |
| R14 | Reduzir | O banco de dados é essencial ao sistema. Limites de conexões, isolamento de recursos, monitoração de carga e redundância reduzem a probabilidade e a duração da indisponibilidade. |
| R15 | Reduzir | O envio corporativo de e-mails é necessário. Proteger a chave em cofre e aplicar autenticação de domínio com SPF, DKIM e DMARC reduzem o uso indevido do canal e a falsificação de remetente. |
| R16 | Reduzir | As notificações em tempo real são úteis ao fluxo de faturamento. Limites de conexões e eventos, com controle de taxa no WebSocket, reduzem a sobrecarga do EventBus. |
| R17 | Reduzir | A inscrição em canais de faturamento é função legítima. Verificar a autorização para cada canal e período reduz a divulgação de eventos fora do escopo permitido. |
| R18 | Reduzir | Criar, enviar e aprovar lançamentos são atividades necessárias. Segregar essas funções e impedir a aprovação pelo próprio autor reduz a fraude sem eliminar o fluxo de aprovação. |
| R19 | Reduzir | As consultas ao Oracle são necessárias à integração legada. Uso de bindvars, validação de parâmetros e manutenção de acesso somente leitura reduzem a injeção e seu alcance. |
| R20 | Evitar | Autenticação local e modo de depuração são dispensáveis em produção. Desabilitar essas opções e impedir o deploy com configuração insegura elimina a condição que origina o risco. |
| R21 | Reduzir | Os ambientes de produção e testes são necessários. Separação de credenciais e permissões por schema, com isolamento de recursos ou instâncias, reduz o movimento lateral e a disputa de capacidade. |
| R22 | Reduzir | Os anexos fazem parte do processo de aprovação. Varredura de conteúdo malicioso e isolamento de arquivos suspeitos reduzem o comprometimento dos aprovadores ao abrir documentos. |
| R23 | Reduzir | A carga de integração com o ERP é necessária. Tratar campos exportados como texto e verificar a integridade do arquivo antes da importação reduzem a injeção de fórmulas e a adulteração no storage. |
| R24 | Reduzir | Validar destinatários autorizados por cliente no servidor; registrar destinatário, usuário e lançamento; alertar sobre desvios. |
| R25 | Reduzir | Rotacionar refresh tokens e detectar reutilização; revogar a família de tokens e as sessões comprometidas. |
| R26 | Reduzir | Persistir evento de auditoria de forma durável e vinculada à operação; usar entrega com repetição e reconciliação; alertar sobre falhas. |
| R27 | Reduzir | Exigir reautenticação adicional em aprovações críticas; preservar identidade, sessão, horário e conteúdo aprovado em trilha protegida. |
| R28 | Reduzir | Negar acesso quando a autorização falhar; testar exceções e indisponibilidade de dependências dos guards; registrar tentativas negadas. |
| R29 | Reduzir | Aplicar proteção anti-CSRF e validação de origem nas rotas autenticadas por cookie; configurar SameSite adequado e testar requisições entre origens. |

### 6.3 Regra para aceitação de risco

Toda aceitação precisa registrar quatro itens:

| Item                | O que registrar                                                        |
| ------------------- | ---------------------------------------------------------------------- |
| **Motivo**          | Motivo da aceitação do risco.                                          |
| **Aprovador**       | Quem decide, líder técnico ou gestão da área de negócio e de segurança.|
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

Cada linha diz o que a função faz pelo risco. Onde a função não está marcada, a omissão é intencional (ver 8.3).

| Risco | Govern                                    | Identify | Protect                             | Detect                                    | Respond                                      | Recover                                                    |
| ----- | ----------------------------------------- | -------- | ----------------------------------- | ----------------------------------------- | -------------------------------------------- | ---------------------------------------------------------- |
| R01   | GV.RR: matriz de quem escreve lançamentos | —        | PR.AA: mínimo privilégio na escrita | DE.CM: alerta de alteração fora do padrão | RS.MA: bloquear usuário e congelar o período | RC.RP: recompor valor pela auditoria antes do envio ao ERP |
| R02   | —        | —        |  PR.AA: autenticação de dois fatores (MFA) | DE.CM: alerta para falha no segundo nível de autenticação | RS.MA: bloquear usuário e congelar o período | RC.RP: revisar e reverter operações feitas pela conta comprometida | 
| R03   | —        | —        | PR.AA: verificação de autorização, permissões do perfil para cada requisição | DE.CM: registrar e alertar sobre negações por escopo indevido | —       | —       |
| R04   | —        | —        | PR.PS: URLs de acesso externo com validade curta ou uso único | DE.CM: registrar a emissão de URLs assinadas | —       | —       |
| R05   | —        | —        | — | DE.CM: monitoramento ativo das ações de cada usuário | RS.MI: bloqueio temporário do usuário em caso de comportamento anômalo; RS.CO: comunicar o encarregado de dados quando houver dado pessoal | — |
| R06   | —        | —        | PR.DS: `JWT_SECRET` armazenado no cofre corporativo, uso de gitleaks | — | — | — |
| R07   | —        | —        | — | DE.CM: monitoramento das ações de cada usuário, procurando comportamento anômalo | RS.MA: se confirmado o vazamento do `JWT_SECRET`, gera outro em substituição ao antigo | RC.RP: reverter operações de escrita realizadas com secret vazado |
| R08   | —        | —        | PR.DS: registro read-only de toda operação mutante no sistema | DE.CM: verificar o encadeamento por hash dos registros | — | — | 
| R09   | GV.RR: matriz de quem escreve regras de serviço | — | PR.DS: registro de operação mutante em log read-only | DE.CM: alertar sobre alteração de regra de serviço | — | RC.RP: reverter faturamentos gerados com regras de serviço erradas | 
| R10   | GV.SC: inventário de dependências (SBOM) e assinatura de artefatos | — | PR.IR: uso de validadores de código, testes automatizados, ferramentas de qualidade e segurança de código | — | — | — |
| R11   | — | — | PR.IR: uso de rate limiters conforme operação | — | — | — |
| R12   |  —        | —        | PR.DS: `CELERY_CALLBACK_SECRET` armazenado no cofre corporativo, uso de gitleaks | — | — | — |
| R13   | —        | —        | PR.PS: validação de origem nas requisições | DE.CM: monitoramento das requisições, procurando por comportamento anômalo | RS.MA: se confirmado o vazamento do `CELERY_CALLBACK_SECRET`, gera outro em substituição ao antigo | — |
| R14   | GV.SC: escolha de serviços/software de banco de dados que seja escalável |  —        | PR.IR: adição de múltiplas instâncias espelhadas do banco de dados e uso de balanceamento de carga entre as instâncias | DE.CM: monitoramento da carga nas instâncias do banco de dados | — | RC.RP: failover para réplica e restauração de backup | 
| R15   | —        | —        | PR.DS: `EMAIL_SERVICE_API_KEY` armazenado no cofre corporativo, uso de gitleaks; PR.PS: uso de autenticação de domínio no servidor de e-mails (SPF, DKIM, DMARC) | — | — | — |
| R16   | —        | —        | PR.IR: uso de limites globais de acesso por IP | — | — | — |
| R17   | —        | —        | PR.AA: verificação de permissões/autorização de acesso para inscrição no ws | — | — | — |
| R18   | GV.PO: política que impede que usuário `admin` aprove o próprio lançamento | —        | PR.AA: validação do usuário que requisita a aprovação de lançamento | DE.CM: alertar sobre tentativa de autoaprovação | — | — |
| R19   | —        | —        | PR.DS: filtros em todas as queries realizadas no banco de dados, buscando prevenir SQL injection | DE.CM: análise estática de SQL concatenado no CI | — | — | 
| R20   | —        | —        | PR.IR: verificação de variáveis de controle conforme o ambiente; PR.AT: conscientizar a equipe a verificar as variáveis de controle antes de realizar o deploy | DE.CM: bloqueio de deploy com configuração insegura | — | — | 
| R21   | GV.PO: credenciais distintas por ambiente | —        | PR.IR: separação do schema de produção e testes | — | — | — | 
| R22   | —        | —        | PR.PS: uso de anti-vírus e scanners de conteúdos maliciosos nos anexos | — | RS.MA: report do usuário que anexou material com conteúdo malicioso | — | 
| R23   | —        | —        | PR.PS: validação de dados a serem exportados para o ERP | — | RS.MA: report do usuário que tentou inserir dados maliciosos para os arquivos do ERP | RC.RP: regenerar o arquivo de carga pelo sistema |
| R24 | — | — | PR.AA: autorizar destinatários por cliente | DE.CM: alertar sobre destinatários indevidos | RS.MI: bloquear envio indevido e investigar destinatários | — |
| R25 | — | — | PR.AA: rotacionar e revogar refresh tokens | DE.CM: detectar reuso de refresh token | RS.MI: revogar sessões e família de tokens | — |
| R26 | — | — | PR.PS: persistência durável dos logs de auditoria | DE.CM: alertar sobre falhas e lacunas na auditoria | RS.MI: conter operações sem rastreabilidade e investigar falha | — |
| R27 | — | — | PR.AA: reautenticação em aprovação crítica; PR.DS: proteção da evidência | DE.CM: correlacionar aprovação, sessão e reautenticação | RS.MI: preservar evidências e investigar contestação | — |
| R28 | — | — | PR.AA: negar acesso em falhas dos guards | DE.CM: monitorar exceções e tentativas negadas | RS.MI: bloquear rota afetada e investigar operações realizadas | — |
| R29 | — | — | PR.PS: proteção anti-CSRF e configuração dos cookies | DE.CM: monitorar requisições mutantes de origem indevida | RS.MI: revogar sessão comprometida e investigar alterações | — |

---

### 8.3 Funções não marcadas

- **Identify** não aparece em nenhuma linha porque é transversal: o inventário de ativos (ID.AM) foi feito na Etapa 1 e o registro de riscos (ID.RA) é o próprio documento de critérios e registro, válido para todos os riscos.
- **Govern** só é marcado quando o risco exige política ou atribuição de responsabilidade própria (R01, R09, R14, R18). Os demais seguem a política geral de segredos e de aceitação de risco da seção 6.3.
- **Detect, Respond e Recover** ficam sem marcação quando o controle preventivo basta para o nível residual pretendido ou quando o evento é detectado de imediato pela própria falha. O plano de tratamento acrescenta ações nessas funções onde foram necessárias (ver 3.2).

  ---