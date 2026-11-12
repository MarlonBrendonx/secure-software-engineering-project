# Etapa 5 — Limitações e descartes

Uma varredura automática produz ruído. Este documento mostra o que descartamos e o que o teste não garante.

## Alertas descartados

Dos 11 alertas do passive scan, seis ficaram fora da análise.

| Alerta                                                                        | Motivo      | Justificativa                                                  |
| ----------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------- |
| Session Management Response Identified, Authentication request identified     | Informativo | O ZAP só reconhece login e refresh. Não é falha.               |
| Modern Web Application                                                        | Informativo | Indica que a página é uma SPA, o que limita o spider.          |
| Content-Type Header Missing                                                   | Informativo | Ocorre em respostas sem corpo. Sem impacto direto.             |
| CSP: Failure to Define Directive with No Fallback, CSP: `style-src unsafe-inline` | Agrupado | Tratados dentro do A01, pois são da mesma política de CSP.     |

## Possíveis falsos positivos

- **Divulgação de data e hora (Unix).** Provavelmente são os claims `iat` e `exp` do JWT, que o cliente precisa ler. Confirmar no detalhe do alerta.
- **Informação no `localStorage`.** Nenhum arquivo do frontend usa `localStorage`. A origem pode ser uma biblioteca ou o modo de desenvolvimento do Next.js. Não foi confirmado.
- **CSP no modo `dev`.** O front rodou com `pnpm dev`, e a CSP muda nesse modo. Repetir com `pnpm build && pnpm start`.
- **Cabeçalhos em produção.** Um proxy reverso pode acrescentar `X-Content-Type-Options` e remover `X-Powered-By`. Os achados A02 e A03 valem para o protótipo isolado.

## Limitações do teste

- **O active scan como `analyst` quase não chegou às rotas protegidas.** No backend, as requisições a `/v1/billing` e `/v1/registry` receberam `401`. O motivo provável é o token expirado (vale 15 minutos), mas não confirmamos. No frontend, o scanner só recebeu redirecionamentos (`307`/`308`) e `404`. Por isso, "0 alertas" cobre sobretudo a autenticação e as rotas inexistentes, não a lógica dos endpoints.
- **O active scan como `admin` alcançou as rotas protegidas, mas de forma rasa.** Não houve `401`, mas a maioria das respostas em `/v1/billing` e `/v1/registry` foi `422` (parâmetros inválidos), e o histórico só tem `GET`. As rotas de escrita não foram atacadas. O CSV também não traz os alertas, que dependem da captura ou do relatório.
- **Não houve active scan como `manager`.** As rotas dele foram só observadas no passive scan, sem alerta.
- **O CSV do `admin` não nomeia os alertas.** Os nomes vêm da captura 04a, de outra sessão. A ligação com A01 e A02 é uma inferência, confirmada com `curl`.
- **Sessões curtas e com uma só configuração.** Elas não cobrem `audit`, `DELETE`, `PATCH` nem o WebSocket (`/ws`). A política do active scan não ficou registrada.
- **A sessão `admin` criou dados de teste** (uma regra de serviço e um lançamento). Quem repetir o teste deve recriar o Redis.
- **O scan não entende regras de negócio.** Ele não confirma, por exemplo, se um analista de outro cliente lê um lançamento (R03). Esse risco segue coberto só pelos testes TS01 e TS02 da etapa 4.
- **O ambiente local difere do real.** Não há proxy reverso, TLS nem SSO, e o login é simulado (mock). Achados de HTTPS, cabeçalhos e autenticação podem mudar em produção.
- **O relatório do ZAP não foi exportado.** Os resultados estão nas capturas e nos CSV.

## Observação fora do ZAP

A resposta de `/v1/auth/refresh` (captura 05b) devolve o `access_token` no cookie `HttpOnly` e também no corpo JSON. Isso reduz o efeito do `HttpOnly`. O ZAP não apontou isso, e não verificamos no código do front se ele usa o token do corpo. Fica como ponto a investigar.

## Próximas etapas

- Repetir o active scan com token renovado por script de autenticação do ZAP, incluindo `manager` e as rotas de escrita. Excluir `/v1/auth/logout` e `/v1/auth/refresh` e reduzir as threads, pois o scan atingiu o limite da API (`429`).
- Rodar o ZAP no CI (etapa 7) para que os cabeçalhos corrigidos não regridam.
- Monitorar eventos de segurança em execução (etapa 6).
- Registrar na etapa 2 um risco de configuração insegura de cabeçalhos HTTP.
