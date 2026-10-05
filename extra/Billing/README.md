# Instalação do Billing

Guia passo a passo para instalar e colocar o Billing no ar com Docker.

Para entender como o sistema funciona por dentro (perfis, auditoria e endpoints), veja o
[README.md](README.md).

---

## Sumário

1. [Pré-requisitos](#1-pré-requisitos)
2. [Obter o projeto](#2-obter-o-projeto)
3. [Escolher o modo de instalação](#3-escolher-o-modo-de-instalação)
4. [Instalação de demonstração (5 minutos)](#4-instalação-de-demonstração-5-minutos)
5. [Primeiro acesso](#5-primeiro-acesso)
6. [Instalação para uso real (produção)](#6-instalação-para-uso-real-produção)
7. [Outras formas de executar](#7-outras-formas-de-executar)
8. [Configurações opcionais](#8-configurações-opcionais)
9. [Operação do dia a dia](#9-operação-do-dia-a-dia)
10. [Solução de problemas](#10-solução-de-problemas)
11. [Desinstalar](#11-desinstalar)

---

## 1. Pré-requisitos

| Item | Versão mínima | Observação |
|---|---|---|
| Docker | Engine 24+ ou Docker Desktop 4.27+ | No Windows e no macOS, use o Docker Desktop |
| Docker Compose | v2.24+ | Já vem com o Docker Desktop. Confira com `docker compose version` |
| Portas livres | 443 e 80 | Podem ser trocadas (veja a [seção 8](#8-configurações-opcionais)) |
| Espaço em disco | ~2 GB | Para as imagens e a compilação |
| Internet | — | Só durante a instalação, para baixar as imagens e as dependências |

Para uso real, você também vai precisar de:
- o endereço do **LDAP/Active Directory** da empresa (ex.: `ldaps://ldap.empresa.local:636`) e o nome do
  domínio (ex.: `EMPRESA`);
- de preferência, um **certificado HTTPS** emitido pela empresa (`.crt` e `.key`);
- as **faixas de IP da VPN**, se o acesso tiver de ficar restrito a ela.

Para conferir se o Docker está pronto, rode:

```bash
docker --version
docker compose version
```

---

## 2. Obter o projeto

Clone o diretório no github e entre na pasta billing:

```bash
git clone 
cd billing
```

**Todos os comandos deste guia devem ser executados dentro da pasta `billing`.**

A estrutura relevante para a instalação é esta:

```
billing/
├── docker-compose.yml            # sobe API + interface em contêineres separados (recomendado)
├── docker-compose.postgres.yml   # complemento opcional: PostgreSQL e Redis
├── Dockerfile                    # alternativa: tudo em um contêiner único
├── .env.example                  # modelo de configuração
├── backend/Dockerfile            # imagem da API
├── frontend/Dockerfile           # imagem da interface + Nginx (HTTPS)
└── infra/                        # scripts de inicialização e configuração do Nginx
```

---

## 3. Escolher o modo de instalação

| Modo | Quando usar | Contêineres |
|---|---|---|
| **A. Dois contêineres** (recomendado) | Uso normal: até ~1.000 usuários, uma instância | `billing-api` + `billing-web` |
| **B. Contêiner único** | Instalação mais simples possível, servidor pequeno | `billing` |
| **C. Dois contêineres + PostgreSQL/Redis** | Várias instâncias da API ou política que exige PostgreSQL | 4 contêineres |

As seções 4 a 6 usam o **modo A**. Os modos B e C estão na [seção 7](#7-outras-formas-de-executar).

```
            Navegador
                │ HTTPS (443)
                ▼
     ┌──────────────────────┐        ┌──────────────────────┐
     │     billing-web      │ /api → │     billing-api      │
     │  interface + Nginx   │───────►│  API + banco SQLite  │
     │  (único com portas)  │        │  (sem portas expostas)│
     └──────────────────────┘        └──────────┬───────────┘
                                                │
                                         LDAP da empresa
```

---

## 4. Instalação de demonstração (5 minutos)

A demonstração usa um **login simulado**: não precisa de LDAP e cria quatro usuários de teste. Serve para
conhecer o sistema. **Não use em produção.**

**Linux / macOS / Git Bash:**

```bash
BILLING_DEMO=1 docker compose up -d --build
```

**Windows (PowerShell):**

```powershell
$env:BILLING_DEMO=1; docker compose up -d --build
```

A primeira execução leva alguns minutos, porque compila a interface e instala as dependências. Ao final,
confira se os dois contêineres estão `healthy`:

```bash
docker compose ps
```

```
NAME          STATUS
billing-api   Up 1 minute (healthy)
billing-web   Up 1 minute (healthy)
```

Agora abra **https://localhost** no navegador.

| Usuário | Senha | Perfil |
|---|---|---|
| `admin` | `demo123` | Administrador (cadastros e usuários) |
| `operacional` | `demo123` | Operacional (lançamentos e planilha ERP) |
| `gestor` | `demo123` | Gestor (aprovações) |
| `auditor` | `demo123` | Auditor (trilha de auditoria) |

---

## 5. Primeiro acesso

1. **Aviso de certificado.** Na primeira vez, o navegador avisa que a conexão "não é particular". Isso é
   esperado, porque o sistema gerou um certificado autoassinado. Clique em **Avançado → Continuar para
   localhost**. Em produção, use o certificado da empresa (veja a [seção 8](#8-configurações-opcionais)).
2. **Usuário e senha.** Informe o usuário e a senha (na demonstração, `demo123`).
3. **Segundo fator.** No primeiro login de cada usuário, aparece um **QR code**:
   - instale no celular um aplicativo autenticador (Google Authenticator, Microsoft Authenticator,
     Authy ou similar);
   - escaneie o QR code. Se não conseguir, clique em "Não consegue escanear?" e digite a chave
     manualmente no aplicativo;
   - digite o código de 6 dígitos que aparece no aplicativo.
4. Nos próximos logins, o sistema pede apenas o código do aplicativo.

**Roteiro sugerido para conhecer o sistema:**

| Passo | Usuário | O que fazer |
|---|---|---|
| 1 | `admin` | Em **Cadastros**, crie uma Empresa, depois um Cliente, um Contrato e uma Regra de serviço com valor unitário |
| 2 | `operacional` | Em **Lançamentos**, crie um lançamento para o cliente e clique em **Submeter** |
| 3 | `gestor` | Em **Aprovações**, aprove ou reprove (reprovar exige motivo) |
| 4 | `operacional` | Em **Planilha ERP**, gere e baixe o CSV do período |
| 5 | `auditor` | Em **Auditoria**, veja tudo o que foi feito, com usuário, IP e horário |

---

## 6. Instalação para uso real (produção)

> **Importante:** se você rodou a demonstração, apague os dados dela antes, para que os usuários de teste
> não passem para a produção:
>
> ```bash
> docker compose down -v
> ```

### 6.1 Criar o arquivo de configuração

```bash
cp .env.example .env
```

Abra o `.env` e preencha **pelo menos** o LDAP da empresa:

```ini
BILLING_AMBIENTE=producao
BILLING_IDP_TIPO=ldap
BILLING_LDAP_URL=ldaps://ldap.empresa.local:636
BILLING_LDAP_DOMINIO=EMPRESA
```

As chaves de segurança (`BILLING_JWT_CHAVE_ATUAL`, `BILLING_MFA_CHAVE_CIFRAGEM` e `BILLING_OPS_TOKEN`)
podem ficar vazias. Nesse caso, são geradas automaticamente na primeira execução e guardadas no volume
da API. Se preferir defini-las, cada uma precisa ter **32 caracteres ou mais**. Para gerar uma:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(48))"
```

### 6.2 Subir o sistema

```bash
docker compose up -d --build
docker compose ps        # aguarde os dois contêineres ficarem "healthy"
```

### 6.3 Criar o primeiro administrador

O login deve ser o **mesmo do login corporativo**. A senha não é cadastrada no Billing: ela é conferida no
LDAP.

```bash
docker compose exec billing-api python3 -m app.cli criar-usuario joao.silva "João Silva" ADMINISTRADOR
```

Os perfis disponíveis são `ADMINISTRADOR`, `OPERACIONAL`, `GESTOR`, `AUDITOR` e `OPERACAO`.

Depois disso, o administrador entra pelo navegador, cadastra o segundo fator e pode criar os demais
usuários pela tela **Usuários**.

### 6.4 Conferir a conexão com o LDAP

A verificação de saúde do provedor de identidade usa o token de operação. Se você não definiu o token no
`.env`, consulte o que foi gerado:

```bash
TOKEN=$(docker compose exec -T billing-api sh -c '. /dados/segredos.env; echo $GERADO_OPS')
curl -k -H "X-Ops-Token: $TOKEN" https://localhost/api/saude/provedor-identidade
```

| Resposta | Significado |
|---|---|
| `{"saudavel": true, ...}` (HTTP 200) | O LDAP está acessível |
| `{"saudavel": false, ...}` (HTTP 503) | Não foi possível conectar. Revise `BILLING_LDAP_URL`, o DNS e o firewall |

### 6.5 Checklist de produção

- [ ] `.env` com o LDAP da empresa e `BILLING_AMBIENTE=producao`
- [ ] Certificado da empresa instalado ([seção 8](#certificado-https-da-empresa))
- [ ] Acesso restrito às faixas da VPN ([seção 8](#restringir-o-acesso-à-vpn))
- [ ] Primeiro administrador criado e com o segundo fator configurado
- [ ] Conexão com o LDAP verificada (item 6.4)
- [ ] Backup do volume da API agendado ([seção 9](#backup))

---

## 7. Outras formas de executar

### Modo A sem Compose (com `docker run`)

```bash
docker build -f backend/Dockerfile  -t billing-api .
docker build -f frontend/Dockerfile -t billing-web .

docker network create billing-rede

# API: sem -p, fica acessível só na rede interna
docker run -d --name billing-api --network billing-rede --restart unless-stopped \
  -v billing-api-dados:/dados --env-file .env billing-api

# Interface: suba depois da API
docker run -d --name billing-web --network billing-rede --restart unless-stopped \
  -p 443:443 -p 80:80 -v billing-web-certs:/certs \
  -e BILLING_API_URL=http://billing-api:8000 billing-web
```

Para demonstração, troque `--env-file .env` por `-e BILLING_DEMO=1`. No PowerShell, troque a quebra de
linha `\` por crase (`` ` ``) ou escreva cada comando em uma linha só.

### Modo B: contêiner único

```bash
docker build -t billing .

# demonstração
docker run -d --name billing --restart unless-stopped \
  -p 443:443 -p 80:80 -v billing-dados:/dados -e BILLING_DEMO=1 billing

# produção
docker run -d --name billing --restart unless-stopped \
  -p 443:443 -p 80:80 -v billing-dados:/dados --env-file .env billing
docker exec billing python3 -m app.cli criar-usuario joao.silva "João Silva" ADMINISTRADOR
```

Nesse modo, o certificado fica em `/dados/certs` (no mesmo volume dos dados).

### Modo C: com PostgreSQL e Redis

Defina `POSTGRES_PASSWORD` no `.env` e rode:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
```

Nos comandos seguintes (`ps`, `logs`, `down`), repita os dois `-f`. Esse complemento ainda não foi testado
em ambiente real: valide em homologação antes de usar.

---

## 8. Configurações opcionais

### Trocar as portas

Se as portas 443 ou 80 já estiverem em uso:

```bash
BILLING_PORTA_HTTPS=8443 BILLING_PORTA_HTTP=8080 docker compose up -d
```

Acesse **https://localhost:8443**. O redirecionamento de HTTP para HTTPS acompanha a porta escolhida.

### Certificado HTTPS da empresa

Copie os arquivos para o volume de certificados com os nomes `billing.crt` e `billing.key` e reinicie a
interface:

```bash
docker cp empresa.crt billing-web:/certs/billing.crt
docker cp empresa.key billing-web:/certs/billing.key
docker compose restart billing-web
```

### Restringir o acesso à VPN

Por padrão, só são aceitas conexões das faixas privadas (`10.0.0.0/8`, `172.16.0.0/12` e
`192.168.0.0/16`). Para usar as faixas exatas da VPN:

1. Edite `infra/nginx/rede-permitida.conf`, por exemplo:
   ```nginx
   allow 10.20.0.0/16;   # VPN da empresa
   deny all;
   ```
2. No `docker-compose.yml`, descomente a linha que monta esse arquivo no serviço `billing-web`.
3. Rode `docker compose up -d`.

### Tempo de sessão, limite de tentativas e retenção de logs

Ajuste no `.env` e rode `docker compose up -d`:

| Variável | Padrão | O que controla |
|---|---|---|
| `BILLING_ACCESS_TOKEN_MINUTOS` | 15 | Validade do token de acesso (renovado automaticamente pela interface) |
| `BILLING_SESSAO_MAXIMA_HORAS` | 8 | Tempo máximo de uma sessão antes de exigir novo login |
| `BILLING_LIMITE_LOGIN_POR_MINUTO` | 10 | Tentativas de login por minuto, por IP |
| `BILLING_RETENCAO_LOGS_ANOS` | 5 | Prazo usado pelo comando de limpeza de logs |

---

## 9. Operação do dia a dia

### Comandos úteis

| Tarefa | Comando |
|---|---|
| Ver o estado | `docker compose ps` |
| Ver os logs | `docker compose logs -f billing-api` (ou `billing-web`) |
| Parar | `docker compose stop` |
| Iniciar de novo | `docker compose start` |
| Criar usuário | `docker compose exec billing-api python3 -m app.cli criar-usuario LOGIN "Nome" PERFIL` |
| Encerrar as sessões de um usuário | `docker compose exec billing-api python3 -m app.cli revogar-sessoes LOGIN` |
| Encerrar todas as sessões | `docker compose exec billing-api python3 -m app.cli revogar-todas-sessoes` |
| Limpar logs além do prazo | `docker compose exec billing-api python3 -m app.cli limpar-logs` |

Desativar um usuário ou mudar o perfil dele também pode ser feito pela tela **Usuários**. As duas ações
encerram as sessões abertas na hora.

### Atualizar para uma nova versão

Extraia a nova versão por cima da pasta atual, preservando o seu `.env`, e rode:

```bash
docker compose up -d --build
```

Os dados ficam nos volumes e não são perdidos na atualização.

### Backup

Todos os dados da API ficam no volume `billing_api-dados`:
- o banco `billing.db`;
- o arquivo `segredos.env`, com as chaves.

> **Atenção:** sem o `segredos.env`, todos os usuários precisam recadastrar o segundo fator.

Para gerar um backup consistente, pare a API por alguns segundos:

```bash
docker compose stop billing-api
docker run --rm -v billing_api-dados:/dados -v "$(pwd)":/backup ubuntu:24.04 \
  tar czf /backup/billing-backup-$(date +%F).tgz -C /dados .
docker compose start billing-api
```

Para restaurar a partir de um backup:

```bash
docker compose stop billing-api
docker run --rm -v billing_api-dados:/dados -v "$(pwd)":/backup ubuntu:24.04 \
  sh -c "rm -rf /dados/* && tar xzf /backup/billing-backup-AAAA-MM-DD.tgz -C /dados && chown -R 1001:1001 /dados"
docker compose start billing-api
```

O nome do volume vem do nome da pasta do projeto. Confira o nome exato com `docker volume ls`.

---

## 10. Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `port is already allocated` ao subir | Outra aplicação usa a porta 443 ou 80 | Use outras portas ([seção 8](#trocar-as-portas)) |
| `services.billing-api.env_file must be a string` | Docker Compose antigo | Atualize para a v2.24 ou superior |
| O navegador mostra "conexão não particular" | Certificado autoassinado | Esperado em testes. Em produção, instale o certificado da empresa |
| Página **403 Forbidden** do Nginx | O seu IP está fora das faixas permitidas | Ajuste `rede-permitida.conf` ([seção 8](#restringir-o-acesso-à-vpn)) |
| `billing-web` não sobe e aparece *dependency failed* | A API não ficou saudável | Veja `docker compose logs billing-api` |
| Log da API com "Configuração insegura para produção" | Chave definida no `.env` com menos de 32 caracteres | Gere chaves maiores ou deixe os campos vazios para geração automática |
| "Usuário ou senha inválidos" com a senha certa | O usuário não foi cadastrado no Billing, está inativo, ou o LDAP não respondeu | Crie o usuário (item 6.3) e verifique o LDAP (item 6.4) |
| "Código inválido" no segundo fator | O relógio do celular está fora de hora | Ative a data/hora automática no celular |
| "Etapa de login expirada" | Mais de 5 minutos entre a senha e o código | Informe usuário e senha de novo |
| "Muitas tentativas. Aguarde um minuto" | Limite de 10 tentativas por minuto atingido | Aguarde 1 minuto |
| O usuário perdeu o celular | — | Tela **Usuários** → **Redefinir 2FA**. No próximo login ele cadastra de novo |
| A sessão cai a cada 8 horas | Limite absoluto da sessão | Comportamento esperado. Ajuste `BILLING_SESSAO_MAXIMA_HORAS` se necessário |

Se o problema continuar, os logs ajudam a encontrar a causa:

```bash
docker compose logs --tail 100 billing-api
docker compose logs --tail 100 billing-web
```

---

## 11. Desinstalar

Para parar e remover os contêineres, **mantendo os dados**:

```bash
docker compose down
```

Para remover os contêineres **e apagar todos os dados** (banco, chaves e certificados). Essa ação é
irreversível, então faça backup antes:

```bash
docker compose down -v
```

Para remover também as imagens construídas:

```bash
docker image rm billing-api billing-web
```
