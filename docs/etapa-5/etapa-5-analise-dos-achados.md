# Etapa 5 — Análise dos achados

Esta análise usa duas validações, uma com cada perfil. A sessão `analyst` deu a lista de alertas da captura 04a. A sessão `admin` deu o histórico do scan passivo com login por MFA e rotas de escrita. O passive scan do ZAP apontou 11 alertas no nosso protótipo, na sessão `analyst`. Escolhemos três para analisar, de tipos diferentes. Foram uma política de CSP fraca no front (A01), um cabeçalho de segurança que falta na API (A02) e um cabeçalho que revela a tecnologia do servidor (A03).

Os três são problemas de configuração, não de lógica do sistema. Nenhum deles, sozinho, dá acesso a dados, mas todos deixam o trabalho de um atacante mais fácil se ele já tiver encontrado outra brecha. Os três vieram do passive scan. O active scan como `analyst` não gerou nenhum alerta novo, e explicamos o porquê em [Limitações](etapa-5-limitacoes.md).

| ID  | Alerta                           | Onde            | Gravidade | Correção                                                                                 |
| --- | -------------------------------- | --------------- | :-------: | ---------------------------------------------------------------------------------------- |
| A01 | CSP com `unsafe-inline`          | Front (`:3000`) |  Medium   | nonce por requisição e `form-action 'self'` ([detalhes](etapa-5-correcoes-propostas.md)) |
| A02 | `X-Content-Type-Options` ausente | API (`:8000`)   |    Low    | middleware no FastAPI                                                                    |
| A03 | `X-Powered-By` exposto           | Front (`:3000`) |    Low    | `poweredByHeader: false`                                                                 |

## Validação com o perfil `admin`

Esta validação soma-se à do `analyst`, e uma não substitui a outra. O CSV do `admin` mostra só o nível máximo por mensagem, sem o nome do alerta. Por isso não dá para comparar o total de alertas das duas sessões. Aqui o `admin` serve para checar se os achados se repetem e se as rotas de escrita geram algo novo.

O [histórico do scan passivo como `admin`](../../evidencias/etapa-5/Backend/scan-passivo-admin.csv) tem 64 mensagens e cobre o que a sessão `analyst` não cobriu: o login com MFA e as rotas de escrita.

- **Cobertura autenticada.** A sessão passou por `login`, `get-session`, `refresh`, `registry` (clientes, programas e regras de serviço) e `billing` (listagem, média, criação de lançamento). O passive scan analisou respostas reais dessas rotas, e não apenas `401`.
- **Onde estão os alertas.** Os 2 alertas **Médios** estão nas páginas do front (`/login` e `/psp`). Isso bate com o A01, porque a CSP é um cabeçalho que o front envia em toda página. Os 2 alertas **Baixos** estão nas duas chamadas a `GET /v1/auth/get-session`, na API. Esses dois são compatíveis com o A02. O CSV só mostra o nível, então a ligação com cada alerta é uma inferência, confirmada pelos cabeçalhos abaixo.
- **Nenhum alerta nas rotas de escrita.** As rotas de escrita (`POST` com `201` e `200`) não geraram alerta de nível Baixo ou maior. O passive scan só lê as respostas e não testa a lógica dessas rotas. Isso não prova que elas estão corretas.
- **Active scan como `admin`.** O [histórico do active scan](../../evidencias/etapa-5/Backend/scan-ativo-admin.csv) tem 445 requisições ao backend e nenhum `401`, ao contrário do `analyst`. A maioria das respostas em `/v1/billing` e `/v1/registry` foi `422`, e `registry` devolveu `200` em 23 delas. O token passou, mas os parâmetros do scanner foram rejeitados pela validação. Só há `GET` no histórico, então as rotas de escrita não foram atacadas. O CSV não traz os alertas.
- **A API usou CORS corretamente.** Os 4 `OPTIONS` (preflight) da sessão receberam `200`. Conferimos direto que a origem `http://localhost:3000` é aceita e que uma origem estranha recebe `400`.

### Confirmação direta dos cabeçalhos

Como o export csv não nomeia os alertas, conferimos os cabeçalhos com `curl` no protótipo em execução.

| Achado | Comando                                             | Resultado                                                                                                                       |
| ------ | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| A01    | `curl -I http://localhost:3000/login`               | CSP com `script-src 'self' 'unsafe-inline'` e `style-src 'self' 'unsafe-inline'`, sem `form-action`                             |
| A02    | `curl -i http://localhost:8000/v1/auth/get-session` | `401` com `server: uvicorn` e `x-request-id`, **sem** `x-content-type-options`. O mesmo vale para a resposta `405` de `/health` |
| A03    | `curl -I http://localhost:3000/login`               | `X-Powered-By: Next.js` presente. A API não envia esse cabeçalho, só `server: uvicorn`                                          |

Isso **confirma o A03 como problema do front** (antes era só uma leitura do código) e confirma que o front já envia `X-Content-Type-Options: nosniff` e a API não (A02). Nessa checagem, a CSP não trazia `'unsafe-eval'` e as páginas vinham com cabeçalhos de pré-renderização do Next.js. Isso indica que o front estava rodando como build de produção. Por isso a CSP do scan e a do `curl` podem diferir só pelo `'unsafe-eval'`.

As evidências são a captura [04a](../../evidencias/etapa-5/Backend/04a-alertas-passivo.png), com a lista dos 11 alertas, e a [05b](../../evidencias/etapa-5/Backend/05b-scan-ativo-politicas-aplicadas.png), com o detalhe do A02.

---

## A01 — CSP com `unsafe-inline`

A CSP é um cabeçalho em que o servidor diz ao navegador de onde os scripts e estilos de uma página podem vir. Ela serve de segunda barreira contra XSS, porque se alguém conseguir injetar um script na página, a CSP pode impedir que ele rode. O `'unsafe-inline'` abre uma exceção para tudo o que está escrito direto no HTML, e um script injetado entra nessa exceção.

O ZAP gerou três alertas dessa família, todos Medium e com 3 ocorrências cada. São eles o `script-src unsafe-inline`, o `style-src unsafe-inline` e o "Failure to Define Directive with No Fallback". Esse último indica uma diretiva que a política não define e que não herda valor de outra. Achamos que é a `form-action`, mas ainda precisamos confirmar no detalhe do alerta.

Os alertas são de respostas do front (`http://localhost:3000`). Conferimos no código e a causa está no `next.config.ts`, linhas 14 a 24, onde a política tem `script-src 'self' 'unsafe-inline'` e `style-src 'self' 'unsafe-inline'`. A captura 04a mostra os três alertas na lista. Ainda falta tirar a captura do detalhe, com a URL e o cabeçalho ([Execução e evidências](etapa-5-execucao-e-evidencias.md)).

Para o nosso sistema, o ponto que mais pesa é o token. A sessão fica em cookie, mas a resposta do login também devolve o `access_token` no corpo JSON, como se vê na captura 05b. Se existir uma brecha de XSS algum dia, o script injetado teria um token ao alcance. Uma CSP mais rígida bloquearia esse script antes.

Também vale dizer que o `'unsafe-inline'` não está ali por descuido. O Next.js injeta pequenos scripts inline para montar a página, e a política precisa permitir isso. Para tirar a exceção seria preciso usar um nonce, um código que muda a cada requisição, e isso dá mais trabalho. Além disso, o front rodou com `pnpm dev`, e nesse modo o `script-src` ainda leva `'unsafe-eval'`. Em produção a política é um pouco mais enxuta.

Na classificação, é OWASP Top 10 2021 A05 (Security Misconfiguration) e CWE-693 (Protection Mechanism Failure). O ZAP deu gravidade Medium.

---

## A02 — `X-Content-Type-Options` ausente na API

Sem o cabeçalho `X-Content-Type-Options: nosniff`, alguns navegadores tentam descobrir sozinhos o tipo de uma resposta, mesmo quando o servidor já informou qual é. Isso pode fazer um JSON ser tratado como HTML com script, por exemplo. O cabeçalho desliga esse palpite.

O ZAP não encontrou o cabeçalho nas respostas do backend (`http://localhost:8000`). O alerta é do tipo _Systemic_, ou seja, se repete em vários endereços. A captura 05b mostra o caso do `POST /v1/auth/refresh`, cuja resposta traz `server: uvicorn` e `content-type: application/json`, sem nenhum `x-content-type-options`. No `main.py`, o único cabeçalho que a API acrescenta é o `X-Request-ID`. Na captura, o ZAP marca risco Low, confiança Medium, CWE 693, WASC 15 e fonte "Passivo (10021)".

Uma observação sobre a captura. Ela está na pasta do scan ativo, mas o campo "Fonte" mostra que o alerta saiu do passive scan.

O risco direto é baixo, porque a API só devolve JSON. O que nos chamou atenção foi a diferença entre os dois lados, já que o front já envia esse cabeçalho (`next.config.ts`) e a API não. A configuração de cabeçalhos foi feita só de um lado. Corrigir custa uma linha.

Na classificação, é OWASP Top 10 2021 A05 e CWE-693. O ZAP deu gravidade Low, com confiança Medium.

---

## A03 — `X-Powered-By` exposto

O cabeçalho `X-Powered-By` informa qual tecnologia gerou a resposta. Nenhum usuário precisa dele, mas quem está fazendo reconhecimento usa a informação para procurar falhas conhecidas daquele framework e daquela versão.

O ZAP encontrou o cabeçalho em 3 respostas, com gravidade Low. Ele vem do front: o Next.js envia `X-Powered-By: Next.js` por padrão e o nosso `next.config.ts` não define `poweredByHeader: false`. Confirmamos com `curl -I http://localhost:3000/login`, que devolve o cabeçalho (tabela acima). O detalhe do alerta no ZAP confirma a evidência `X-Powered-By: Next.js`, com confiança Medium, origem na regra passiva 10037, CWE-497 e WASC-13. A captura do detalhe não mostra a URL das 3 respostas, que aparece na lista de mensagens do alerta.

Esconder o cabeçalho não conserta nenhuma falha. Só tira uma pista de graça de quem está procurando. O risco aqui é de reconhecimento, não de invasão.

Na classificação, é OWASP Top 10 2021 A05 e CWE-497. O ZAP deu gravidade Low, com confiança Medium. As etiquetas do próprio ZAP apontam para outras categorias (OWASP 2017 A03 e OWASP 2025 A01), porque ele classifica o vazamento como exposição de informação. Mantemos a A05 de 2021 por ser uma falha de configuração do servidor.

---

## Relação com as etapas anteriores

A regra de negar por padrão (RS06) se confirmou. No active scan como `analyst`, as requisições a `/v1/billing` e `/v1/registry` sem token válido receberam `401` e nenhuma devolveu dados. As rotas que não existem receberam `404`.

A sessão `admin` mostrou o MFA funcionando no fluxo normal: o único `401` foi o `refresh` anterior ao login, e depois do login as rotas protegidas responderam `200` ou `201`. Isso mostra que o login com MFA entrega uma sessão válida, mas não testa um ataque contra o MFA.

O ZAP não testou a autorização por recurso (R03, TS01 e TS02). O passive scan só observa o tráfego, e o active scan como `analyst` não passou da autenticação. Como `admin`, ele passou, mas só com `GET`. Saber se um analista consegue ler o lançamento de outro cliente continua dependendo dos testes da etapa 4. A sessão `admin` também não ajuda nisso, porque o `admin` tem escrita em todo o escopo.

Por fim, encontramos uma lacuna no nosso registro de riscos. Nenhum risco ou requisito das etapas 2 e 3 trata de cabeçalhos HTTP de segurança, e os três achados se enquadram nessas falhas.

---
