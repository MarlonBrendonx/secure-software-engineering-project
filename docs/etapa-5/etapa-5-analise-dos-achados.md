# Etapa 5 — Análise dos achados

O passive scan do ZAP apontou 11 alertas no nosso protótipo. Escolhemos três para analisar, de tipos diferentes. Foram uma política de CSP fraca no front (A01), um cabeçalho de segurança que falta na API (A02) e um cabeçalho que revela a tecnologia do servidor (A03).

Os três são problemas de configuração, não de lógica do sistema. Nenhum deles, sozinho, dá acesso a dados, mas todos deixam o trabalho de um atacante mais fácil se ele já tiver encontrado outra brecha. Os três vieram do passive scan. O active scan não gerou nenhum alerta novo, e explicamos o porquê em [Limitações](etapa-5-limitacoes.md).

| ID  | Alerta                           | Onde                  | Gravidade | Correção                                                                                 |
| --- | -------------------------------- | --------------------- | :-------: | ---------------------------------------------------------------------------------------- |
| A01 | CSP com `unsafe-inline`          | front (`:3000`)       |  Medium   | nonce por requisição e `form-action 'self'` ([detalhes](etapa-5-correcoes-propostas.md)) |
| A02 | `X-Content-Type-Options` ausente | API (`:8000`)         |    Low    | middleware no FastAPI                                                                    |
| A03 | `X-Powered-By` exposto           | provavelmente o front |    Low    | `poweredByHeader: false`                                                                 |

As evidências são a captura [04a](../../evidencias/etapa-5/Backend/04a-alertas-passivo.png), com a lista dos 11 alertas, e a [5b](../../evidencias/etapa-5/Backend/5b-scan-ativo-politicas-aplicadas.png), com o detalhe do A02.

---

## A01 — CSP com `unsafe-inline`

A CSP é um cabeçalho em que o servidor diz ao navegador de onde os scripts e estilos de uma página podem vir. Ela serve de segunda barreira contra XSS, porque se alguém conseguir injetar um script na página, a CSP pode impedir que ele rode. O `'unsafe-inline'` abre uma exceção para tudo o que está escrito direto no HTML, e um script injetado entra nessa exceção.

O ZAP gerou três alertas dessa família, todos Medium e com 3 ocorrências cada. São eles o `script-src unsafe-inline`, o `style-src unsafe-inline` e o "Failure to Define Directive with No Fallback". Esse último indica uma diretiva que a política não define e que não herda valor de outra. Achamos que é a `form-action`, mas ainda precisamos confirmar no detalhe do alerta.

Os alertas são de respostas do front (`http://localhost:3000`). Conferimos no código e a causa está no `next.config.ts`, linhas 14 a 24, onde a política tem `script-src 'self' 'unsafe-inline'` e `style-src 'self' 'unsafe-inline'`. A captura 04a mostra os três alertas na lista. Ainda falta tirar a captura do detalhe, com a URL e o cabeçalho (veja [Execução e evidências](etapa-5-execucao-e-evidencias.md)).

Para o nosso sistema, o ponto que mais pesa é o token. A sessão fica em cookie, mas a resposta do login também devolve o `access_token` no corpo JSON, como se vê na captura 5b. Se existir uma brecha de XSS algum dia, o script injetado teria um token ao alcance. Uma CSP mais rígida bloquearia esse script antes.

Também vale dizer que o `'unsafe-inline'` não está ali por descuido. O Next.js injeta pequenos scripts inline para montar a página, e a política precisa permitir isso. Para tirar a exceção seria preciso usar um nonce, um código que muda a cada requisição, e isso dá mais trabalho. Além disso, o front rodou com `pnpm dev`, e nesse modo o `script-src` ainda leva `'unsafe-eval'`. Em produção a política é um pouco mais enxuta.

Na classificação, é OWASP Top 10 2021 A05 (Security Misconfiguration) e CWE-693 (Protection Mechanism Failure). O ZAP deu gravidade Medium.

---

## A02 — `X-Content-Type-Options` ausente na API

Sem o cabeçalho `X-Content-Type-Options: nosniff`, alguns navegadores tentam descobrir sozinhos o tipo de uma resposta, mesmo quando o servidor já informou qual é. Isso pode fazer um JSON ser tratado como HTML com script, por exemplo. O cabeçalho desliga esse palpite.

O ZAP não encontrou o cabeçalho nas respostas do backend (`http://localhost:8000`). O alerta é do tipo _Systemic_, ou seja, se repete em vários endereços. A captura 5b mostra o caso do `POST /v1/auth/refresh`, cuja resposta traz `server: uvicorn` e `content-type: application/json`, sem nenhum `x-content-type-options`. No `main.py`, o único cabeçalho que a API acrescenta é o `X-Request-ID`. Na captura, o ZAP marca risco Low, confiança Medium, CWE 693, WASC 15 e fonte "Passivo (10021)".

Uma observação sobre a captura. Ela está na pasta do scan ativo, mas o campo "Fonte" mostra que o alerta saiu do passive scan.

O risco direto é baixo, porque a API só devolve JSON. O que nos chamou atenção foi a diferença entre os dois lados, já que o front já envia esse cabeçalho (`next.config.ts`) e a API não. A configuração de cabeçalhos foi feita só de um lado. Corrigir custa uma linha.

Na classificação, é OWASP Top 10 2021 A05 e CWE-693. O ZAP deu gravidade Low, com confiança Medium.

---

## A03 — `X-Powered-By` exposto

O cabeçalho `X-Powered-By` informa qual tecnologia gerou a resposta. Nenhum usuário precisa dele, mas quem está fazendo reconhecimento usa a informação para procurar falhas conhecidas daquele framework e daquela versão.

O ZAP encontrou o cabeçalho em 3 respostas, com gravidade Low. Achamos que ele vem do front, porque o Next.js envia `X-Powered-By: Next.js` por padrão e o nosso `next.config.ts` não define `poweredByHeader: false`. Essa conclusão vem da leitura do código. A captura 04a mostra só a linha "O servidor vaza informações por meio dos campos de cabeçalho de resposta HTTP X-Powered-By (3)", sem a URL, então ainda falta confirmar no detalhe do alerta.

Esconder o cabeçalho não conserta nenhuma falha. Só tira uma pista de graça de quem está procurando. O risco aqui é de reconhecimento, não de invasão.

Na classificação, é OWASP Top 10 2021 A05 e CWE-497, que também precisa ser confirmado no detalhe do alerta. O ZAP deu gravidade Low, e não registramos a confiança.

---

## Relação com as etapas anteriores

A regra de negar por padrão (RS06) se confirmou. No CSV do backend, as 350 requisições a `/v1/billing` e `/v1/registry` sem token válido receberam `401` e nenhuma devolveu dados. As rotas que não existem receberam `404`.

O ZAP não testou a autorização por recurso (R03, TS01 e TS02) nem o MFA. O scanner nunca passou da autenticação e só usamos o perfil `analyst`. Saber se um analista consegue ler o lançamento de outro cliente continua dependendo dos testes da etapa 4.

Por fim, encontramos uma lacuna no nosso registro de riscos. Nenhum risco ou requisito das etapas 2 e 3 trata de cabeçalhos HTTP de segurança, e os três achados caem justamente aí.

---
