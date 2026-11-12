# Etapa 5 — Execução e evidências

Este documento registra como a verificação foi executada e lista as evidências. Os resultados e a interpretação estão na [Análise dos achados](etapa-5-analise-dos-achados.md). Os limites do teste estão em [Limitações](etapa-5-limitacoes.md).

## Sessões

| Sessão | Perfil                                       | Tipo                                                     | Evidências                                 |
| ------ | -------------------------------------------- | -------------------------------------------------------- | ------------------------------------------ |
| 1      | `analyst`                                    | passive scan e active scan (backend e frontend)          | capturas 01 a 05b e `scan-ativo-front.csv` |
| 2      | `admin`, com MFA                             | só passive scan (64 mensagens, todas com origem `Proxy`) | `scan-passivo-admin.csv`                   |
| 3      | `analyst` e `manager` (pelo nome do arquivo) | só passive scan (79 mensagens, todas com origem `Proxy`) | `scan-passivo-analyst-manager.csv`         |
| 4      | `admin`                                      | active scan do backend (445 requisições `GET`)           | `scan-ativo-admin.csv`                     |

As sessões 2 e 4 existem porque a sessão 1 não alcançou as rotas de escrita nem as protegidas. Elas exigem MFA (veja [Ambiente e configuração](etapa-5-ambiente-e-configuracao.md)).

## Passo a passo

1. Subir Redis, backend e frontend (comandos em [Ambiente e configuração](etapa-5-ambiente-e-configuracao.md)).
2. Criar o contexto `Faturamento` no ZAP com as duas URLs e ligar o modo Protegido (captura 01).
3. Importar o OpenAPI do backend e navegar pelo front com o proxy do ZAP (captura 02).
4. Configurar a autenticação do `analyst` pelo Replacer (captura 03).
5. Executar o passive scan durante a navegação (capturas 04a e 04b).
6. Executar o active scan no backend (captura 05a) e no frontend.
7. Exportar o histórico das requisições em CSV.
8. Repetir a navegação com o proxy ligado como `admin` (sessão 2) e como `analyst` e `manager` (sessão 3), para cobrir login com MFA e rotas de escrita.

## Índice de evidências

Todos os caminhos são relativos a `evidencias/etapa-5/`.

| Arquivo                                          | O que mostra                                                                          |
| ------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `Backend/01-contexto-zap.png`                    | contexto `Faturamento` com as duas URLs incluídas                                     |
| `Backend/02-rotas-importadas.png`                | OpenAPI importado: rotas `/v1/...` na árvore e todas as tarefas processadas           |
| `Backend/03-autenticacao.png`                    | regra "Token Analyst" no Replacer, cabeçalho `Authorization`, todos os iniciadores    |
| `Backend/04a-alertas-passivo.png`                | lista de alertas do passive scan e a contagem por severidade                          |
| `Backend/04b-scan-passivo-endpoints.png`         | histórico do tráfego analisado: login, refresh, telas do front e rotas de billing     |
| `Backend/05a-scan-ativo.png`                     | active scan do backend concluído, sem alertas novos                                   |
| `Backend/05b-scan-ativo-politicas-aplicadas.png` | detalhe do alerta `X-Content-Type-Options Header Missing` em `/v1/auth/refresh` (A02) |
| `Backend/scan-ativo-admin.csv`                   | histórico das requisições do active scan no backend como `admin`, sem `401`           |
| `Backend/scan-passivo-admin.csv`                 | histórico do passive scan como `admin`                                                |
| `Backend/scan-passivo-analyst-manager.csv`       | histórico do passive scan como `analyst` e `manager`                                  |
| `Frontend/scan-ativo-front.csv`                  | histórico das requisições do active scan no frontend                                  |
