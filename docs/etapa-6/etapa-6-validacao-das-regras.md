# Etapa 6 — Validação das regras

A aplicação já permite gerar parte dos eventos de entrada das [regras de detecção](etapa-6-regras-de-deteccao.md). Cada regra ainda precisa de um teste controlado que comprove a correlação e o alerta, e não apenas a negação preventiva da operação.

## Testes planejados

| Regra | Teste planejado                                                                                                                      | Evidência esperada                                                                                                                  |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| D01   | Cinco chamadas de gestor sem MFA em rota de aprovação (já existe: `test_falhas_repetidas_de_mfa_geram_alerta`)                       | Cinco `mfa_ausente` na auditoria e um único `mfa_falhas_repetidas` em `psp:alerts`                                                   |
| D02   | Analista pede 10 lançamentos de cliente fora do escopo, incluindo listagem por período fora do escopo                                | Dez `acesso_negado` e um `acesso_negado_repetido`; as negações de período também contadas                                           |
| D03   | Onze logins com senha errada para o mesmo usuário e um login errado para cinco usuários a partir da mesma origem                     | Alerta por usuário e alerta por origem, sem expor qual usuário existe                                                               |
| D04   | Gestor com D03 disparado faz login com sucesso                                                                                       | Alerta Crítico com usuário, origem e `sid`                                                                                          |
| D05   | Renovar a sessão e reapresentar o refresh antigo (o caso do V01)                                                                     | `401` no reuso, sessão revogada, evento de reuso e alerta                                                                           |
| D06   | Repetir os tokens forjados do retest (`alg=none`, assinatura trocada, `role=admin`) e um token válido com `sid` revogado             | Eventos de token recusado com motivo; alerta Médio para assinatura inválida e Crítico para `sid` desconhecido com assinatura válida |
| D07   | `PATCH` e `DELETE` em lançamento aguardando aprovação; transição não permitida; autoaprovação                                        | Recusa, evento com usuário, lançamento, operação e motivo, e alerta                                                                 |
| D08   | Alterar o tipo e o valor de uma regra com lançamentos no período aberto                                                              | `regra_servico_atualizada` com os campos e alerta para o Negócio                                                                    |
| D09   | Analista consulta todos os clientes do escopo em sequência, acima do volume de referência                                            | Evento de leitura com volume e alerta                                                                                               |
| D10   | Derrubar o Redis durante uma requisição autenticada                                                                                  | `503` sem detalhe interno, nenhuma operação efetivada, evento de falha do guard e alerta                                            |
| D11   | Simular erro na gravação da auditoria durante uma alteração de lançamento                                                            | Operação desfeita, erro ao usuário e alerta de falha de auditoria                                                                   |
| D12   | Abrir o WebSocket com `Origin` de outro site três vezes; requisição de escrita sem token anti-CSRF                                   | Fechamento `4403` e `403` registrados na auditoria e alerta                                                                         |
| D13   | Mais de 100 requisições à rota de login da mesma origem                                                                              | `429` a partir da 11ª no minuto e um alerta de varredura                                                                            |
| D14   | Alterar o total de um arquivo de carga depois de gerado                                                                              | Importação bloqueada, alerta e carga regenerada igual à original                                                                    |

## O que cada teste precisa para rodar

| Pré-requisito                                 | Regras                  |
| --------------------------------------------- | ----------------------- |
| Pode rodar já no protótipo                    | D01, D02                |
| Precisa só da regra (eventos existem ou são fáceis de gravar) | D03, D04, D08, D13 |
| Precisa primeiro gravar o evento na auditoria | D05, D06, D07, D10, D12 |
| Depende de controles que ainda não existem (outbox e carga do ERP) | D11, D14   |

D09 depende do registro das consultas e exportações com o volume devolvido, que o protótipo ainda não grava (grupo 6 dos [eventos mínimos](etapa-6-objetivos-e-eventos.md#eventos-mínimos-a-registrar)).

---
