# Papel
Você é um engenheiro de software sênior. Gere o sistema descrito abaixo de forma incremental, com código de produção, testes e documentação.

# Contexto
Sistema interno de **billing (faturamento)** da empresa. O sistema atual tem um controle de login antigo e simples, sem expiração adequada de sessão e sem proteção contra ataques. A empresa já sofreu dois incidentes:
- uma invasão que roubou e expôs dados do sistema;
- um script malicioso que tentou milhares de logins em poucos minutos contra uma conta.

A empresa também precisa atender exigências de auditoria (LGPD e outras): sessões com tempo determinado, revogação de acesso e logs de auditoria.

**Prioridade:** o módulo de autenticação é pré-requisito. Nenhuma outra funcionalidade de billing vai para produção sem login, sessão e revogação de token funcionando de forma robusta.

# Stack
- Backend: [definir]
- Banco de dados: [definir]
- Frontend: [definir]
- Provedor de identidade: login corporativo da empresa (SSO)

# 1. Módulo de autenticação (implementar primeiro)

## 1.1 Atores
| Ator | O que pode fazer |
|---|---|
| Usuário não autenticado | Acessar apenas a tela ou endpoint de login |
| Usuário autenticado | Renovar a sessão, consultar se ela está ativa e fazer logout |
| Administrador/Operação (SRE) | Verificar a saúde do provedor de identidade, sem precisar autenticar como usuário final |
| Provedor de Identidade (externo) | Validar credenciais e emitir tokens |
| Base local de usuários | Guardar perfil, papéis e vínculo do usuário no banco do próprio sistema |

Não há integração de parceiros via API neste módulo. O foco é o login interativo.

## 1.2 Fluxo de login
1. O usuário informa usuário e senha, que são os do login corporativo.
2. O sistema aplica o limite de tentativas: **10 requisições por minuto por IP**, valor configurável.
3. As credenciais são validadas pelo provedor de identidade corporativo.
4. O sistema exige **autenticação em dois fatores**, porque o login corporativo hoje não tem esse recurso.
5. Com as credenciais e o segundo fator válidos, o sistema emite **tokens revogáveis** e carrega os papéis do usuário a partir da base local.

## 1.3 Sessão
- A sessão tem tempo de expiração determinado.
- O usuário pode renovar a sessão periodicamente.
- Há um endpoint para consultar se a sessão está ativa.
- Os tokens podem ser revogados, por exemplo quando o acesso de um usuário é retirado.

## 1.4 Logout
- O logout encerra a sessão de fato: revoga o token no servidor e remove os cookies de autenticação do navegador.
- Se a página for reaberta depois do logout, o sistema exige uma nova autenticação.

## 1.5 Saúde do provedor de identidade
- Endpoint para o time de Operação/SRE verificar se o provedor de identidade está saudável.

# 2. Perfis e funcionalidades do billing (após a autenticação)

| Perfil | Funcionalidades |
|---|---|
| Administrador | Cadastrar empresas, clientes, contratos, segmentos, programas, grupos econômicos, centros de custo, unidades de negócio, fornecedores e regras de serviço |
| Operacional | Fazer lançamentos por cliente × período × regra de serviço e gerar planilhas para alimentar o ERP |
| Gestor/Supervisor | Validar e aprovar os lançamentos feitos pelo operacional |

- Os escopos são estritamente separados. O administrador **não pode** executar funções do operacional, e vice-versa.
- Toda permissão deve ser verificada no servidor.
- Se um usuário tentar acessar uma funcionalidade fora do seu perfil, o sistema nega o acesso e registra a tentativa para análise posterior.

# 3. Auditoria
Registrar, para **todos** os usuários:
- acessos ao sistema, com data e hora, IP e usuário, incluindo tentativas de login que falharam;
- toda operação de edição ou remoção em qualquer dado (empresas, clientes, contratos etc.);
- tentativas de acesso negadas por falta de permissão.

Os registros devem poder ser filtrados e segregados por usuário, perfil e tipo de ação. Como o volume cresce com o tempo, o armazenamento e a consulta dos logs devem ser pensados para essa escala.

# 4. Rede e comunicação
- Toda comunicação entre usuário e servidor deve ser criptografada (HTTPS/TLS), inclusive dentro da VPN.
- Ver ponto em aberto sobre acesso só por VPN ou também por redes públicas.

# 5. Capacidade
- Uso previsto de cerca de 50 usuários, mas o sistema deve ser dimensionado para **até 1.000 usuários**. Isso vale para a capacidade do servidor e para o volume de logs.

# 6. Entregáveis
1. Modelo de dados, incluindo a base local de usuários, perfis, papéis, tokens e logs de auditoria.
2. API documentada: login, renovação, status da sessão, logout e saúde do provedor de identidade, seguida dos endpoints de billing.
3. Backend e frontend: tela de login com segundo fator, depois as telas de cadastros, lançamentos, aprovação, geração de planilha ERP e consulta de auditoria.
4. Testes automatizados.
5. README com instalação, configuração (limites, tempo de sessão, integração com o SSO) e pontos em aberto.

# 7. Critérios de aceite
- Um usuário não autenticado só acessa o login. Qualquer outra rota é recusada.
- A 11ª tentativa de login no mesmo minuto, a partir do mesmo IP, é bloqueada.
- Sem o segundo fator, o login não é concluído.
- Um token revogado ou expirado é recusado.
- Após o logout, reabrir a página exige um novo login, e os cookies de autenticação foram removidos.
- O endpoint de saúde do provedor de identidade responde sem exigir login de usuário final.
- Um administrador recebe acesso negado ao tentar fazer um lançamento, e a tentativa fica registrada.
- Um operacional recebe acesso negado ao tentar editar um cadastro, e a tentativa fica registrada.
- Toda edição ou remoção gera um registro de auditoria com usuário, data, IP e dado afetado.

# 8. Pontos em aberto (as entrevistas divergem)
Implementar de forma configurável e listar no README. Não decida sozinho:
- **Acesso:** a primeira entrevista diz "apenas pela VPN, sem acesso externo". A segunda menciona "cliente final" e preocupação com acesso por redes públicas.
- **Público:** a primeira entrevista diz que só o pessoal interno acessa. A segunda cita "visitante ou cliente" e "cliente final" como usuários.
- **Perfil Administrador:** em uma entrevista, ele faz os cadastros de base. Na outra, "Administrador/Operação" é o time de SRE que só verifica o provedor de identidade. Confirmar se são perfis distintos.
- **Tempo de sessão:** a duração da sessão e a política de renovação não foram definidas.
- **Retenção dos logs:** o prazo não foi definido.
- **Segundo fator:** o método (aplicativo autenticador, SMS etc.) não foi definido.

# Forma de trabalho
Antes de codificar, apresente a arquitetura, o modelo de dados e a lista de endpoints, e aguarde minha confirmação.
Implemente primeiro o módulo de autenticação completo, com testes. Só depois avance para cadastros, lançamentos,
aprovação, planilha ERP e auditoria, mostrando os testes ao final de cada módulo.
