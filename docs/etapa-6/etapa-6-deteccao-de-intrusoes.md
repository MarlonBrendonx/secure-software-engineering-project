# Etapa 6 — Monitoramento, detecção e resposta a incidentes

Esta etapa continua a [Etapa 5, verificação de vulnerabilidades](../etapa-5/etapa-5-verificacao-vulnerabilidades.md). Ela parte dos controles de detecção que as etapas anteriores deixaram previstos, mas sem regra própria: o C7 (monitoramento e alertas) da [arquitetura segura](../etapa-3/etapa-3-diagrama.md#2-controles-posicionados-no-diagrama), a coluna Detect do [mapeamento NIST CSF](../etapa-2/etapa-2-nist-csf.md#81-análise-de-cada-relação) e a frase "geram alerta para a equipe de segurança" nos critérios de RS01 a RS08 dos [requisitos](../etapa-3/etapa-3-requisitos.md#requisitos). Também usa os achados V01 a V03 do [retest autenticado](../etapa-5/etapa-5-retest-autenticado.md) da Etapa 5.

Os documentos propõem 14 regras de detecção (D01 a D14) e um roteiro de resposta. Os identificadores D01 a D14 desta etapa são **regras de detecção** e não se confundem com as decisões de arquitetura D01 a D08 da Etapa 3. Quando uma regra cita uma decisão, ela aparece como "decisão D0x da Etapa 3".

## Resultado em uma frase

Das 14 regras propostas, só D01 tem alerta implementado e testado no [protótipo](../../extra/prototipo-psp/). D02 tem alerta, mas sem teste do alerta, e as outras doze dependem de uma regra de correlação ou de eventos que o protótipo ainda não grava. Nada aqui é uma capacidade operacional: o alerta do protótipo é um `logger.warning` mais uma entrada na lista `psp:alerts` do Redis, sem destinatário, sem fila de tratamento e sem plantão.

## Documentos desta etapa

|  #  | Documento                                                         | O que responde                                                                                   |
| :-: | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
|  1  | [Objetivos, eventos e fontes](etapa-6-objetivos-e-eventos.md)     | O que o monitoramento precisa perceber, quais eventos registrar e de onde vêm os dados           |
|  2  | [Regras de detecção](etapa-6-regras-de-deteccao.md)               | Quais são as regras D01 a D14, quando cada uma dispara e com qual severidade                     |
|  3  | [Resposta a incidentes](etapa-6-resposta-a-incidentes.md)         | O que fazer depois de um alerta, da identificação ao pós-incidente, e quem faz cada parte        |
|  4  | [Validação das regras](etapa-6-validacao-das-regras.md)           | Como comprovar que cada regra correlaciona os eventos e dispara o alerta                          |
|  5  | [Limitações](etapa-6-limitacoes.md)                               | O que esta etapa não cobre e o que falta para a detecção ser uma capacidade real                 |

## Situação das regras no protótipo

| Situação no protótipo                    | Regras                  | O que existe                                                                                                                                                              |
| ---------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Alerta implementado e testado            | D01                     | `SecurityMonitor` conta `mfa_invalido` e `mfa_ausente` por usuário e dispara `mfa_falhas_repetidas`. O teste `test_falhas_repetidas_de_mfa_geram_alerta` cobre o caso. |
| Alerta implementado, sem teste do alerta | D02                     | O mesmo monitor conta `acesso_negado` e dispara `acesso_negado_repetido`. Os testes conferem o registro da negação, mas não o alerta.                                    |
| Evento registrado, sem regra de alerta   | D03, D04, D08           | `login_falha`, `login_sucesso`, `regra_servico_atualizada` e `regra_servico_excluida` ficam na auditoria, mas nada os correlaciona.                                      |
| Sinal só no log ou na resposta HTTP      | D06, D10, D12, D13      | Token recusado (`401`), falha do guard (`503`), WebSocket fechado por origem (`4403`) e limite excedido (`429`) não chegam à auditoria.                                  |
| Evento não gerado                        | D05, D07, D09, D11, D14 | Faltam o controle que produz o evento (rotação do refresh, autoaprovação, outbox, carga do ERP) ou o registro da leitura.                                                |

## Rastreabilidade

A tabela liga cada regra aos riscos da Etapa 2, aos requisitos da Etapa 3 e aos achados da Etapa 5.

| Regra | Risco (etapa 2) | Requisito (etapa 3)                                | Achado (etapa 5) | Severidade inicial | Situação no protótipo           |
| ----- | --------------- | -------------------------------------------------- | ---------------- | ------------------ | ------------------------------- |
| D01   | R02             | RS02                                               | —                | Alta               | Alerta implementado e testado   |
| D02   | R03, R05        | RS03                                               | —                | Alta               | Alerta sem teste                |
| D03   | R02             | RS02                                               | —                | Média              | Evento registrado               |
| D04   | R02             | RS02                                               | —                | Crítica            | Evento registrado               |
| D05   | R25             | RS04 (sessão revogável)                            | V01              | Alta               | Evento não gerado               |
| D06   | R06, R07        | RS04                                               | —                | Crítica ou Média   | Sinal só na resposta HTTP       |
| D07   | R01, R18        | RS01                                               | —                | Alta               | Evento não gerado               |
| D08   | R09             | sem requisito dedicado                             | —                | Média              | Evento registrado               |
| D09   | R05             | sem requisito dedicado; relacionado a RS03         | —                | Média              | Evento não gerado               |
| D10   | R28             | RS06                                               | —                | Alta               | Sinal só no log                 |
| D11   | R26, R08        | RS05                                               | —                | Crítica            | Evento não gerado               |
| D12   | R29, R17        | RS08                                               | —                | Média              | Sinal só no log                 |
| D13   | R11, R16        | sem requisito dedicado                             | —                | Baixa              | Sinal só na resposta HTTP       |
| D14   | R23             | RS07                                               | —                | Crítica            | Evento não gerado               |

O V02 (token também no corpo da resposta) e o V03 (`PyJWT` com CVE) não têm regra de detecção própria. Eles são tratados como correção, no passo 5 da [resposta a incidentes](etapa-6-resposta-a-incidentes.md#5-correção).

## Relação com o NIST CSF 2.0

Esta etapa se relaciona principalmente às funções:

- **Detect:** observação, correlação e identificação de eventos suspeitos;
- **Respond:** triagem, contenção, investigação, comunicação e correção;
- **Recover:** restauração de serviço ou informação e retorno controlado à operação.

As funções estão representadas como planejamento de segurança. A documentação não implica que uma capacidade operacional de SOC, SIEM, IDS ou resposta automatizada já exista.

Nas categorias usadas na [Etapa 2](../etapa-2/etapa-2-nist-csf.md#72-categorias-do-csf-20-usadas-no-mapeamento), as regras D01 a D14 e as fontes de dados correspondem a DE.CM (monitoramento contínuo) e DE.AE (análise de eventos adversos). A triagem e a investigação correspondem a RS.MA e RS.AN, a contenção e a correção a RS.MI, e a comunicação a RS.CO. A recomposição dos valores e a regeneração da carga correspondem a RC.RP, e o aviso ao cliente da rede sobre a correção a RC.CO.

---
