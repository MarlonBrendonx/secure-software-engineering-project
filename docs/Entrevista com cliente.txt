Entrevista com o "Cliente"

Analista de Requisitos:  Para começarmos, pode me contar por que este módulo de autenticação está sendo criado agora? O que motivou o projeto?

Cliente:  Hoje nosso sistema de billing tem um controle de login muito simples, feito há anos, sem expiração adequada de sessão e sem nenhum tipo elaborado de proteção contra ataques cibernéticos. Uma vez, tivemos um incidente em que um hacker executou um script malicioso e tentou milhares de logins em poucos minutos contra uma conta de cliente. Além disso, estamos entrando em conformidade com exigências de auditoria (LGPD e outros), e isso exige sessões controladas (tempo determinado), revogação de acesso e logs de auditoria.

Analista de Requisitos:  Compreendo. E qual é a expectativa de prazo e qual o grau de importância dissas questões para o negócio?

Cliente:  É imprescindível resolver agora. Nenhuma outra funcionalidade de billing poderá avançar para produção enquanto não tivermos login, sessão e revogação de token funcionando de forma robusta, porque todo o resto fica atrás desse módulo.

Analista de Requisitos:  Quem efetivamente vai interagir com esse módulo de autenticação? Preciso entender todos os perfis.

Cliente:  Temos quatro grupos:

1. Usuário não autenticado —> qualquer visitante ou cliente que ainda não fez login. Ele só pode acessar a tela/endpoint de login.
2. Usuário autenticado —> cliente final ou operador que já passou pelo login e possui uma sessão válida. Ele pode renovar sua sessão, consultar se ela ainda está ativa e encerrar sessão (logout).
3. Administrador/Operação —> nosso time de operação/SRE, que precisa apenas verificar se o provedor de identidade está saudável, sem necessariamente autenticar como usuário final.
4. Sistemas externos-> o Provedor de Identidade que valida credenciais e emite tokens; e a Base local de usuários, que guarda perfil, papéis e vínculo do usuário dentro do nosso próprio banco.

Analista de Requisitos:  Existe algum outro tipo de usuário, como uma integração de parceiro via API?

Cliente:  Ainda não neste módulo, o foco agora é login interativo de usuário.

Analista de Requisitos:  O que precisa acontecer quando um usuário desconhecido tenta entrar no sistema?

Cliente:  Ele informa usuário e senha. Então, o sistema:
-> Precisa aplicar um limite de tentativas.
-> Depois, validar as credenciais.
-> Se as credenciais forem válidas, o sistema deve emitir tokens revogáveis.

Analista de Requisitos:  E qual o limite de tentativas que você mencionou? Você já tem um número em mente?

Cliente:  Pensamos em 10 requisições por minuto por IP. Pode ser ajustável depois, mas esse é o valor inicial que colocamos no requisito.

Analista de Requisitos:  Além de renovar periodicamente, o usuário autenticado precisa de mais alguma operação sobre a própria sessão?

Cliente:  Sim, o usuário aperta "Sair" e a aplicação tem que encerrar de verdade.

Analista de Requisitos:  O que significa "encerrar de verdade"?

Cliente:  Os cookies de autenticação não devem ficar no navegador do usuário, quero dizer... se a página for aberta novamente, deve ser exigida uma nova autenticação.

Analista de Requisitos:  Você possui alguma recomendação sobre funções de registros para auditoria ou log?

Cliente:  Sim. É importante ter informações de auditoria que permitam conferir os acessos, como data, IPs, etç.

Analista de Requisitos:  Para encerrar, você mencionou o incidente de ataque com execução de código malicioso (tentativas intensas de login). Existe algum outro cenário de ameaças que já preocupa vocês, mesmo antes de eu levantar minha própria lista de riscos?

Cliente:  Sim, há uma preocupação com a segurança no acesso por meio de rede públicas, quero dizer, alguém poderia interceptar informações de login e acessar o sistema. Questões desse tipo.

Analista de Requisitos:  Perfeito, esses pontos ajudam bastante. Vou estudar tudo isso e formalizar em requisitos, elaborar uma lista de vulnerabilidades e outras questões de segurança importantens. 
Assim que finalizar, vou cotatá-lo para revisarmos juntos antes de avançarmos no projeto.