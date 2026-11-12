# Etapa 5 — Ambiente e configuração

Este documento responde três perguntas: o que foi testado, com qual ferramenta e com qual configuração.

## Sistema testado

Protótipo do faturamento PSP, em `extra/prototipo-psp/`.

| Componente | Tecnologia            | Endereço local          | Alvo do teste  |
| ---------- | --------------------- | ----------------------- | -------------- |
| Backend    | FastAPI (Python 3.11) | `http://localhost:8000` | sim            |
| Frontend   | Next.js               | `http://localhost:3000` | sim            |
| Dados      | Redis 7               | `localhost:6379`        | fora do escopo |

O protótipo roda só na máquina local e usa usuários e dados fictícios (`analyst`, `manager`, `admin`). Nenhum dado real foi usado.

O frontend rodou em **modo de desenvolvimento** (`pnpm dev`). Isso muda a política de CSP: o `next.config.ts` acrescenta `'unsafe-eval'` ao `script-src` quando `NODE_ENV` é `development`. Os alertas de CSP devem ser relidos com essa ressalva.

## Ferramenta

- ZAP (Zed Attack Proxy), versão 2.17.0.
- Forma de execução: aplicação desktop, instalada localmente.
- Navegador: o Firefox aberto pelo próprio ZAP, já configurado para usar o proxy em `localhost:8080`.

## Como o ambiente foi subido

Passo a passo resumido do [README do protótipo](../../extra/prototipo-psp/README.md). Os valores de `JWT_SECRET`, da senha e do OTP ficam no `.env` local e não aparecem aqui.

```bash
# Redis descartável
docker run --rm -p 6379:6379 redis:7-alpine

# Backend, na porta 8000
cd extra/prototipo-psp/backend
.venv/bin/uvicorn src.presentation.api.main:create_app --factory --port 8000

# Frontend, na porta 3000
cd frontend && pnpm dev

# Ou via container docker
docker compose up --build
```

## Configuração do teste

| Item                   | Valor                                                                                                                                                                                                               |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Contexto do ZAP        | `http://localhost:3000` e `http://localhost:8000` incluídos ([captura 01](../../evidencias/etapa-5/Backend/01-contexto-zap.png))                                                                                    |
| Fonte da API           | Importação de `http://localhost:8000/openapi.json` e navegação manual pelo front com o proxy do ZAP ([captura 02](../../evidencias/etapa-5/Backend/02-rotas-importadas.png))                                        |
| Autenticação           | Inicialmente feito com usuário `analyst`. Regra "Token Analyst" no Replacer, que envia `Authorization: Bearer <token>` em todas as requisições ([captura 03](../../evidencias/etapa-5/Backend/03-autenticacao.png)) |
| Tipos de varredura     | Scan Passivo e Ativo                                                                                                                                                                                                |
| Política do Scan Ativo | Padrão                                                                                                                                                                                                              |
| Modo do ZAP            | Protegido, para o ZAP atacar só URLs do contexto                                                                                                                                                                    |

**Sessões de validação.** A etapa tem duas validações, uma por perfil.

- **`analyst`:** não exige MFA. Deu origem às capturas 04a a 05b e ao CSV do scan ativo do frontend. Nessa sessão, as rotas de escrita de `service-rules` **não foram alcançadas**, porque `manager` e `admin` exigem MFA e um token sem segundo fator recebe `401 mfa_necessario`.
- **`admin`:** o `admin` navegou pelo front com o proxy do ZAP ligado e passou pelo login com MFA, o que alcançou as rotas de escrita. O histórico do scan passivo está em [`scan-passivo-admin.csv`](../../evidencias/etapa-5/Backend/scan-passivo-admin.csv). O active scan do backend com esse perfil está em [`scan-ativo-admin.csv`](../../evidencias/etapa-5/Backend/scan-ativo-admin.csv).

**Observação sobre o token.** O token de acesso do protótipo vale 15 minutos (Max-Age=900 no cookie). A regra do Replacer guarda um valor fixo. Depois que o token expira, as requisições do scanner passam a receber `401`. Esse ponto afeta a leitura do active scan e está detalhado em [Limitações](etapa-5-limitacoes.md).

---
