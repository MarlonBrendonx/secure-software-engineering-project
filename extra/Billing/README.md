# Network Billing

Sistema interno de faturamento da rede credenciada.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 16 · Redis 7 · React 18 + TypeScript + Vite · Nginx · Docker.

Este arquivo tem duas partes:
- **Instalação e operação** (seções 1 a 14): subir com Docker, configurar o login pelo Google, primeiro acesso, backup e solução de problemas.
- **Desenvolvimento e referência técnica** (seções 15 a 21): rodar sem containers, testes, frontend, SSO e 2FA, segurança e pontos em aberto.

### Estado da implementação

| Módulo | Situação |
|---|---|
| 1. Fundação: SSO (Google, Microsoft, corporativo), 2FA por app autenticador, perfis, substituições, auditoria, parâmetros | ✅ pronto, 75 testes |
| 2. Contratos e motor de cálculo | a fazer |
| 3. Lançamentos, aprovação e anexos | a fazer |
| 4. Fechamento e reabertura | a fazer |
| 5. Carga ERP | a fazer |
| 6. Integração Oracle | a fazer |
| 7. Frontend | telas do módulo 1 prontas (login, 2FA, usuários, substituições, auditoria, parâmetros); as de billing entram com os módulos 2 a 5 |
| 8. Infra, deploy e testes de ponta a ponta | Docker Compose pronto (API, web, Postgres, Redis); falta HTTPS próprio e envio de e-mail |
---

## Sumário

**Instalação e operação**

1. [Pré-requisitos](#1-pré-requisitos)
2. [Obter o projeto](#2-obter-o-projeto)
3. [Como o sistema roda](#3-como-o-sistema-roda)
4. [Subir o sistema](#4-subir-o-sistema)
5. [Primeiro acesso (sem Google)](#5-primeiro-acesso-sem-google)
6. [Login pelo Google: criar o projeto no Google Cloud](#6-login-pelo-google-criar-o-projeto-no-google-cloud)
7. [Criar o `.env` com o ID e a chave do Google](#7-criar-o-env-com-o-id-e-a-chave-do-google)
8. [Primeiro login pelo Google](#8-primeiro-login-pelo-google)
9. [Login pela Microsoft (opcional)](#9-login-pela-microsoft-opcional)
10. [Uso real (produção)](#10-uso-real-produção)
11. [Configurações opcionais](#11-configurações-opcionais)
12. [Operação do dia a dia](#12-operação-do-dia-a-dia)
13. [Solução de problemas](#13-solução-de-problemas)
14. [Desinstalar](#14-desinstalar)

**Desenvolvimento e referência técnica**

15. [Desenvolvimento sem containers](#15-desenvolvimento-sem-containers)
16. [Testes automatizados](#16-testes-automatizados)
17. [Frontend](#17-frontend)
18. [Login: SSO e verificação em duas etapas](#18-login-sso-e-verificação-em-duas-etapas)
19. [Decisões de segurança](#19-decisões-de-segurança)
20. [Parâmetros configuráveis](#20-parâmetros-configuráveis)
21. [Pontos em aberto](#21-pontos-em-aberto)

---

## 1. Pré-requisitos

| Item | Versão mínima | Observação |
|---|---|---|
| Docker | Engine 24+ ou Docker Desktop 4.27+ | No Windows e no macOS, use o Docker Desktop |
| Docker Compose | v2.24+ | Já vem com o Docker. Confira com `docker compose version` |
| Porta livre | 8080 | Pode ser trocada (veja a [seção 11](#trocar-a-porta)) |
| Espaço em disco | ~2 GB | Para as imagens e a compilação |
| Internet | — | Para baixar as imagens e, depois, para o login pelo Google |
| Celular | — | Com um aplicativo autenticador: Google Authenticator, Microsoft Authenticator, Authy ou similar |

Para o login pelo Google, você também vai precisar de uma conta Google para acessar o
[Google Cloud Console](https://console.cloud.google.com). O cadastro do login é gratuito.

**Python, Node.js, PostgreSQL e Redis não precisam estar instalados:** tudo roda dentro dos contêineres.

Para conferir se o Docker está pronto:

```bash
docker --version
docker compose version
```

---

## 2. Obter o projeto

Clone o repositório (ou extraia o `.zip`) e entre na pasta:

```bash
git clone <endereço-do-repositório> Billing
cd Billing
```

**Todos os comandos deste guia devem ser executados dentro da pasta `Billing`**, a que tem o arquivo
`docker-compose.yml`. A única exceção é a criação do `.env`, na [seção 7](#7-criar-o-env-com-o-id-e-a-chave-do-google).

A estrutura relevante para a instalação é esta:

```
Billing/
├── docker-compose.yml        # sobe os 4 contêineres
├── .env.example              # modelo com todas as configurações possíveis
├── backend/
│   ├── Dockerfile            # imagem da API (Python)
│   └── .env                  # sua configuração (você cria na seção 7; não vai para o git)
├── frontend/
│   ├── Dockerfile            # imagem da interface (React compilado + Nginx)
│   └── nginx.conf
└── infra/postgres-init.sql   # cria o usuário do banco usado pela aplicação
```

---

## 3. Como o sistema roda

```
                  Navegador
                      │ http://localhost:8080
                      ▼
          ┌───────────────────────┐          ┌───────────────────────┐
          │          web          │  /api →  │          api          │
          │  interface + Nginx    │─────────►│  FastAPI (Python)     │
          │  (único com porta)    │          │  sem porta exposta    │
          └───────────────────────┘          └───┬───────────┬───────┘
                                                 │           │
                                     ┌───────────▼──┐   ┌────▼────────┐
                                     │   postgres   │   │    redis    │
                                     │  dados       │   │  limite de  │
                                     │              │   │  tentativas │
                                     └──────────────┘   └─────────────┘

        Login: Google / Microsoft (SSO)  ou  usuário e senha  →  código do aplicativo autenticador
```

| Contêiner | O que roda | Porta |
|---|---|---|
| `web` | Nginx com a interface já compilada; repassa `/api` para a API | **8080** |
| `api` | API em Python. Na subida, espera o banco, aplica as migrations e gera as chaves que faltarem | nenhuma |
| `postgres` | PostgreSQL 16 | 5432, só em `127.0.0.1` |
| `redis` | Redis 7 | 6379, só em `127.0.0.1` |

Os dados ficam em dois volumes do Docker:
- `pgdata`: o banco.
- `segredos`: as chaves geradas automaticamente.

**Os dois volumes precisam entrar no backup.**

---

## 4. Subir o sistema

```bash
docker compose up -d --build
```

A primeira execução leva alguns minutos, porque baixa as imagens e compila a interface. Ao final, confira
se os quatro contêineres estão `healthy`:

```bash
docker compose ps
```

```
NAME                 SERVICE    STATUS
billing-api-1        api        Up 1 minute (healthy)
billing-postgres-1   postgres   Up 1 minute (healthy)
billing-redis-1      redis      Up 1 minute (healthy)
billing-web-1        web        Up 1 minute (healthy)
```

Abra **http://localhost:8080**. Sem o `.env`, a tela de login mostra "Nenhum provedor de login configurado".
Isso é esperado: o botão do Google aparece depois da [seção 7](#7-criar-o-env-com-o-id-e-a-chave-do-google).

> Não é preciso criar chaves à mão. Na primeira subida, a API gera a chave da sessão (JWT) e a chave que
> criptografa os segredos do 2FA, e guarda as duas no volume `segredos`. O log mostra:
> ```
> [billing] gerando a chave do JWT em /segredos
> [billing] gerando a chave de criptografia do 2FA em /segredos
> ```

---

## 5. Primeiro acesso (sem Google)

O jeito mais rápido de entrar é com uma conta de **usuário e senha**:

```bash
docker compose exec api nbb create-local-user admin.local "Seu Nome" seu-email+local@gmail.com --roles admin
```

O comando pede a senha duas vezes. A senha precisa ter **12 caracteres ou mais** e combinar ao menos 3 tipos
entre minúsculas, maiúsculas, números e símbolos, por exemplo `Billing#2026ok`.

> Use um e-mail **diferente** do que você vai usar no Google (o `+local` resolve). O sistema recusa o login
> pelo Google quando já existe uma conta de usuário e senha com o mesmo e-mail.

Depois, no navegador:

1. Abra **http://localhost:8080** e clique em **"Entrar com usuário e senha"**.
2. Informe o usuário (`admin.local`) e a senha.
3. Como o perfil **Administrador** exige verificação em duas etapas, aparece um aviso amarelo. Clique em
   **Ativar agora** (ou na aba **Segurança da conta**).
4. Clique em **Ativar verificação em duas etapas**. Aparece um **QR code**:
   - no celular, abra o aplicativo autenticador e toque em "adicionar";
   - leia o QR code. Se não conseguir, clique em "Não consegue ler o QR code?" e digite a chave manualmente;
   - digite no Billing o código de 6 dígitos do aplicativo e clique em **Ativar**.
5. O sistema mostra **10 códigos de recuperação**. Baixe ou copie e guarde em lugar seguro: cada um permite
   entrar uma vez se você perder o celular.
6. Marque "Guardei os códigos" e clique em **Concluir**. As abas **Usuários**, **Substituições** e
   **Parâmetros** aparecem.

Nos próximos logins, o sistema pede usuário, senha e o código do aplicativo.

Perfis disponíveis em `--roles` (separe por vírgula para dar mais de um):

| Perfil | Pode | Exige 2FA |
|---|---|---|
| `analyst` | Consultar dados, fazer lançamentos, gerar relatórios | não |
| `manager` | Aprovar lançamentos, gerar carga ERP, fechar período, ler a auditoria | **sim** |
| `admin` | Gerir usuários, perfis, substituições, contratos e parâmetros | **sim** |
| `auditor` | Somente leitura, incluindo a trilha de auditoria (controladoria e auditoria externa) | não |

---

## 6. Login pelo Google: criar o projeto no Google Cloud

Para o botão **"Entrar com Google"** funcionar, o Billing precisa ser registrado no Google. O registro gera um
**ID do cliente** e uma **chave secreta**. Faça isso uma vez.

### 6.1 Criar o projeto

1. Acesse **https://console.cloud.google.com** com a sua conta Google.
2. No topo da página, ao lado do logo "Google Cloud", clique no **seletor de projetos** (mostra o nome do
   projeto atual, por exemplo "My First Project").
3. Na janela que abre, clique em **Novo projeto**, no canto superior direito. Atalho:
   **https://console.cloud.google.com/projectcreate**
4. Preencha:
   - **Nome do projeto:** `Billing`
   - **Local:** deixe "Sem organização"
5. Clique em **Criar** e aguarde a notificação no sino.
6. Abra de novo o seletor de projetos e **selecione `Billing`**. Confira se o topo da página agora mostra
   "Billing".

### 6.2 Configurar a tela de consentimento

1. Acesse **https://console.cloud.google.com/auth/overview**. Pelo menu, é **APIs e serviços → Tela de
   consentimento OAuth**; nas versões novas aparece como **Google Auth Platform**.
2. Clique em **Começar** (ou "Get started") e preencha:
   - **Informações do app:** nome `Billing` e o seu e-mail como e-mail de suporte → **Próxima**
   - **Público:** **Externo** → **Próxima**
   - **Dados de contato:** o seu e-mail → **Próxima**
   - Aceite a política de dados de usuário → **Continuar** → **Criar**
3. No menu à esquerda, abra **Público** (ou "Audience"). Em **Usuários de teste**, clique em
   **Adicionar usuários** e inclua os e-mails Gmail que vão entrar no Billing, começando pelo seu.

> Enquanto o app estiver em **modo de teste**, só os e-mails da lista de usuários de teste conseguem entrar
> (até 100). Para liberar outros, use **Publicar app** na mesma tela. O Billing só pede nome e e-mail, que
> não exigem verificação do Google.

### 6.3 Criar o cliente OAuth (ID e chave)

1. No menu à esquerda, abra **Clientes** (ou **Credenciais → Criar credenciais → ID do cliente OAuth**).
2. Clique em **Criar cliente** e preencha:
   - **Tipo de aplicativo:** **Aplicativo da Web**
   - **Nome:** `Billing local`
   - **URIs de redirecionamento autorizados** → **Adicionar URI**:
     ```
     http://localhost:8080/api/v1/auth/oidc/google/callback
     ```
     O endereço precisa ser **exatamente** esse, sem barra no final. Se você trocar a porta ou publicar o
     sistema em outro endereço, cadastre também o novo (veja a [seção 10](#10-uso-real-produção)).
   - Deixe "Origens JavaScript autorizadas" vazio.
3. Clique em **Criar**. Aparece uma janela com:
   - **ID do cliente**, terminado em `.apps.googleusercontent.com`
   - **Chave secreta do cliente**, que começa com `GOCSPX-`

   **Copie os dois agora.** A chave secreta só aparece completa nesse momento. Se perder, crie uma nova no
   mesmo cliente.

---

## 7. Criar o `.env` com o ID e a chave do Google

O `.env` fica **dentro da pasta `backend`**. Com os contêineres, ele só precisa da configuração dos
provedores de login. As chaves do sistema já foram geradas automaticamente (seção 4).

**1. Crie o arquivo.** Na pasta `Billing`, rode o bloco abaixo trocando `COLE-O-ID` e `COLE-A-CHAVE` pelos
valores copiados na seção 6.3. Mantenha as aspas e escreva tudo em **uma linha só**:

```bash
cat > backend/.env <<'EOF'
NBB_OIDC_PROVIDERS={"google":{"name":"Google","issuer":"https://accounts.google.com","client_id":"COLE-O-ID.apps.googleusercontent.com","client_secret":"COLE-A-CHAVE","allowed_domains":["gmail.com"]}}
EOF
chmod 600 backend/.env
```

Se preferir um editor, abra `backend/.env` (por exemplo, `nano backend/.env`), cole a linha `NBB_OIDC_PROVIDERS=...`
com os seus valores e salve.

O que cada campo faz:

| Campo | Valor | Para que serve |
|---|---|---|
| `client_id` | ID do cliente | Identifica o Billing no Google |
| `client_secret` | Chave secreta | Prova que é o Billing pedindo o login |
| `allowed_domains` | `["gmail.com"]` | Domínios de e-mail aceitos. Com Google Workspace da empresa, use o domínio dela, como `["empresa.com.br"]` |
| `auto_provision` | omitido (`false`) | Com `true`, qualquer pessoa do domínio entra automaticamente, sem perfil, e pode pedir acesso. **Não use `true` com `gmail.com`**, porque abriria o cadastro para qualquer conta Gmail |

**2. Aplique a configuração:**

```bash
docker compose up -d
```

**3. Confira:**

```bash
docker compose exec api printenv NBB_OIDC_PROVIDERS
curl -s http://localhost:8080/api/v1/auth/providers
```

- O primeiro comando deve mostrar a linha que você colou.
- O segundo deve responder `[{"id":"google","name":"Google",...}]`.

Recarregue **http://localhost:8080**. O botão **"Entrar com Google"** aparece.

> **Segurança:** o `.env` contém a chave secreta do Google. Ele já está no `.gitignore`. Não envie esse
> arquivo por e-mail, não o publique e não o coloque no git.

---

## 8. Primeiro login pelo Google

O Billing **não cria contas sozinho** para quem entra pelo Google, a não ser que você use `auto_provision`.
A pessoa precisa ser **pré-cadastrada pelo e-mail**, e o vínculo com a conta Google é feito no primeiro login.

**1. Cadastre a pessoa.** Escolha uma das duas formas:

- **Pela tela:** como admin, abra **Usuários → Novo usuário** e preencha nome, login, o **e-mail do Gmail** e
  a forma de entrada **"Google / Microsoft (SSO)"**. Marque os perfis e clique em **Cadastrar**.
- **Pelo terminal, só para o primeiro administrador** (funciona apenas se ainda não existir nenhum admin):
  ```bash
  docker compose exec api nbb bootstrap-admin lucas "Lucas A. Martins" seu-email@gmail.com
  ```

**2. A pessoa entra:**

1. Abre **http://localhost:8080** e clica em **"Entrar com Google"**.
2. Escolhe a conta Google. Em modo de teste, o Google mostra o aviso "O Google não verificou este app":
   clique em **Continuar**.
3. Volta ao Billing já logada. Se o perfil exigir 2FA (Gerente ou Admin), ela ativa o autenticador como na
   [seção 5](#5-primeiro-acesso-sem-google), passos 3 a 6.
4. Nos próximos logins: **Entrar com Google** → código do aplicativo.

Se o login for recusado, o Billing volta à tela de login com uma mensagem. As causas estão na
[seção 13](#13-solução-de-problemas).

---

## 9. Login pela Microsoft (opcional)

Para contas Microsoft 365 / Entra ID da empresa:

1. Acesse **https://entra.microsoft.com** → **Aplicativos → Registros de aplicativo → Novo registro**.
2. Preencha:
   - **Nome:** `Billing`
   - **Tipos de conta:** "Contas somente neste diretório organizacional"
   - **URI de redirecionamento:** plataforma **Web**, endereço
     `http://localhost:8080/api/v1/auth/oidc/microsoft/callback`
3. Clique em **Registrar**. Na tela **Visão geral**, copie a **ID do aplicativo (cliente)** e a **ID do
   diretório (locatário)**.
4. Em **Certificados e segredos → Novo segredo do cliente**, crie um segredo e copie o **Valor**. Ele só
   aparece uma vez.
5. No `backend/.env`, deixe a linha com os dois provedores, ainda em uma linha só:
   ```
   NBB_OIDC_PROVIDERS={"google":{"name":"Google","issuer":"https://accounts.google.com","client_id":"ID-GOOGLE","client_secret":"CHAVE-GOOGLE","allowed_domains":["gmail.com"]},"microsoft":{"name":"Microsoft","issuer":"https://login.microsoftonline.com/ID-DO-LOCATARIO/v2.0","client_id":"ID-DO-APLICATIVO","client_secret":"VALOR-DO-SEGREDO","allowed_domains":["empresa.com.br"],"require_email_verified":false}}
   ```
   O `require_email_verified: false` é necessário porque a Microsoft não informa se o e-mail foi verificado.
   Use essa opção **só** com o ID do locatário da empresa no `issuer`, nunca com `common`.
6. Rode `docker compose up -d`.

---

## 10. Uso real (produção)

Para colocar o sistema na rede da empresa:

1. **HTTPS.** O contêiner `web` atende em HTTP. Coloque-o atrás do proxy reverso ou do balanceador da empresa,
   com o certificado (ex.: `https://billing.empresa.com.br` → `http://servidor:8080`), e suba com:
   ```bash
   BILLING_URL=https://billing.empresa.com.br BILLING_COOKIE_SECURE=true docker compose up -d
   ```
2. **Google e Microsoft.** Cadastre a nova URL de retorno, por exemplo
   `https://billing.empresa.com.br/api/v1/auth/oidc/google/callback`. Fora de `localhost`, o Google só
   aceita HTTPS.
3. **Senhas do banco.** As senhas do Postgres no `docker-compose.yml` e em `infra/postgres-init.sql` são de
   desenvolvimento. Troque nos dois arquivos **antes da primeira subida**, porque o banco só é criado uma vez.
4. **Domínio permitido.** Em `allowed_domains`, use o domínio corporativo em vez de `gmail.com`.
5. **Publicar o app** no Google ([seção 6.2](#62-configurar-a-tela-de-consentimento)) ou manter a lista de
   usuários de teste atualizada.

### Checklist de produção

- [ ] Acesso por HTTPS, com `BILLING_URL` e `BILLING_COOKIE_SECURE=true`
- [ ] URLs de retorno de produção cadastradas no Google e/ou na Microsoft
- [ ] `backend/.env` com o domínio da empresa em `allowed_domains` e permissão `600`
- [ ] Senhas do Postgres trocadas
- [ ] Primeiro administrador criado e com o 2FA ativo
- [ ] Contas locais de teste removidas ou desligadas (tela **Usuários → Desligar**)
- [ ] Backup do banco **e** do volume `segredos` agendado ([seção 12](#backup))

---

## 11. Configurações opcionais

### Trocar a porta

```bash
BILLING_PORTA=9000 BILLING_URL=http://localhost:9000 docker compose up -d
```

Acesse **http://localhost:9000**. Cadastre também a URL de retorno correspondente no Google
(`http://localhost:9000/api/v1/auth/oidc/google/callback`).

### Sessão, tentativas de login e senhas

Acrescente no `backend/.env` e rode `docker compose up -d`:

| Variável | Padrão | O que controla |
|---|---|---|
| `NBB_ACCESS_TOKEN_TTL_SECONDS` | 900 | Validade do token de acesso; a interface renova sozinha |
| `NBB_REFRESH_IDLE_MINUTES` | 30 | Minutos sem uso até a sessão expirar |
| `NBB_REFRESH_ABSOLUTE_HOURS` | 10 | Duração máxima de uma sessão |
| `NBB_LOGIN_RATE_LIMIT` | 10 | Tentativas de login por minuto, por IP |
| `NBB_MFA_MAX_ATTEMPTS` | 5 | Códigos 2FA errados por usuário a cada 5 minutos |
| `NBB_PASSWORD_MIN_LENGTH` | 12 | Tamanho mínimo da senha das contas locais |
| `NBB_TOTP_ISSUER` | `Network Billing` | Nome que aparece no aplicativo autenticador |

### Parâmetros de negócio

O limite de dupla aprovação, o alerta de desvio, a duração máxima das substituições e a opção de exigir 2FA
de todos os usuários ficam na tela **Parâmetros**, para o administrador. Toda alteração fica na auditoria.

---

## 12. Operação do dia a dia

### Comandos úteis

| Tarefa | Comando |
|---|---|
| Ver o estado | `docker compose ps` |
| Ver os logs | `docker compose logs -f api` (ou `web`) |
| Parar | `docker compose stop` |
| Iniciar de novo | `docker compose start` |
| Criar conta de usuário e senha | `docker compose exec api nbb create-local-user LOGIN "Nome" EMAIL --roles analyst` |
| Criar o primeiro admin (SSO) | `docker compose exec api nbb bootstrap-admin LOGIN "Nome" EMAIL` |
| Encerrar todas as sessões | `docker compose exec api nbb revoke-all-sessions` |
| Recifrar os segredos do 2FA após trocar a chave | `docker compose exec api nbb reencrypt` |

Pela tela **Usuários**, o administrador cadastra, muda perfis, **desliga** e **reseta o 2FA** de quem perdeu
o celular. Desligar ou resetar encerra as sessões da pessoa na hora.

> **Limitação desta versão:** o envio de e-mail ainda não está configurado. Por isso o "Esqueci minha senha"
> e o link de criação de senha das contas locais cadastradas pela tela não chegam por e-mail. Para contas
> com usuário e senha, use o comando `nbb create-local-user`, que pede a senha no terminal.

### Atualizar para uma nova versão

Extraia a nova versão por cima da pasta atual, **preservando o `backend/.env`**, e rode:

```bash
docker compose up -d --build
```

As migrations do banco são aplicadas sozinhas na subida. Os dados ficam nos volumes e não se perdem.

### Backup

São **duas** coisas para guardar:
1. **O banco**, com usuários, auditoria e configurações.
2. **O volume `segredos`**, com as chaves.

> **Atenção:** sem a chave do volume `segredos`, os segredos do 2FA ficam ilegíveis e **todos os usuários
> precisam recadastrar o autenticador**.

```bash
# banco
docker compose exec -T postgres pg_dump -U nbb_owner nbb > billing-banco-$(date +%F).sql
# chaves
docker run --rm -v billing_segredos:/segredos -v "$(pwd)":/backup alpine \
  tar czf /backup/billing-segredos-$(date +%F).tgz -C /segredos .
```

Guarde o arquivo de chaves em local protegido, porque ele permite ler os segredos do 2FA.

Para restaurar:

```bash
docker compose stop api
docker compose exec -T postgres dropdb -U nbb_owner nbb
docker compose exec -T postgres createdb -U nbb_owner nbb
docker compose exec -T postgres psql -U nbb_owner -d nbb -v ON_ERROR_STOP=1 < billing-banco-AAAA-MM-DD.sql
docker run --rm -v billing_segredos:/segredos -v "$(pwd)":/backup alpine \
  sh -c "tar xzf /backup/billing-segredos-AAAA-MM-DD.tgz -C /segredos && chown -R 10001 /segredos"
docker compose start api
```

O banco é recriado vazio antes da restauração. Assim a trilha de auditoria volta idêntica: mesmos eventos,
horários e hashes, e a verificação de integridade continua passando.

O nome dos volumes vem do nome da pasta do projeto (`billing_pgdata`, `billing_segredos`). Confira com
`docker volume ls`.

---

## 13. Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `port is already allocated` ao subir | Outra aplicação usa a porta 8080 ou 5432 | Troque a porta do sistema ([seção 11](#trocar-a-porta)) ou pare o Postgres local (`sudo systemctl stop postgresql`) |
| `env_file ... must be a string` | Docker Compose antigo | Atualize para a v2.24 ou superior |
| Tela de login com "Nenhum provedor de login configurado" | `backend/.env` não existe, está em outra pasta ou a linha está quebrada | Seção 7. Confira com `docker compose exec api printenv NBB_OIDC_PROVIDERS` |
| Google mostra **Erro 400: redirect_uri_mismatch** | A URL de retorno cadastrada é diferente da usada | Cadastre exatamente `http://localhost:8080/api/v1/auth/oidc/google/callback` (seção 6.3) |
| Google mostra **Erro 403: access_denied** | O app está em modo de teste e o e-mail não está na lista | Adicione o e-mail em **Público → Usuários de teste** (seção 6.2) |
| Google mostra **Erro 401: invalid_client** | ID ou chave copiados errado | Confira os valores no `.env`, sem espaços extras, e rode `docker compose up -d` |
| "Seu e-mail não está cadastrado" | A pessoa não foi pré-cadastrada | Cadastre pela tela **Usuários** com o mesmo e-mail (seção 8) |
| "Contas desse domínio de e-mail não têm acesso" | O domínio não está em `allowed_domains` | Inclua o domínio no `.env` |
| "Já existe um usuário com este e-mail vinculado de outra forma" | Existe conta de usuário e senha com o mesmo e-mail | Use outro e-mail na conta local (ex.: `+local`) |
| "Código inválido" no segundo fator | Relógio do celular fora de hora, ou código já usado | Ative a data/hora automática no celular e espere o próximo código |
| "Muitos códigos errados. Aguarde alguns minutos" | 5 códigos errados em 5 minutos | Aguarde 5 minutos |
| "Muitas tentativas de login. Aguarde um minuto" | 10 tentativas por minuto atingidas | Aguarde 1 minuto |
| A pessoa perdeu o celular | — | Ela entra com um **código de recuperação**, ou o admin usa **Usuários → Resetar 2FA** |
| Gerente ou Admin entra mas não vê as abas | O 2FA ainda não foi ativado | Aba **Segurança da conta** → Ativar |
| `web` não sobe e aparece *dependency failed* | A API não ficou saudável | Veja `docker compose logs api` |
| Log da API: "NBB_DATA_ENCRYPTION_KEYS: a chave nº 1 não é uma chave válida" | Chave preenchida errado no `.env` | Apague essa linha do `.env`; a chave do volume é usada |

Se o problema continuar, os logs ajudam a encontrar a causa:

```bash
docker compose logs --tail 100 api
docker compose logs --tail 100 web
```

---

## 14. Desinstalar

Para parar e remover os contêineres, **mantendo os dados**:

```bash
docker compose down
```

Para remover os contêineres **e apagar todos os dados** (banco e chaves). Essa ação é irreversível, então
faça backup antes:

```bash
docker compose down -v
```

Para remover também as imagens construídas:

```bash
docker image rm billing-api billing-web
```

Se você criou o projeto no Google Cloud só para testar, ele pode ser excluído em **IAM e administrador →
Configurações → Encerrar**.

---

## 15. Desenvolvimento sem containers

Para mexer no código com recarga automática (a API e a interface reiniciam a cada alteração salva), use os scripts. Eles precisam de Python 3.12+ e Node.js 18+, e o Postgres e o Redis continuam no Docker.

Na pasta raiz do projeto (a que tem o `docker-compose.yml`):

```bash
./dev-setup.sh lucas "Lucas A. Martins" seu-email@gmail.com
```

O script pode ser rodado de novo sem estragar nada. Ele faz o seguinte:
1. Sobe o Postgres e o Redis.
2. Instala as dependências.
3. Cria o `backend/.env` só se ele ainda não existir.
4. Gera as chaves que ainda estiverem com o texto de exemplo.
5. Roda as migrations e cria o admin (se o admin já existir, segue adiante).
6. Sobe o servidor em segundo plano.

Ao final, o sistema fica em **http://localhost:5173** e a documentação da API em http://localhost:8000/api/v1/docs.

Para parar: `./dev-stop.sh`. Os logs ficam em `backend/uvicorn.log` e `frontend/vite.log`.

Para entrar sem configurar o Google nesse modo, crie uma conta local direto no computador:

```bash
cd backend
nbb create-local-user admin.local "Seu Nome" seu-email+local@gmail.com --roles admin
```

**Usando os dois modos no mesmo computador:** eles compartilham o banco. Por isso precisam das mesmas chaves;
senão, o 2FA cadastrado num modo não funciona no outro. O `dev-setup.sh` cuida disso: se faltar alguma chave no
`backend/.env`, ele copia a que os contêineres já geraram no volume `segredos` e só cria uma nova se não houver
contêiner. Daí em diante as chaves ficam no `.env`, e os contêineres passam a usar as mesmas, porque as do `.env`
têm prioridade.

A URL de retorno do Google no modo de desenvolvimento é `http://localhost:8000/api/v1/auth/oidc/google/callback`.
Cadastre as duas URLs no Google (a da porta 8080 e esta) se for usar os dois modos.

### Atualizando uma instalação de desenvolvimento antiga (módulo 1 sem SSO/2FA)

```bash
cd backend
pip install -e ".[dev]"                  # dependências novas: pyotp, segno, cryptography
nbb generate-data-key                    # cole em NBB_DATA_ENCRYPTION_KEYS
alembic upgrade head                     # aplica 0002: usuários 'corporate' passam a 'sso'
```

No `.env`, troque as variáveis antigas `NBB_OIDC_ISSUER`, `NBB_OIDC_CLIENT_ID`, `NBB_OIDC_CLIENT_SECRET`, `NBB_OIDC_REDIRECT_URI` e `NBB_OIDC_LOGIN_CLAIM` por `NBB_OIDC_PROVIDERS` e `NBB_PUBLIC_BASE_URL`. As variáveis antigas são ignoradas. Os usuários existentes precisam ter o e-mail preenchido para o primeiro login por SSO, e gerentes e admins precisam cadastrar o autenticador para recuperar as permissões.

---

## 16. Testes automatizados

```bash
cd backend
pip install -e ".[dev]"
pytest
```

Os testes usam Postgres e Redis reais (banco `nbb_test`, Redis db 15). O schema do banco de testes é recriado a cada execução. O cliente OIDC é testado contra um provedor OIDC local (chave RSA, JWKS e discovery reais), sem acessar Google nem Microsoft.

---

## 17. Frontend

Fica em `frontend/` (React + TypeScript + Vite) e usa o mesmo visual da versão anterior do Billing: barra superior azul com abas e login em cartão sobre fundo azul.

| Tela | Quem vê |
|---|---|
| Login | todos: botões dos provedores configurados, usuário e senha para contas externas, segunda etapa com o código ou com código de recuperação, "esqueci minha senha" |
| Início | todos: perfis e permissões, aviso de 2FA pendente, pedido de acesso, substituições recebidas |
| Segurança da conta | todos: ativar o 2FA com QR code, códigos de recuperação, desativar (quando o perfil permite) |
| Usuários | `users.manage`: cadastrar, perfis, desligar, resetar 2FA, pedidos de acesso |
| Substituições | `delegations.manage` |
| Auditoria | `audit.read`: filtros, detalhes antes/depois, verificação de integridade, exportação CSV |
| Parâmetros | `settings.manage` |

Nos contêineres, o Nginx do `web` serve a interface compilada e repassa `/api` para a API. Em desenvolvimento, o Vite (porta 5173) repassa `/api` para a API (porta 8000). O navegador fala com uma origem só, então os cookies `HttpOnly`, o CSRF e o `SameSite=Strict` funcionam como em produção, sem CORS. O token de acesso de 15 minutos é renovado sozinho quando expira.

```bash
cd frontend
npm install
npx vite            # http://localhost:5173
npm run build       # gera frontend/dist (é o que o contêiner web serve pelo Nginx)
```

---

## 18. Login: SSO e verificação em duas etapas

```
 ┌───────────── Etapa 1: quem é você ─────────────┐   ┌──── Etapa 2: o código ────┐
 │ "Entrar com Google"    ─┐                      │   │                           │
 │ "Entrar com Microsoft" ─┼─► provedor ─► callback├──►│ autenticador ativo?       │
 │ "Login corporativo"    ─┘                      │   │  sim → /login/verificacao │
 │ usuário e senha (contas locais) ───────────────┘   │        código de 6 dígitos│
 └────────────────────────────────────────────────┘   │  não → sessão sem 2FA     │
                                                      └───────────────────────────┘
```

### Configurando os provedores (`NBB_OIDC_PROVIDERS`)

O passo a passo do Google está nas [seções 6 e 7](#6-login-pelo-google-criar-o-projeto-no-google-cloud). Aqui está a referência completa.

É um JSON `{id: config}`. Cada provedor vira um botão na tela de login (`GET /api/v1/auth/providers`). A URL de retorno a cadastrar no console de cada provedor é:

`{NBB_PUBLIC_BASE_URL}/api/v1/auth/oidc/{id}/callback`

```json
{
  "google": {
    "name": "Google",
    "issuer": "https://accounts.google.com",
    "client_id": "....apps.googleusercontent.com",
    "client_secret": "...",
    "allowed_domains": ["empresa.com.br"],
    "auto_provision": true
  },
  "microsoft": {
    "name": "Microsoft",
    "issuer": "https://login.microsoftonline.com/<tenant-id-da-empresa>/v2.0",
    "client_id": "...",
    "client_secret": "...",
    "allowed_domains": ["empresa.com.br"],
    "require_email_verified": false
  },
  "corporativo": {
    "name": "Login corporativo",
    "issuer": "https://sso.empresa.com.br/realms/empresa",
    "client_id": "network-billing",
    "client_secret": "...",
    "trust_idp_mfa": true
  }
}
```

| Opção | Padrão | Para que serve |
|---|---|---|
| `allowed_domains` | `[]` | Domínios de e-mail aceitos. Vazio = qualquer domínio, mas só entra quem o admin pré-cadastrou. |
| `auto_provision` | `false` | Cria automaticamente, **sem perfil**, quem vier de um domínio permitido. A pessoa só consegue pedir acesso. |
| `link_by_email` | `true` | No primeiro login, vincula a conta do provedor ao usuário pré-cadastrado com o mesmo e-mail. |
| `require_email_verified` | `true` | Exige `email_verified=true`. A Microsoft não envia esse claim: desligue **só** com o issuer de um tenant único da empresa (nunca com `common`), porque aí o e-mail é controlado pela empresa. |
| `trust_idp_mfa` | `false` | Aceita o MFA feito no provedor (claim `amr`) no lugar do código TOTP. Use apenas em provedor da própria empresa com MFA obrigatório. |

**Como o sistema decide quem entra:**
1. Conta do provedor já vinculada (par provedor + `sub`): entra como o usuário vinculado. Daí em diante vale o `sub`, mesmo que a pessoa troque o e-mail na conta do Google ou da Microsoft.
2. E-mail **verificado** igual ao de um usuário SSO pré-cadastrado: vincula e entra.
3. Domínio permitido com `auto_provision`: cria o usuário sem perfil.
4. Qualquer outro caso: recusado e registrado na auditoria (`auth.login_failed`).

**Proteções:**
- Não há vínculo por e-mail não verificado.
- Uma segunda conta do mesmo provedor não assume um usuário que já tem vínculo.
- O SSO nunca entra numa conta local com o mesmo e-mail.

Uma mesma pessoa pode ter Google e Microsoft vinculados.

Erros do callback voltam ao frontend como `/login?erro=<código>`. Os códigos são: `domain_not_allowed`, `not_registered`, `email_not_verified`, `identity_conflict`, `user_blocked`, `provider_error`, `cancelled`, `expired`, `invalid_state` e `rate_limited`.

### Verificação em duas etapas (TOTP)

Funciona com Google Authenticator, Microsoft Authenticator, Authy, 1Password e qualquer app TOTP padrão (RFC 6238: 6 dígitos, 30 segundos).

| Endpoint | Para quê |
|---|---|
| `GET /auth/mfa` | Situação: ativo, obrigatório, códigos de recuperação restantes |
| `POST /auth/mfa/totp/setup` | Gera o QR code (`qr_svg`, pronto para `<img src>`) e o segredo para digitação manual |
| `POST /auth/mfa/totp/confirm` | Confirma com o primeiro código, ativa o 2FA e devolve **10 códigos de recuperação** (mostrados uma única vez) |
| `POST /auth/mfa/verify` | Segunda etapa do login: código de 6 dígitos ou código de recuperação |
| `POST /auth/mfa/recovery-codes` | Gera novos códigos de recuperação (exige código do app) |
| `POST /auth/mfa/disable` | Desativa o 2FA. Recusado se o perfil exige |
| `POST /users/{id}/mfa/reset` | Admin remove o autenticador de quem perdeu o celular. Encerra as sessões da pessoa |

**Quem é obrigado a ter 2FA:**
- Perfis com `requires_mfa`: Gerente e Admin.
- Com `mfa.required_for_all = true`, todos os usuários.

Sem o código, a pessoa entra, mas as permissões desses perfis ficam bloqueadas. O `/me` traz `mfa_enrollment_required: true` para o frontend levar à tela de cadastro. Logo depois de confirmar o cadastro, as permissões passam a valer, sem novo login.

**Detalhes de segurança:**
- Antes do código não existe sessão. A etapa 1 gera só um ticket de 5 minutos, de uso único, em cookie `HttpOnly` restrito ao caminho `/api/v1/auth/mfa`.
- Limites de tentativas:
  - Cada ticket aceita 5 códigos errados.
  - Cada usuário pode errar 5 códigos a cada 5 minutos, somando todas as tentativas de login (resposta `mfa_locked`).
  - Os endpoints de login continuam com o limite de 10 por minuto por IP.
- Um código aceito não vale de novo (anti-replay pelo passo de tempo). A tolerância de relógio é de ±30 s.
- O segredo TOTP fica cifrado no banco (Fernet, com `NBB_DATA_ENCRYPTION_KEYS`) e aparece como `[redacted]` na auditoria.
- Os códigos de recuperação são guardados só como hash e valem uma vez cada.
- Ativar o 2FA troca a sessão atual por uma nova e encerra as demais.
- Desativar o 2FA ou resetá-lo pelo admin encerra as outras sessões.
- Trocar a senha de uma conta local **não** desliga o 2FA.
- Contas locais (ex.: auditoria externa) também usam TOTP e, com ele, podem receber perfis que exigem 2FA.

**Risco conhecido:** quem tem perfil obrigatório e ainda não cadastrou o autenticador faz o cadastro com a sessão só do primeiro fator. Quem roubar a conta Google/Microsoft da pessoa *antes* do primeiro cadastro conseguiria cadastrar o próprio celular. Mitigações:
- Pedir que gerentes e admins cadastrem o 2FA logo que recebem o perfil.
- Usar `trust_idp_mfa` no provedor corporativo.
- Acompanhar o evento `mfa.enrolled` na auditoria.

### Rotação da chave de criptografia dos segredos TOTP
`NBB_DATA_ENCRYPTION_KEYS` é uma lista. A primeira chave cifra e todas decifram. Para rotacionar:
1. Coloque a chave nova na frente da lista.
2. Os segredos antigos continuam legíveis.
3. Rode `nbb reencrypt` e depois remova a chave antiga.

---

## 19. Decisões de segurança

### Dois usuários de banco
- `nbb_owner` roda as migrations e é dono das tabelas.
- `nbb_app` é o usuário da aplicação. Não tem UPDATE, DELETE nem TRUNCATE na trilha de auditoria (e, nos próximos módulos, nas tabelas imutáveis de lançamentos aprovados, fechamento e cargas ERP).

### Trilha de auditoria
- Toda inserção, alteração e exclusão de modelos marcados com `__audited__` gera um evento automaticamente, na mesma transação, com o usuário, o IP, o id da requisição e os valores anterior e novo. Hashes de senha aparecem como `[redacted]`.
- Login, logout, falhas de login, desligamentos e as próprias consultas à auditoria também são registrados.
- Cada evento guarda o SHA-256 do anterior (cadeia de hashes, calculada por trigger no banco). `GET /api/v1/audit-events/verify` aponta a primeira linha adulterada ou removida.
- UPDATE, DELETE e TRUNCATE são barrados por trigger até para o dono do schema. Um DBA que desligue o trigger consegue alterar a tabela, mas a cadeia denuncia a alteração.
- Retenção: o sistema não apaga nada. O expurgo após 10 anos é um procedimento de DBA, feito fora da aplicação e registrado.
- Recomendação para produção: exportar periodicamente para armazenamento com bloqueio de objeto (WORM), como S3 Object Lock.

### Login e sessão
- **SSO e 2FA:** ver a [seção 18](#18-login-sso-e-verificação-em-duas-etapas).
- **Contas locais** (ex.: auditoria externa): senha guardada só como hash Argon2id. Esquecida a senha, o usuário recebe por e-mail um link de uso único, válido por 30 minutos, para criar outra. O envio de e-mail ainda não está configurado nesta versão (ver [seção 12](#12-operação-do-dia-a-dia)).
- **JWT:** validade de 15 minutos, no cookie `nbb_at` (`HttpOnly`, `Secure`, `SameSite=Strict`), inacessível a scripts.
- **Refresh token:** opaco e guardado só como hash. Gira a cada uso. Reutilizar um refresh antigo derruba a sessão (indício de roubo).
- **CSRF:** double-submit. O frontend envia o cookie `nbb_csrf` no cabeçalho `X-CSRF-Token` em toda requisição que altera dados.
- **Rate limit:** 10 tentativas de login por minuto por IP, em janela deslizante no Redis. A 11ª recebe 429. Se o Redis cair, o limite continua valendo por instância, em memória. Nos contêineres, o Nginx repassa o IP real no `X-Forwarded-For`. Rodando a API atrás de outro proxy, configure `NBB_TRUSTED_PROXIES`.
- **Desligamento** (`POST /users/{id}/terminate`): bloqueia o usuário, invalida todos os tokens (`token_version`), encerra todas as sessões e revoga as substituições ligadas a ele. Vale na próxima requisição, não no próximo login. Novo login por SSO também é recusado.

### Rotação da chave do JWT
Nos contêineres, a chave gerada sozinha fica em `/segredos/jwt_key`. Para controlá-la, defina `NBB_JWT_KEYS` e `NBB_JWT_ACTIVE_KID` no `backend/.env`; as do `.env` têm prioridade.

`NBB_JWT_KEYS` é um mapa `{kid: segredo}`. A chave `NBB_JWT_ACTIVE_KID` assina os tokens, e qualquer chave do mapa os valida.

- **Rotação periódica:**
  1. Gere uma chave nova com `nbb generate-key`.
  2. Adicione-a ao mapa e torne-a ativa.
  3. Depois de 15 minutos, remova a chave antiga.
- **Suspeita de vazamento:**
  1. Remova a chave comprometida do mapa e reinicie as instâncias. Todos os tokens assinados com ela caem na hora.
  2. Rode `nbb revoke-all-sessions` para encerrar também os refresh tokens.

### Perfis e substituições
- Os perfis são pacotes de permissões guardados no banco (`role`, `role_permission`). As permissões são recalculadas a cada requisição.
- Segregação de funções:
  - Ninguém altera os próprios perfis nem decide o próprio pedido de acesso.
  - Admin não aprova lançamentos nem lê a auditoria.
- **Substituição em férias:**
  - O admin concede a um substituto um perfil que o titular tem, com início e fim obrigatórios (máximo configurável, 60 dias por padrão) e justificativa.
  - As ações do substituto ficam no nome dele, com `via_delegation_id` apontando a substituição usada.
  - A permissão some ao fim do prazo, na revogação ou se o titular for desligado.

---

## 20. Parâmetros configuráveis

Alterados pela tela **Parâmetros** ou por `PUT /api/v1/settings/{chave}`. Toda alteração vai para a auditoria.

| Chave | Padrão | Uso |
|---|---|---|
| `approval.double_threshold` | 50000.00 | Valor acima do qual um lançamento exige duas aprovações |
| `approval.deviation_pct` | 30 | Desvio (%) em relação à média que dispara alerta ao aprovador |
| `approval.deviation_window_months` | 6 | Meses usados na média do cliente |
| `delegation.max_days` | 60 | Duração máxima de uma substituição |
| `privacy.store_cpf` | false | Guardar CPF dos responsáveis |
| `mfa.required_for_all` | false | Exige 2FA de todos os usuários (por padrão, só Gerente e Admin) |

---

## 21. Pontos em aberto

| Ponto | Como ficou configurável |
|---|---|
| O perfil Analyst cobre lançamentos ou é preciso um perfil "Lançador"? | Hoje `entries.write` está no Analyst. Para separar, crie o perfil `lancador` e mova a permissão em `role_permission`, sem mudar código. |
| O CPF dos responsáveis é necessário? | Desligado por padrão (`privacy.store_cpf = false`). O campo será criado criptografado no módulo 2, aguardando o jurídico. |
| Qual o limiar do alerta de valor fora da média? | Padrão provisório: 30% sobre a média dos últimos 6 meses (`approval.deviation_*`). |
| Semântica de "Faixas" | Padrão a implementar no módulo 2: o preço da faixa vale para todos os atendimentos. Progressivo fica como opção do contrato. |
| Base do "Percentual" | Valor-base informado no lançamento. |
| Arredondamento | HALF_UP em centavos. |
| Layout da planilha do ERP | Aguardando o modelo do ERP. |
| Coordenador como segundo aprovador | Coordenadores e gerentes compartilham o perfil `manager`. |
