# Etapa 5 — Correções propostas

Para cada achado da [análise](etapa-5-analise-dos-achados.md), a correção segue a mesma ordem: problema, medida, exemplo, referência e verificação.

## A01 — CSP com `unsafe-inline`

1. **Problema.** O `script-src` e o `style-src` aceitam `'unsafe-inline'`. A CSP não bloqueia um script injetado no HTML. A política também não define `form-action`.
2. **Medida.** Gerar um nonce por requisição em um `middleware.ts` do Next.js, montar a CSP com ele e remover `'unsafe-inline'` do `script-src`. Acrescentar `form-action 'self'`. O `style-src` pode ficar para uma segunda rodada, porque estilos inline em React costumam depender de bibliotecas de terceiros.
3. **Exemplo.** Trecho do `middleware.ts`, no lugar da CSP fixa do `next.config.ts`:

   ```ts
   // O nonce muda a cada requisição. Um script injetado não conhece o valor
   // e o navegador o bloqueia, mesmo que ele esteja inline.
   const nonce = Buffer.from(crypto.randomUUID()).toString("base64");

   const csp = [
     "default-src 'self'",
     `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
     "form-action 'self'",
     "object-src 'none'",
     "base-uri 'self'",
     "frame-ancestors 'none'",
   ].join("; ");
   ```

   Efeito colateral: com nonce, as páginas passam a ser renderizadas a cada requisição, sem cache estático.

4. **Referência OWASP.** OWASP Content Security Policy Cheat Sheet. ASVS 4.0.3, requisito V14.4.3.
5. **Como verificar.** Repetir o passive scan com navegação completa e esperar que os alertas `script-src unsafe-inline` e "Failure to Define Directive with No Fallback" desapareçam. Conferir no console do navegador que nenhuma violação de CSP quebra as telas `/psp` e `/service-rules`. Testar também com `pnpm build && pnpm start`, porque o modo `dev` usa uma política diferente.

## A02 — `X-Content-Type-Options` ausente na API

1. **Problema.** As respostas do backend não trazem `X-Content-Type-Options: nosniff`. O front envia esse cabeçalho e a API não.
2. **Medida.** Um middleware no FastAPI que acrescenta o cabeçalho a todas as respostas, inclusive as de erro.
3. **Exemplo.** Em `backend/src/presentation/api/main.py`, ao lado do middleware de `X-Request-ID`:

   ```python
   @app.middleware("http")
   async def security_headers_middleware(
       request: Request, call_next: Callable[[Request], Awaitable[Response]]
   ) -> Response:
       response = await call_next(request)
       # Impede o navegador de adivinhar o tipo do conteúdo. A API só serve JSON,
       # então qualquer interpretação diferente seria um desvio.
       response.headers.setdefault("X-Content-Type-Options", "nosniff")
       return response
   ```

4. **Referência OWASP.** OWASP HTTP Headers Cheat Sheet. ASVS 4.0.3, requisito V14.4.4.
5. **Como verificar.** Rodar `curl -i http://localhost:8000/v1/auth/get-session` e confirmar a linha `x-content-type-options: nosniff` mesmo na resposta `401`. Adicionar um teste em `backend/tests/` que confira o cabeçalho em uma rota pública e em uma rota que devolve erro. Repetir o passive scan e esperar que o alerta desapareça.

## A03 — Vazamento de informação por `X-Powered-By`

1. **Problema.** O servidor informa a tecnologia (Next.js) em um cabeçalho de resposta que nenhum cliente legítimo usa.
2. **Medida.** Desligar o cabeçalho no Next.js. De forma opcional, esconder também o `server: uvicorn` do backend, que apareceu na captura 05b mas que o ZAP não apontou.
3. **Exemplo.** Em `frontend/next.config.ts`:

   ```ts
   const nextConfig: NextConfig = {
     poweredByHeader: false,
     // ...restante da configuração
   };
   ```

   No backend, a opção equivalente do uvicorn é `--no-server-header`.

4. **Referência OWASP.** OWASP Secure Headers Project e ASVS 4.0.3, requisito V14.3.3.
5. **Como verificar.** Rodar `curl -I http://localhost:3000` e confirmar que `x-powered-by` não aparece. Repetir o passive scan e esperar que o alerta desapareça.

## Prioridade

| Achado | Esforço                                  | Redução de risco | Ordem sugerida |
| ------ | ---------------------------------------- | ---------------- | :------------: |
| A02    | baixo (um middleware, um teste)          | baixa            |       1        |
| A03    | baixo (uma opção de config)              | baixa            |       2        |
| A01    | alto (nonce, middleware, testes de tela) | média            |       3        |

A ordem segue o esforço: A02 e A03 saem em minutos e eliminam dois alertas. O A01 reduz mais risco, mas mexe na renderização das páginas e pede mais testes, então vai por último e em um PR separado.

As correções são propostas de correção. Ainda não foram aplicadas nem testadas, então a redução de risco continua sendo uma estimativa.

---
