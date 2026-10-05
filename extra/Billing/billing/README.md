# Billing — sistema interno de faturamento

Sistema de billing com módulo de autenticação robusto (login corporativo + segundo fator, sessões com
prazo, revogação de tokens e trilha de auditoria) e as funcionalidades de cadastros, lançamentos,
aprovação e planilha para o ERP.

| Camada | Tecnologia |
|---|---|
| API | Python 3.13 + FastAPI + SQLAlchemy |
| Banco | PostgreSQL 16 |
| Limite de tentativas | Redis 7 |
| Interface | React 18 + TypeScript (Vite) |
| Entrada / TLS | Nginx (HTTPS obrigatório, restrição por faixa de IP da VPN) |
| Login | LDAP / Active Directory corporativo + TOTP (aplicativo autenticador) |

---

## Arquitetura

```
Navegador ──HTTPS──► Nginx (TLS, só faixas da VPN) ──► API FastAPI ──► PostgreSQL
                         │                                  │
                         └── arquivos estáticos (React)     ├──► Redis (limite de tentativas)
                                                            └──► LDAP corporativo (validação de senha)
```

- A API **não** é exposta diretamente: só o Nginx publica portas.
- O sistema **não guarda senhas**. Usuário e senha são validados no login corporativo (adaptador
  `app/idp.py`). A base local guarda apenas o vínculo do login com o perfil e o segredo do segundo fator
  (cifrado).
- Tokens ficam em cookies `HttpOnly`, `Secure` e `SameSite=Strict`: o JavaScript da página nunca os lê.

### Fluxo de login

1. `POST /api/auth/login` com usuário e senha.
   O limite de **10 tentativas por minuto por IP** é aplicado *antes* de qualquer validação.
2. A senha é validada no LDAP, e o usuário precisa existir e estar ativo na base local.
   A resposta de erro é sempre a mesma, para não revelar se o usuário existe.
3. É emitido um desafio de 5 minutos para o segundo fator.
   - No primeiro acesso, `POST /api/auth/mfa/cadastro` gera o QR code para o aplicativo autenticador.
4. `POST /api/auth/mfa/verificar` confere o código de 6 dígitos (também com limite de tentativas).
   Se estiver certo, abre a sessão e emite:
   - **token de acesso** (JWT, 15 min);
   - **token de renovação** (opaco, guardado só como hash no banco, trocado a cada uso).

### Sessão e revogação

- Toda requisição confere a sessão no banco. Por isso, revogar tem **efeito imediato**, mesmo que o
  token ainda não tenha expirado.
- `POST /api/auth/renovar` emite novos tokens até o **limite absoluto de 8 h**. Depois disso, é preciso
  entrar de novo.
- Desativar um usuário ou mudar o perfil dele encerra todas as sessões abertas.
- `POST /api/auth/logout` revoga a sessão no servidor, apaga os cookies e envia
  `Clear-Site-Data: "cookies"`. Reabrir a página exige um novo login.

### Perfis

| Perfil | Pode | Não pode |
|---|---|---|
| ADMINISTRADOR | Cadastros de base (10 entidades) e gestão de usuários | Lançar, aprovar, gerar planilha ERP |
| OPERACIONAL | Lançamentos e planilha ERP; consultar cadastros | Alterar cadastros, aprovar |
| GESTOR | Validar e aprovar ou reprovar lançamentos; consultar | Lançar, alterar cadastros |
| AUDITOR | Consultar e exportar a trilha de auditoria | Qualquer alteração |
| OPERACAO | Sem telas; saúde do IdP via token de operação | — |

Toda permissão é verificada no servidor. Uma tentativa fora do perfil recebe `403` e gera um registro
`ACESSO_NEGADO` com usuário, perfil, IP, rota e horário.

### Auditoria

O sistema registra para todos os usuários:
- login com sucesso;
- falhas de login (com o motivo), falhas do segundo fator e bloqueios por excesso de tentativas;
- logout e revogação de sessões;
- acessos negados;
- toda criação, edição e remoção, com os valores **antes e depois**;
- submissão, aprovação e reprovação de lançamentos;
- geração e download da planilha ERP.

A gravação é feita na mesma transação da alteração: ou os dois ficam salvos, ou nenhum.

Não existem rotas para editar ou apagar logs. A consulta permite filtrar por usuário, login, perfil,
tipo de ação, entidade e período, com paginação e exportação em CSV.

**Escala (até 1.000 usuários):** a tabela tem índices por data, usuário+data, tipo+data e perfil+data.
Renovações de sessão não são registradas, e um ataque de força bruta gera um único registro por minuto,
não um por tentativa. Assim o volume fica proporcional ao uso real.

---

## Como executar

### Contêiner único (interface + API no mesmo Docker)

Uma só imagem com a interface React, a API e o Nginx (HTTPS). Os dados ficam no volume `/dados`:
banco SQLite, certificado e chaves geradas na primeira execução.

```bash
docker build -t billing .

# Demonstração: login simulado, sem LDAP. Senha de todos os usuários: demo123
docker run -d --name billing --restart unless-stopped \
  -p 443:443 -p 80:80 -v billing-dados:/dados -e BILLING_DEMO=1 billing
```

Acesse https://localhost e aceite o certificado autoassinado. Os usuários de demonstração são `admin`,
`operacional`, `gestor` e `auditor`. No primeiro login de cada um, escaneie o QR code com um aplicativo
autenticador.

Para uso real, retire `BILLING_DEMO` e informe o LDAP da empresa:

```bash
docker run -d --name billing --restart unless-stopped -p 443:443 -p 80:80 -v billing-dados:/dados \
  -e BILLING_LDAP_URL=ldaps://ldap.empresa.local:636 -e BILLING_LDAP_DOMINIO=EMPRESA billing
docker exec billing python3 -m app.cli criar-usuario joao.silva "João Silva" ADMINISTRADOR
```

| Ajuste | Como |
|---|---|
| Certificado da empresa | Coloque `billing.crt` e `billing.key` em `/dados/certs` do volume e reinicie |
| Publicar em outra porta | `-p 8443:443 -e BILLING_PORTA_HTTPS=8443`, para o redirecionamento HTTP→HTTPS apontar para a porta certa |
| Faixas de IP da VPN | Monte o seu arquivo em `/etc/nginx/rede-permitida.conf` (`-v ./rede.conf:/etc/nginx/rede-permitida.conf:ro`) |
| Chaves próprias | `-e BILLING_JWT_CHAVE_ATUAL=... -e BILLING_MFA_CHAVE_CIFRAGEM=... -e BILLING_OPS_TOKEN=...`. Sem isso, são geradas e guardadas em `/dados/segredos.env` |
| Token de operação gerado | `docker exec billing sh -c '. /dados/segredos.env; echo $GERADO_OPS'` |
| PostgreSQL/Redis externos | `-e BILLING_DATABASE_URL=postgresql+psycopg://... -e BILLING_LIMITADOR_TIPO=redis -e BILLING_REDIS_URL=redis://...` |

Se a API ou o Nginx pararem, o contêiner para, e o `--restart` o sobe de novo. O SQLite e o limite de
tentativas em memória atendem bem uma instância. Para várias instâncias, use PostgreSQL e Redis (veja a próxima
seção).

### Dois contêineres separados (API e interface)

Cada parte roda no seu próprio contêiner:

| Contêiner | Imagem | O que faz | Portas |
|---|---|---|---|
| `billing-api` | `backend/Dockerfile` | API FastAPI e banco SQLite no volume `/dados` | nenhuma publicada (só a rede interna) |
| `billing-web` | `frontend/Dockerfile` | Interface React e Nginx com HTTPS, que encaminha `/api` para a API | 443 e 80 |

**Com Docker Compose (recomendado):**

```bash
# Demonstração: login simulado, senha demo123 (usuários admin, operacional, gestor, auditor)
BILLING_DEMO=1 docker compose up -d --build

# Uso real: crie o .env a partir do .env.example (LDAP e, se quiser, chaves próprias)
docker compose up -d --build
docker compose exec billing-api python3 -m app.cli criar-usuario joao.silva "João Silva" ADMINISTRADOR
```

Para outras portas, use `BILLING_PORTA_HTTPS=8443 BILLING_PORTA_HTTP=8080 docker compose up -d`.

**Com `docker run`, um contêiner de cada vez:**

```bash
docker build -f backend/Dockerfile  -t billing-api .
docker build -f frontend/Dockerfile -t billing-web .

docker network create billing-rede

# 1) API: sem -p, fica acessível só na rede interna
docker run -d --name billing-api --network billing-rede --restart unless-stopped \
  -v billing-api-dados:/dados -e BILLING_DEMO=1 billing-api

# 2) Interface: aponta para a API pelo nome do contêiner
docker run -d --name billing-web --network billing-rede --restart unless-stopped \
  -p 443:443 -p 80:80 -v billing-web-certs:/certs \
  -e BILLING_API_URL=http://billing-api:8000 billing-web
```

Acesse https://localhost. Cada contêiner pode ser atualizado ou reiniciado sem mexer no outro: o Nginx
volta a encontrar a API pelo nome mesmo que ela reinicie com outro IP.

| Ajuste | Como |
|---|---|
| Certificado da empresa | Coloque `billing.crt` e `billing.key` no volume `/certs` do `billing-web` e reinicie esse contêiner |
| Faixas de IP da VPN | Monte o seu arquivo em `/etc/nginx/rede-permitida.conf` do `billing-web` |
| Token de operação gerado | `docker exec billing-api sh -c '. /dados/segredos.env; echo $GERADO_OPS'` |
| PostgreSQL e Redis em contêineres próprios | `docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build` (defina `POSTGRES_PASSWORD` no `.env`) |

### Desenvolvimento (sem Docker, sem LDAP)

```bash
cd backend
pip install -r requirements-dev.txt
export BILLING_AMBIENTE=desenvolvimento BILLING_DATABASE_URL=sqlite:///dev.db \
       BILLING_IDP_TIPO=fake BILLING_LIMITADOR_TIPO=memoria BILLING_COOKIE_SECURE=false \
       BILLING_FAKE_USUARIOS='{"admin":"senha1","op":"senha2","gestor":"senha3","auditor":"senha4"}'
python -m app.cli iniciar-banco
python -m app.cli criar-usuario admin "Admin" ADMINISTRADOR
python -m app.cli criar-usuario op "Operacional" OPERACIONAL
uvicorn app.main:app --reload          # documentação da API em http://localhost:8000/api/docs

cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

O provedor `fake` existe apenas para desenvolvimento e testes. A aplicação se recusa a subir com ele em
produção.

### Testes

```bash
cd backend && python -m pytest -q
```

47 testes cobrem todos os critérios de aceite:

| Critério de aceite | Teste(s) em `backend/tests/` |
|---|---|
| Não autenticado só acessa o login | `test_todas_as_rotas_protegidas_recusam_quem_nao_esta_logado` (percorre todas as rotas da API) |
| 11ª tentativa no mesmo minuto é bloqueada | `test_decima_primeira_tentativa_no_mesmo_minuto_e_bloqueada`, `test_limite_tambem_vale_para_o_codigo_do_segundo_fator` |
| Sem segundo fator não há login | `test_sem_segundo_fator_nao_ha_sessao`, `test_token_do_desafio_nao_serve_como_token_de_acesso` |
| Token revogado ou expirado é recusado | `test_token_expirado_e_recusado`, `test_revogacao_tem_efeito_imediato`, `test_token_assinado_com_outra_chave_e_recusado`, `test_sessao_nao_renova_depois_do_limite_absoluto` |
| Logout apaga cookies e exige novo login | `test_logout_revoga_no_servidor_e_apaga_os_cookies` |
| Saúde do IdP sem login de usuário final | `test_saude_do_provedor_sem_login_de_usuario` |
| Administrador não lança (e fica registrado) | `test_administrador_nao_faz_lancamento_e_a_tentativa_fica_registrada` |
| Operacional não edita cadastro (e fica registrado) | `test_operacional_nao_edita_cadastro_e_a_tentativa_fica_registrada`, `test_matriz_de_permissoes` |
| Edição/remoção geram auditoria completa | `test_edicao_e_remocao_de_cadastro_geram_auditoria`, `test_remocao_de_rascunho_fica_registrada` |

---

## Operação

| Situação | Comando |
|---|---|
| Desligamento de colaborador | Desativar na tela **Usuários** (encerra as sessões) ou `python -m app.cli revogar-sessoes LOGIN` |
| Usuário perdeu o celular | Tela **Usuários** → **Redefinir 2FA** |
| Suspeita de vazamento da chave JWT | Trocar `BILLING_JWT_CHAVE_ATUAL` e `BILLING_JWT_KID_ATUAL`, deixar `..._ANTERIOR` vazio, reiniciar a API e rodar `python -m app.cli revogar-todas-sessoes` |
| Rotação programada da chave JWT | Mover a chave atual para `..._ANTERIOR` (com o seu `kid`), definir uma nova chave atual e reiniciar. Os tokens antigos continuam válidos até expirarem (15 min) |
| Retenção de logs | `python -m app.cli limpar-logs` (agendar mensalmente; a própria limpeza fica registrada) |
| Saúde do provedor de identidade | `curl -H "X-Ops-Token: $BILLING_OPS_TOKEN" https://billing/api/saude/provedor-identidade` (200 = ok, 503 = falha) |

---

## Endpoints

| Grupo | Rotas |
|---|---|
| Autenticação | `POST /api/auth/login`, `POST /api/auth/mfa/cadastro`, `POST /api/auth/mfa/verificar`, `POST /api/auth/renovar`, `GET /api/auth/sessao`, `POST /api/auth/logout` |
| Saúde | `GET /api/saude/provedor-identidade` (token de operação), `GET /api/saude/api` |
| Usuários | `GET/POST /api/usuarios`, `PUT /api/usuarios/{id}`, `POST /api/usuarios/{id}/revogar-sessoes`, `POST /api/usuarios/{id}/redefinir-mfa` |
| Cadastros | `GET /api/cadastros`, `GET/POST /api/cadastros/{entidade}`, `GET/PUT/DELETE /api/cadastros/{entidade}/{id}` |
| Lançamentos | `GET/POST /api/lancamentos`, `GET/PUT/DELETE /api/lancamentos/{id}`, `POST /api/lancamentos/{id}/submeter` |
| Aprovação | `GET /api/aprovacoes/pendentes`, `POST /api/lancamentos/{id}/aprovar`, `POST /api/lancamentos/{id}/reprovar` |
| Planilha ERP | `POST/GET /api/exportacoes-erp`, `GET /api/exportacoes-erp/{id}/arquivo` |
| Auditoria | `GET /api/auditoria`, `GET /api/auditoria/tipos`, `GET /api/auditoria/exportar` |

As entidades de cadastro são: `empresas`, `clientes`, `contratos`, `segmentos`, `programas`,
`grupos-economicos`, `centros-custo`, `unidades-negocio`, `fornecedores` e `regras-servico`.

A documentação interativa fica em `/api/docs` fora de produção.

---

## Pontos em aberto

Todos foram implementados de forma configurável. **Confirmar com o cliente.**

| Ponto | Padrão adotado | Onde mudar |
|---|---|---|
| Acesso só pela VPN ou também externo | Só faixas privadas (VPN) | `infra/nginx/rede-permitida.conf` |
| Público: só interno ou também "cliente final" | Só usuários cadastrados na base local | — (exigiria um novo perfil) |
| Administrador de cadastros × Operação/SRE | Perfis distintos: ADMINISTRADOR e OPERACAO | `app/models.py` → `Papel` |
| Tempo de sessão | Acesso de 15 min, renovação até 8 h | `BILLING_ACCESS_TOKEN_MINUTOS`, `BILLING_SESSAO_MAXIMA_HORAS` |
| Retenção dos logs | 5 anos | `BILLING_RETENCAO_LOGS_ANOS` |
| Método do segundo fator | TOTP (aplicativo autenticador) | `app/seguranca.py` |
| Quem consulta a auditoria | Perfil AUDITOR dedicado | `app/routers/auditoria.py` |
| Quem gerencia usuários e revoga sessões | ADMINISTRADOR (e linha de comando) | `app/routers/usuarios.py` |
| Cálculo do lançamento | Quantidade × valor unitário da regra de serviço, calculado no servidor | `app/routers/billing.py` → `_calcular` |

## O que não foi verificado aqui

- **Login contra um LDAP real:** os testes usam o provedor fake. Valide `BILLING_LDAP_URL` e
  `BILLING_LDAP_DOMINIO` em homologação.
- **Complemento com PostgreSQL e Redis** (`docker-compose.postgres.yml`): não foi executado aqui. O
  contêiner único e os dois contêineres separados foram construídos e testados (build, subida, HTTPS,
  redirecionamento e fluxo completo nos quatro perfis).

A API e a interface foram testadas rodando juntas: login com cadastro do 2FA, cadastros, lançamento,
gestão de usuários e logout.
