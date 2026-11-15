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

## Testes escritos

O diretório [`etapa-6-validacao-das-regras/`](etapa-6-validacao-das-regras/) traz os testes no formato da suíte do protótipo (pytest, `fakeredis`, mesmos fixtures de `tests/conftest.py`). Eles dependem do código de [objetivos e eventos](etapa-6-objetivos-e-eventos.md#código-proposto), [regras de detecção](etapa-6-regras-de-deteccao.md#código-proposto) e [resposta a incidentes](etapa-6-resposta-a-incidentes.md#código-proposto).

| Regra ou controle     | Testes (`tests/test_etapa6_deteccao.py`, salvo indicação)                                                                                               | Diferença em relação ao teste planejado                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Campos de correlação  | `test_evento_traz_request_id_sessao_perfil_origem_e_rota`, `test_login_recusado_nao_herda_sessao_de_ninguem`, `test_consulta_da_auditoria_nao_carimba_eventos_antigos` | Não estava planejado; confere os campos que a investigação usa                                |
| D01                   | `test_d01_dispara_uma_vez_por_janela`                                                                                                                   | Sete falhas em vez de cinco, para conferir que o alerta não se repete                         |
| D02                   | `test_d02_conta_negacoes_de_item_e_de_periodo`                                                                                                          | Nenhuma                                                                                       |
| D03                   | `test_d03_falhas_repetidas_na_mesma_conta`, `test_d03_mesma_origem_contra_varias_contas_sem_expor_quais_existem`                                         | Nenhuma                                                                                       |
| D04                   | `test_d04_login_privilegiado_depois_de_falhas`, `test_d04_origem_nova_so_depois_da_linha_de_base`, `test_d04_ignora_perfil_nao_privilegiado`             | Inclui o caso da origem nova                                                                  |
| D05                   | `test_d05_reuso_do_refresh_revoga_a_sessao_e_alerta`, `test_renovacao_legitima_continua_funcionando`                                                     | Nenhuma                                                                                       |
| D06                   | `test_d06_tokens_forjados_geram_evento_e_alerta_medio`, `test_d06_token_valido_de_sessao_encerrada_e_critico`, `test_d06_token_expirado_e_registrado_sem_alerta` | O `sid` desconhecido é testado com o token de uma sessão encerrada por logout                 |
| D07                   | `test_d07_autoaprovacao_recusada_gera_alerta` (`tests/test_etapa6_d07_corrigido.py`)                                                                   | Só a autoaprovação, e só no protótipo corrigido                                               |
| D08                   | `test_d08_alteracoes_repetidas_de_regra`                                                                                                                | Só a condição de volume                                                                       |
| D12                   | `test_d12_websocket_de_outra_origem`                                                                                                                    | Só o WebSocket; a requisição sem token anti-CSRF fica para quando RS08 existir                |
| D13                   | `test_d13_varredura_alcanca_o_limite`                                                                                                                   | Confere também que com exatamente 100 respostas `429` ainda não há alerta                     |
| Robustez              | `test_falha_nas_regras_nao_derruba_a_operacao`, `test_alertas_nao_carregam_senha_nem_otp`                                                               | Não estava planejado                                                                          |

Não há teste para D09, D10, D11 e D14, que não têm código (ver [regras de detecção](etapa-6-regras-de-deteccao.md#código-proposto)).

## Resultado da execução

Os testes foram rodados em cópias dos dois protótipos, com os quatro diretórios aplicados na ordem, Python 3.12 e `fakeredis`. Os protótipos do repositório não foram alterados.

| Execução                                                  | Resultado                                                                                       |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Protótipo corrigido, suíte completa                       | 109 aprovados e 2 `xfail` (os dois de RS04 assimétrico e RS08, que já eram `xfail`)             |
| Protótipo original, suíte completa, sem o teste de D07    | 95 aprovados                                                                                    |
| Teste de D07 no protótipo original                        | Falha, porque o original aceita a autoaprovação (`200` em vez de `403`)                         |
| Testes novos no protótipo corrigido sem o código proposto | 18 falham; passam só os três que conferem que nada quebrou (renovação legítima, perfil não privilegiado e alerta sem senha) |
| `ruff check` e `ruff format --check` com a configuração do protótipo | Sem apontamentos                                                                   |

A suíte que já existia continua passando nos dois protótipos, também com só o diretório 1 ou com os diretórios 1 e 2 aplicados. O script `exportar_evidencias.py` foi exercitado contra um Redis falso: filtrou os eventos pelo usuário, manteve os alertas e gravou um hash que confere com o arquivo.

Para repetir, a partir do `backend/` do protótipo com os arquivos aplicados:

```bash
.venv/bin/python -m pytest tests/test_etapa6_deteccao.py tests/test_etapa6_d07_corrigido.py -v
```

---
