# Protótipo PSP: frontend

Frontend do protótipo acadêmico de engenharia de software seguro. Mostra só dois
pontos do sistema original: o login (mock) e o módulo **Faturamento PSP**
(lançamentos).

## Stack

- Next.js 16 (App Router) e React 19
- TypeScript, Tailwind CSS 4 e componentes no estilo shadcn/ui
- TanStack Query v5 para dados do backend
- Biome (lint e formatação) e Vitest (testes)

## Pré-requisitos

- Node.js 20 ou superior
- pnpm 10.28.1
- Backend do protótipo rodando (FastAPI, por padrão em `http://localhost:8000`)

## Como rodar

```bash
pnpm install
cp .env.example .env.local   # ajuste NEXT_PUBLIC_BACKEND_URL se necessário
pnpm dev
```

Acesse `http://localhost:3000/login`. Sem sessão, qualquer rota redireciona
para o login.

## Usuários de demonstração

| Usuário   | Perfil  |
|-----------|---------|
| `admin`   | admin   |
| `analyst` | analista |
| `manager` | gestor  |

As senhas ficam no seed de usuários do backend e não são documentadas aqui.
Para ações de gestor ou admin, o backend pode exigir o código MFA (OTP) no campo
**Código MFA (OTP)** do login. Sem exigência, deixe o campo vazio.

## Variáveis de ambiente

| Nome                       | Padrão                  | Uso                                   |
|----------------------------|-------------------------|---------------------------------------|
| `NEXT_PUBLIC_BACKEND_URL`  | `http://localhost:8000` | URL base da API. Fixada no build.     |

## Scripts

```bash
pnpm dev          # servidor de desenvolvimento
pnpm build        # build de produção (saída standalone; use o Docker para servir)
pnpm test:run     # testes uma vez
pnpm lint         # biome check
pnpm lint:fix     # biome check --write
```

## Docker

Para produção, use a imagem. `pnpm start` não serve a saída standalone.

```bash
docker build --build-arg NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 -t prototipo-psp-frontend .
docker run --rm -p 3000:3000 prototipo-psp-frontend
```

## Estrutura

```
app/
  (auth)/login/     formulário de login (mock)
  (psp)/psp/        Faturamento PSP
  layout.tsx        providers globais
proxy.ts            exige cookie de sessão; /login é a única rota pública
components/
  layout/           sidebar, cabeçalho e layout compartilhado
  psp/              tabela, filtros, resumo e modais de lançamentos
  ui/               componentes de interface base
hooks/psp/          estado e ações da tela PSP
lib/billing/psp.ts  chamadas à API de faturamento (TanStack Query)
lib/fetch-client.ts fetch com cookies, refresh de sessão e tratamento de erro
features/auth/      contexto e cliente de autenticação
```

## Fora do escopo do protótipo

Módulos como dashboard, cadastros, aprovações, integração ERP, provisão e rede
não existem aqui. Anexos e SSO também foram removidos. O WebSocket existe só para o aviso de
mudança no faturamento (veja o README da raiz do protótipo).
