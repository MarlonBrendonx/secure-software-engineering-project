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
