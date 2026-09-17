Entrevista com o "Cliente"

Analista de Requisitos:  Para começarmos, pode me contar se o sistema precisa fazer alguma validação ou autenticação de usuário?

Cliente: Sim, o sistema precisa de um painel de administrador que só pode ser acessado por usuário autorizado. Só que precisa ser um esquema bem seguro, porque há alguns anos atrás tivemos um problema com um hacker que invadiu nossos sitema antigo e causou o maior estrago, roubando dados e expondo informações do sistema. Isso não pode acontecer!

Analista de Requisitos: Correto. E além desses usuários autorizados, existe algum acesso para usuário comum? Tipo um internauta, visitante, etc?

Cliente:  Não. Todo acesso só pode ser feito por usuário autorizado.

Analista de Requisitos: Compreendo. Então o usuário não logado só acessa a tela de login e nada mais?

Cliente: Isso

Analista de Requisitos: E depois de logado? Os usuários todos tem acesso às mesmas funcionalidades ou tem alguma diferenciação entre eles?

Cliente:  Então, nós temos o usuário administrador, que faz os cadastros de informação base do sistema, como empresas, clientes, contratos, segmentos, programas, grupos econômicos, centros de custo, unidades de negócio, fornecedores e regras de serviço. Temos o usuário do operacional que faz os lançamentos por cliente × período × regra de serviço. O usuário supervisor que valida o que o operacional faz e aprova os lançamentos. 

Analista de Requisitos: Certo. E além desses usuários, há outros também? Por exemplo, existem usuários de empresas parceiras ou provedores que serviço que precisam ter acesso ao sistema?

Cliente: Não. São só esses mesmos.

Analista de Requisitos: Nem mesmo algum vindo de outro software com o qual queiram integrar?

Cliente: Por agora não. A ideia é só termos o nosso sistema acessível para o nosso pessoal.

Analista de Requisitos: Entendi. Dentro dessa parte de usuários e considerando o que me falou sobre a segurança, digamos que um usuário não autorizado tente acessar o sistema. Como o sistema precisa se comportar?

Cliente: Ele não deve permitir o acesso! A ideia é o sistema ser 100% seguro!

Analista de Requisitos: Então, não existe sistema 100% seguro, então o que podemos fazer é melhorar o aparato de segurança para saber como lidar com as ameaças. Digamos por exemplo que um usuário malicioso tente acessar o sistema, mas sem saber os dados de acesso de qualquer usuário autorizado. Ele vai tentar usar combinações de usuário e senha para acessar o sistema. A maioria das tentativas vai falhar por mera questão de combinatória, mas digamos que ele consiga aquela chance de 1 em um milhão e acerte uma combinação de usuário/senha que funcione. Não seria interessante termos uma segunda camada de validação no sistema, como autenticação em dois fatores?

Cliente: Nós temos o login corporativo na empresa. Dá para usar esse login?

Analista de Requisitos: Com certeza! Isso simplifica o sistema, delegando a parte de validação de usuário/senha, etc para outro sistema e só recebendo no sistema usuários já validados dentro da rede corporativa. Esse login corporativo usa autenticação de dois fatores?

Cliente: Não. Precisa?

Analista de Requisitos: Depende de quão rígidas são as regras do login corporativo. Se ele demanda o usuário utilizar senha forte e realizar a troca regular da senha em um prazo razoável, já temos algum nível de confiabilidade nele. Se ele já tiver autenticação em dois fatores, então nem precisamos disso no sistema atual. Porém se não tiver e digamos que o SSO permita senhas não tão fortes assim, a autenticação de dois fatores adiciona uma camada de segurança ao sistema, o que ajuda a reduzir o problema que já tiveram antes de invasão, porque pensa comiga na situação que alguém consegue o usuário e senha do login corporativo. Além de todo o acesso que ele terá só por ter um usuário "válido" na rede corporativa, sem a autenticação de dois fatores no sistema, ele poderá acessar tudo como se fosse o usuário de fato. Porém, se obrigamos o usuário a fazer uma checagem adicional, usando um método físico que apenas o usuário verdadeiro deveria ter, então poderemos barrar esse tipo de problema. Isso não seria interessante?

Cliente: Com certeza. Acho que podemos adicionar esse login que está falando também.


##

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
