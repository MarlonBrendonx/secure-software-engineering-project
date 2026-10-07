# Papel
Você é um engenheiro de software sênior. Gere o sistema descrito abaixo de forma incremental, com código de produção, testes e documentação.

# Contexto
Sistema interno de **billing (faturamento)** da empresa. O sistema atual tem um controle de login antigo e simples, sem expiração adequada de sessão e sem proteção contra ataques. A empresa já sofreu dois incidentes:
- uma invasão que roubou e expôs dados do sistema;
- um script malicioso que tentou milhares de logins em poucos minutos contra uma conta.

A empresa também precisa atender exigências de auditoria (LGPD e outras): sessões com tempo determinado, revogação de acesso e logs de auditoria.

**Prioridade:** o módulo de autenticação é pré-requisito. Nenhuma outra funcionalidade de billing vai para produção sem login por SSO, segundo fator, sessão e revogação de token funcionando de forma robusta.

# Stack
- Backend: [definir]
- Banco de dados: [definir]
- Frontend: [definir]
- Provedor de identidade: **SSO via OpenID Connect (OIDC)**, com vários provedores (Google, Microsoft Entra ID e o provedor corporativo da empresa). Obrigatório.
- Segundo fator: **aplicativo autenticador (TOTP, RFC 6238)**: Google Authenticator, Microsoft Authenticator, Authy ou similar. Obrigatório.
- Infra: **Docker + Docker Compose**. Todo o sistema roda em contêineres. Obrigatório.

# 1. Módulo de autenticação (implementar primeiro)

## 1.1 Atores
| Ator | O que pode fazer |
|---|---|
| Usuário não autenticado | Acessar apenas a tela ou os endpoints de login |
| Usuário autenticado | Renovar a sessão, consultar se ela está ativa, gerenciar o próprio 2FA e fazer logout |
| Administrador/Operação (SRE) | Verificar a saúde dos provedores de identidade, sem precisar autenticar como usuário final |
| Provedores de identidade (externos) | Autenticar a pessoa (Google, Microsoft, corporativo) e emitir o `id_token` |
| Base local de usuários | Guardar perfil, papéis, vínculo com as contas dos provedores e o 2FA, no banco do próprio sistema |

Não há integração de parceiros via API neste módulo. O foco é o login interativo.

## 1.2 SSO com vários provedores (obrigatório)
- **Protocolo:** OIDC Authorization Code com **PKCE**, com `state` e `nonce` validados.
- **Validação do `id_token`:** assinatura pelo JWKS do provedor, `iss`, `aud` e `exp`. Para a Microsoft multi-tenant, o issuer contém o tenant (`{tenantid}`).
- **Provedores configuráveis:** cada um vira um botão "Entrar com …" na tela de login. A configuração fica num único parâmetro (JSON) com, por provedor:
  - `name`, `issuer`, `client_id`, `client_secret`
  - `allowed_domains`: domínios de e-mail aceitos
  - `auto_provision`: cria sem perfil quem vier de domínio permitido. Padrão: desligado
  - `link_by_email`: padrão ligado
  - `require_email_verified`: padrão ligado
  - `trust_idp_mfa`: aceita o MFA do provedor (claim `amr`) no lugar do TOTP. Padrão: desligado
- **URL de retorno** de cada provedor: `{URL_PÚBLICA}/api/v1/auth/oidc/{provedor}/callback`.
- **Regras de vínculo:**
  1. Uma conta de provedor já vinculada (par provedor + `sub`) entra como o usuário vinculado. Daí em diante vale o `sub`, mesmo que o e-mail mude.
  2. Um **e-mail verificado** igual ao de um usuário pré-cadastrado pelo administrador é vinculado e entra.
  3. Com `auto_provision` e domínio permitido, o usuário é criado **sem perfil** e só pode solicitar acesso.
  4. Qualquer outro caso é recusado e registrado na auditoria.
- **Proteções obrigatórias:**
  - Nunca vincular por e-mail não verificado.
  - Uma segunda conta do mesmo provedor não assume um usuário que já tem vínculo.
  - O SSO nunca entra numa conta local com o mesmo e-mail.
  - Uma mesma pessoa pode ter mais de um provedor vinculado.
- **Erros do retorno** voltam para a tela de login como `/login?erro=<código>`, com mensagem clara. Por exemplo: domínio não permitido, usuário não cadastrado, e-mail não verificado, conflito de identidade, usuário bloqueado, cancelado, expirado.
- **Contas locais** (usuário e senha, hash Argon2id), apenas para quem não tem conta nos provedores, como a auditoria externa, e para o primeiro acesso antes de configurar o SSO. Também passam pelo 2FA.

## 1.3 Fluxo de login
1. O usuário escolhe um provedor ("Entrar com Google", "Entrar com Microsoft"…) ou, se for conta local, informa usuário e senha.
2. O sistema aplica o limite de tentativas: **10 requisições por minuto por IP**, valor configurável. O limite vale também no retorno do SSO e na etapa do código.
3. O provedor autentica a pessoa e o sistema aplica as regras de vínculo da seção 1.2.
4. O sistema exige o **segundo fator por aplicativo autenticador**. Antes do código **não existe sessão**: a primeira etapa gera só um ticket de uso único e curta duração (5 minutos), em cookie `HttpOnly`.
5. Com o código válido, o sistema emite **tokens revogáveis** e carrega os papéis do usuário a partir da base local.

## 1.4 Segundo fator (TOTP)
- **Cadastro:** a tela mostra um **QR code** e a chave para digitação manual. O 2FA só passa a valer depois que o usuário confirma o primeiro código.
- **Códigos de recuperação:** 10, de uso único, guardados só como hash e mostrados uma única vez.
- **Anti-replay:** um código aceito não vale de novo. A tolerância de relógio é de ±1 passo de 30 s.
- **Limites:** 5 códigos errados por ticket e 5 por usuário a cada 5 minutos, somando todas as tentativas.
- **Segredo** do TOTP cifrado no banco, com chave fora do código e rotacionável.
- **Obrigatoriedade:** obrigatório para os perfis privilegiados. Configurável para todos. Sem o 2FA, as permissões desses perfis ficam bloqueadas até o cadastro.
- **Perda do celular:** o administrador pode resetar o 2FA de um usuário, o que encerra as sessões dele.

## 1.5 Sessão
- A sessão tem tempo de expiração determinado.
- O usuário pode renovar a sessão periodicamente.
- Há um endpoint para consultar se a sessão está ativa.
- Os tokens podem ser revogados, por exemplo quando o acesso de um usuário é retirado. A revogação vale na próxima requisição.
- Tokens em cookies `HttpOnly`, `Secure` e `SameSite`, com proteção CSRF.

## 1.6 Logout
- O logout encerra a sessão de fato: revoga o token no servidor e remove os cookies de autenticação do navegador.
- Se a página for reaberta depois do logout, o sistema exige uma nova autenticação.

## 1.7 Saúde dos provedores de identidade
- Endpoint para o time de Operação/SRE verificar se cada provedor de identidade configurado está acessível.

# 2. Perfis e funcionalidades do billing (após a autenticação)

| Perfil | Funcionalidades |
|---|---|
| Administrador | Cadastrar empresas, clientes, contratos, segmentos, programas, grupos econômicos, centros de custo, unidades de negócio, fornecedores e regras de serviço. Gerir usuários e pré-cadastrar os e-mails que podem entrar por SSO |
| Operacional | Fazer lançamentos por cliente × período × regra de serviço e gerar planilhas para alimentar o ERP |
| Gestor/Supervisor | Validar e aprovar os lançamentos feitos pelo operacional |

- Os escopos são estritamente separados. O administrador **não pode** executar funções do operacional, e vice-versa.
- Toda permissão deve ser verificada no servidor.
- Se um usuário tentar acessar uma funcionalidade fora do seu perfil, o sistema nega o acesso e registra a tentativa para análise posterior.

# 3. Auditoria
Registrar, para **todos** os usuários:
- acessos ao sistema, com data e hora, IP, usuário e provedor usado, incluindo tentativas de login que falharam e recusas do SSO;
- eventos do 2FA: cadastro, código errado, uso de código de recuperação e reset pelo administrador;
- toda operação de edição ou remoção em qualquer dado (empresas, clientes, contratos etc.);
- tentativas de acesso negadas por falta de permissão.

Os registros devem poder ser filtrados e segregados por usuário, perfil e tipo de ação. Segredos (senhas, segredo do TOTP) nunca aparecem nos logs. Como o volume cresce com o tempo, o armazenamento e a consulta dos logs devem ser pensados para essa escala.

# 4. Execução em contêineres (obrigatório)
Todo o sistema roda com Docker Compose. A máquina só precisa do Docker: nada de linguagem, banco ou servidor web instalado no host.

| Contêiner | Função | Porta |
|---|---|---|
| `web` | Proxy reverso (ex.: Nginx) servindo o frontend compilado no build da imagem e repassando `/api` para a API | **única porta publicada** |
| `api` | Backend | nenhuma: só o `web` acessa |
| `db` | Banco de dados | só em `127.0.0.1`, se publicada |
| `cache` | Rate limit e dados de sessão compartilhados entre instâncias (ex.: Redis) | só em `127.0.0.1`, se publicada |

- `docker compose up -d --build` sobe tudo do zero.
- Healthcheck em todos os contêineres, `depends_on` por saúde e `restart: unless-stopped`.
- Na subida, a API espera o banco ficar disponível e aplica as migrations sozinha.
- **Chaves geradas automaticamente:** se a chave de assinatura dos tokens ou a chave que cifra os segredos do 2FA não forem informadas, a API gera as duas na primeira subida e guarda num **volume próprio**. Elas sobrevivem a recriar o contêiner. Chaves informadas na configuração têm prioridade.
- Configuração opcional num arquivo `.env`, fora do git: provedores de SSO, tempos de sessão, limites.
- Comandos administrativos executados dentro do contêiner, com as mesmas chaves da API, por exemplo `docker compose exec api <cli> create-local-user ...`. Precisam existir comandos para:
  - criar o primeiro administrador (por e-mail do SSO);
  - criar conta local (pedindo a senha);
  - gerar chaves;
  - encerrar todas as sessões;
  - recifrar os segredos do 2FA.
- A API roda sem usuário root. O banco tem dois usuários: um dono das tabelas, para as migrations, e outro da aplicação, sem `UPDATE`/`DELETE` na auditoria.
- Os dados ficam em volumes nomeados (banco e chaves), e o README explica o backup dos dois.

# 5. Rede e comunicação
- Toda comunicação entre usuário e servidor deve ser criptografada (HTTPS/TLS), inclusive dentro da VPN. Em produção, o contêiner `web` fica atrás de TLS, com cookies `Secure`.
- O IP real do usuário chega à API pelo proxy (`X-Forwarded-For`) e é usado no rate limit e na auditoria.
- Ver ponto em aberto sobre acesso só por VPN ou também por redes públicas.

# 6. Capacidade
- Uso previsto de cerca de 50 usuários, mas o sistema deve ser dimensionado para **até 1.000 usuários**. Isso vale para a capacidade do servidor e para o volume de logs.

# 7. Entregáveis
1. Modelo de dados, incluindo a base local de usuários, vínculos com os provedores de SSO, 2FA, perfis, papéis, tokens e logs de auditoria.
2. API documentada (OpenAPI):
   - autenticação: provedores, início e retorno do SSO, login local, verificação do código, cadastro e gestão do 2FA, renovação, status da sessão, logout e saúde dos provedores;
   - depois, os endpoints de billing.
3. Backend e frontend:
   - tela de login com os botões dos provedores e a etapa do código;
   - tela de segurança da conta, com QR code e códigos de recuperação;
   - depois, as telas de cadastros, lançamentos, aprovação, geração de planilha ERP e consulta de auditoria.
4. `Dockerfile` da API e do frontend e `docker-compose.yml` com os quatro contêineres.
5. Testes automatizados. Incluir um teste do cliente OIDC contra um provedor OIDC local de teste (JWKS, assinatura, `aud`, `nonce`), sem depender do Google ou da Microsoft.
6. README com:
   - instalação com Docker e primeiro acesso;
   - **passo a passo para registrar o sistema no Google Cloud Console**: criar o projeto, configurar a tela de consentimento e os usuários de teste, criar o cliente OAuth "Aplicativo da Web" com a URL de retorno exata e copiar o ID e a chave secreta. O mesmo para o Microsoft Entra;
   - **criação do `.env`** com o ID e a chave colados, e comandos para conferir se a API leu a configuração;
   - configuração (limites, tempo de sessão, provedores);
   - backup, solução de problemas (incluindo os erros comuns do Google, como `redirect_uri_mismatch` e `access_denied`) e pontos em aberto.

# 8. Critérios de aceite
- Um usuário não autenticado só acessa o login. Qualquer outra rota é recusada.
- A 11ª tentativa de login no mesmo minuto, a partir do mesmo IP, é bloqueada.
- Login pelo Google e pela Microsoft funciona para um e-mail pré-cadastrado e é recusado para um e-mail não cadastrado ou de domínio não permitido.
- Um e-mail não verificado pelo provedor nunca é vinculado a um usuário.
- Uma segunda conta do mesmo provedor com o mesmo e-mail não assume um usuário já vinculado.
- `state` ou `nonce` inválido, ou `id_token` com assinatura ou `aud` incorretos, é recusado.
- Sem o segundo fator, o login não é concluído e nenhuma sessão é criada.
- O mesmo código TOTP não é aceito duas vezes, e um código de recuperação vale uma vez só.
- Um token revogado ou expirado é recusado.
- Após o logout, reabrir a página exige um novo login, e os cookies de autenticação foram removidos.
- O endpoint de saúde dos provedores responde sem exigir login de usuário final.
- Um administrador recebe acesso negado ao tentar fazer um lançamento, e a tentativa fica registrada.
- Um operacional recebe acesso negado ao tentar editar um cadastro, e a tentativa fica registrada.
- Toda edição ou remoção gera um registro de auditoria com usuário, data, IP e dado afetado.
- Em uma máquina só com Docker, `docker compose up -d --build` deixa os quatro contêineres saudáveis, e o sistema abre na porta do `web`.
- Recriar os contêineres (`docker compose up -d --force-recreate`) preserva os dados e as chaves: as sessões e o 2FA continuam válidos.
- A API não fica acessível diretamente pela rede, só através do `web`.

# 9. Pontos em aberto (as entrevistas divergem)
Implementar de forma configurável e listar no README. Não decida sozinho:
- **Acesso:** a primeira entrevista diz "apenas pela VPN, sem acesso externo". A segunda menciona "cliente final" e preocupação com acesso por redes públicas.
- **Público:** a primeira entrevista diz que só o pessoal interno acessa. A segunda cita "visitante ou cliente" e "cliente final" como usuários. Isso define se `auto_provision` fica ligado e quais domínios são permitidos.
- **Perfil Administrador:** em uma entrevista, ele faz os cadastros de base. Na outra, "Administrador/Operação" é o time de SRE que só verifica o provedor de identidade. Confirmar se são perfis distintos.
- **Provedores de SSO:** quais serão usados em produção (Google Workspace, Microsoft 365 ou o provedor corporativo) e quais domínios de e-mail são aceitos.
- **MFA do provedor:** aceitar ou não o MFA do provedor corporativo no lugar do TOTP (`trust_idp_mfa`).
- **Tempo de sessão:** a duração da sessão e a política de renovação não foram definidas.
- **Retenção dos logs:** o prazo não foi definido.

# Forma de trabalho
Antes de codificar, apresente a arquitetura, o modelo de dados, a lista de endpoints e o desenho dos contêineres, e aguarde minha confirmação.
Implemente primeiro o módulo de autenticação completo (SSO, 2FA, sessão, revogação e logout), já rodando em contêineres e com testes. Só depois avance para cadastros, lançamentos, aprovação, planilha ERP e auditoria, mostrando os testes ao final de cada módulo.
