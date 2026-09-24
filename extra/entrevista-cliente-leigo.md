# Entrevista de Levantamento de Requisitos de Segurança — Network Billing Backend

## Ficha da entrevista

| Item | Descrição |
|------|-----------|
| **Data (fictícia)** | 14 de outubro de 2026, 14h às 15h30 |
| **Local** | Sala de reuniões da Gerência Financeira |
| **Cliente** | Márcia Andrade, gerente de Faturamento e Contas |
| **Analista** | Rafael Couto, engenheiro de software seguro |
| **Sistema** | Network Billing Backend, o sistema interno de faturamento da rede credenciada |
| **Objetivo** | Entender o processo de faturamento sob a ótica do negócio, explicar os conceitos de segurança envolvidos em linguagem acessível e transformar as preocupações da cliente em requisitos de segurança verificáveis |

---

## 1. Abertura

**Analista:** Boa tarde, Márcia. Obrigado por reservar esse tempo. Eu sou o Rafael e trabalho com segurança de software. Hoje eu quero entender como funciona o faturamento no seu dia a dia e descobrir o que pode dar errado, seja por um erro, seja por alguém agindo de má-fé. A conversa deve levar cerca de uma hora e meia.

**Cliente:** Boa tarde, Rafael. Vou logo avisando: eu entendo de contrato, de fechamento e de auditoria. De computador, sei usar o que me mandam usar. Se você falar muita sigla, vou te interromper.

**Analista:** Pode interromper à vontade, é justamente essa a ideia. Se eu não conseguir explicar algo de um jeito simples, o problema é meu, não seu.

**Cliente:** Combinado.

---

## 2. Entendendo o negócio

**Analista:** Para começar, me conta como é um mês típico para você e para a sua equipe.

**Cliente:** A gente fatura a rede credenciada. Cada cliente tem um contrato com regras de cobrança. Tem contrato de valor fixo, tem contrato em que a gente multiplica a quantidade de serviços por um preço, tem contrato que é um percentual e tem os de faixa: até tantos atendimentos é um valor, passou disso é outro. Durante o mês, os analistas da minha equipe fazem os lançamentos de cada cliente naquele período. Depois, alguém precisa aprovar.

**Analista:** Quem aprova?

**Cliente:** Eu ou um dos dois coordenadores. E aqui tem uma regra que talvez você não saiba: a aprovação não é só um clique. Quem aprova confere o lançamento contra o contrato e os anexos, que normalmente são relatórios de atendimento e notas. Se não bate, devolve para correção.

**Analista:** Isso é muito útil. Então existe um fluxo: lança, confere, aprova ou devolve. E depois da aprovação?

**Cliente:** Depois geramos a carga para o ERP, que é uma planilha que o sistema monta e que entra no sistema contábil da empresa. E todo mês tem o fechamento. O fechamento precisa estar pronto até o quinto dia útil do mês seguinte, porque a controladoria consolida tudo no sétimo. Se atrasar, atrasa a empresa inteira.

**Analista:** Então um sistema fora do ar no começo do mês é um problema sério para vocês.

**Cliente:** Seríssimo. Do dia primeiro ao quinto útil, o sistema não pode parar.

**Analista:** Anotado. Isso é uma preocupação de **disponibilidade**, ou seja, o sistema estar funcionando quando vocês precisam. Faz parte da segurança também, não é só "impedir hacker".

---

## 3. Quem pode fazer o quê

**Analista:** Hoje o sistema tem quatro perfis: Admin, Manager, Analyst e um perfil chamado "None", que é de quem ainda não recebeu acesso e só pode pedir acesso. Antes de falar deles, quero explicar duas palavras que vou usar bastante: **autenticação** e **autorização**.

**Cliente:** Não são a mesma coisa?

**Analista:** Parecem, mas não são. Pense no crachá da empresa. Quando você passa o crachá na portaria, o prédio confirma que você é a Márcia. Isso é autenticação: provar quem você é. Mas o seu crachá abre a sala do financeiro e não abre a sala dos servidores. Isso é autorização: decidir o que você pode fazer, depois de saber quem você é.

**Cliente:** Ah, entendi. Então o login é o crachá na portaria, e o perfil diz quais portas abrem.

**Analista:** Exatamente. E aqui entra um princípio que chamamos de **menor privilégio**: cada pessoa recebe só as chaves de que precisa para o trabalho dela, nenhuma a mais. No sistema, o perfil Analyst pode ver dados e gerar relatórios; quem aprova é o Manager.

**Cliente:** Espera, mas meus analistas fazem lançamentos. Eles não são só de visualizar.

**Analista:** Boa observação, e é exatamente o tipo de coisa que eu preciso ouvir. Vou registrar que precisamos confirmar se o perfil Analyst atual cobre o lançamento ou se falta um perfil de "lançador". Não quero que alguém receba perfil de Manager só para conseguir lançar, porque aí ele também poderia aprovar.

**Cliente:** E isso seria ruim, né?

**Analista:** Muito. Isso leva a outro conceito: **segregação de funções**. Na contabilidade vocês já conhecem isso, certo?

**Cliente:** Claro. Quem paga não é quem autoriza o pagamento. A auditoria externa pega no nosso pé com isso.

**Analista:** Pois então, no sistema é a mesma lógica. Quem fez o lançamento não pode ser a pessoa que aprova aquele lançamento, mesmo que ela tenha perfil de Manager. Se o sistema não impedir isso, um coordenador poderia lançar um valor inflado e aprovar ele mesmo.

**Cliente:** Isso me preocupa. E tem outra coisa: lançamentos acima de cinquenta mil reais, pela nossa política interna, precisam de duas aprovações. Hoje isso é controlado por e-mail.

**Analista:** Eu não sabia dessa regra. Isso vira um requisito: aprovação dupla para valores acima de um limite configurável, e o sistema precisa bloquear, não só avisar.

**Cliente:** E quando alguém sai de férias? Olha, sendo sincera, o pessoal passa o login para quem vai cobrir. É mais prático, senão o trabalho para.

**Analista:** Entendo por que acontece, e a intenção é boa. Mas deixa eu mostrar o problema. Se a Joana empresta o login dela para o Paulo e o Paulo aprova um lançamento errado, o que o sistema registra?

**Cliente:** Que foi a Joana.

**Analista:** Exatamente. A auditoria vai perguntar para a Joana, que estava na praia. Perdemos a **rastreabilidade**, que é saber quem realmente fez cada coisa, e a **responsabilização**, que é poder cobrar a pessoa certa. É como assinar um cheque em nome de outra pessoa com a autorização verbal dela: na prática, ninguém consegue provar nada depois.

**Cliente:** Pensando assim, é arriscado mesmo. Mas o trabalho não pode parar.

**Analista:** E não vai parar. O caminho certo é a substituição formal: durante as férias, o Paulo recebe temporariamente a permissão que precisa, com data para acabar. Tudo o que ele fizer fica no nome dele. Vou registrar como requisito.

---

## 4. Acesso e identidade

**Analista:** Agora vamos falar do login em si. Vocês entram com o usuário e senha da rede da empresa, correto?

**Cliente:** Sim, o mesmo do e-mail. E por isso eu acho que está tranquilo. Tem senha, então está seguro.

**Analista:** A senha é importante, mas ela sozinha é uma proteção fraca. Vou te dar três exemplos. Primeiro: senhas vazam, por e-mail falso, por alguém que anota num post-it, por uma pessoa que usa a mesma senha num site que foi invadido. Segundo: alguém pode tentar adivinhar a senha, testando milhares de combinações. Terceiro: se a senha é a mesma do e-mail, quem conseguir a senha do e-mail entra também no faturamento.

**Cliente:** Nossa, esse terceiro eu nunca tinha pensado.

**Analista:** Para o segundo caso, o de adivinhação, que chamamos de **ataque de força bruta**, o sistema já tem uma proteção chamada **limite de requisições**. Pense em um cofre que trava depois de algumas tentativas erradas. No sistema, a tela de login aceita no máximo 10 tentativas por minuto vindas do mesmo endereço de rede. Isso deixa a adivinhação lenta demais para compensar.

**Cliente:** E para o primeiro caso, o da senha vazada?

**Analista:** Para isso o ideal é um **segundo fator de autenticação**: além da senha, a pessoa confirma o acesso com um código no celular. É como o banco pedir o código do token além da senha. Mesmo que roubem a senha, falta o celular. Como o login é o corporativo, isso pode ser configurado no próprio serviço de login da empresa. Vou registrar como requisito para quem aprova e para os administradores, pelo menos.

**Cliente:** Faz sentido. E depois que eu entro, o sistema fica me pedindo senha toda hora?

**Analista:** Não. Depois do login, o sistema te entrega uma espécie de pulseira de evento, chamada **token**. É como a pulseira de um show: você mostrou o ingresso na entrada uma vez, e depois só mostra a pulseira para circular. O sistema guarda essa pulseira num lugar do navegador que outros programas da página não conseguem ler, o que protege contra alguns tipos de roubo.

**Cliente:** E alguém não pode falsificar essa pulseira?

**Analista:** Ótima pergunta. A pulseira tem um carimbo, uma espécie de assinatura, feito com uma chave secreta que só o servidor conhece. Se alguém tentar fabricar uma pulseira dizendo "eu sou administrador", o carimbo não confere e o sistema recusa. O ponto crítico é que essa chave secreta nunca pode vazar. Se vazar, é como alguém roubar o carimbo oficial do cartório: ele passa a fabricar documentos que parecem legítimos. Poderia criar uma pulseira de administrador sem nem ter conta.

**Cliente:** E onde fica esse carimbo?

**Analista:** Hoje ele fica numa configuração do servidor, fora do código do programa, o que é o correto. O que eu vou pedir é: poucas pessoas com acesso a ele, troca periódica e um procedimento de emergência caso haja suspeita de vazamento.

**Cliente:** E quando alguém é desligado da empresa?

**Analista:** Essa é uma preocupação importante. Como vocês funcionam hoje?

**Cliente:** O RH avisa a TI, e a TI bloqueia o usuário da rede. Às vezes demora uns dias.

**Analista:** Esses dias são uma janela de risco. Uma pessoa desligada e insatisfeita, com acesso ainda ativo, é o que chamamos de **ameaça interna**. Ela conhece o processo, sabe onde mexer. O requisito é: o acesso ao faturamento precisa ser bloqueado no mesmo dia do desligamento, e as sessões abertas dela precisam ser encerradas, não só o login bloqueado.

**Cliente:** Mas por quê? Se bloqueou o login, ela não entra.

**Analista:** Porque a pulseira que ela já recebeu continua valendo até expirar. Se ela estava logada, pode continuar usando por um tempo. Por isso pedimos que as pulseiras tenham validade curta e que exista uma forma de cancelar todas as de um usuário.

**Cliente:** Não imaginava isso.

**Analista:** Uma curiosidade, que costuma gerar dúvida: quando uma pessoa tem senha cadastrada direto no sistema, nem o administrador consegue ver essa senha.

**Cliente:** Como assim? Então se eu esquecer, ninguém consegue me dizer qual era?

**Analista:** Exatamente, e isso é proposital. O sistema não guarda a senha, guarda um **hash** dela. Pense num moedor de carne: você coloca a carne e sai carne moída, mas não dá para transformar a carne moída de volta no bife. Quando você digita a senha, o sistema passa pelo moedor e compara com o que está guardado. Se alguém roubar o banco de dados, leva só a carne moída.

**Cliente:** Gostei do exemplo. Então, se eu esquecer, o jeito é criar uma senha nova.

**Analista:** Isso mesmo.

---

## 5. Integridade dos valores

**Analista:** Vamos falar do que mais te preocupa, eu imagino: os valores.

**Cliente:** É. O meu pesadelo é fraude, alguém colocar um valor maior do que o contrato permite, ou mudar o contrato para o cálculo dar mais.

**Analista:** O sistema tem uma proteção importante aqui: o cálculo é feito no servidor. Significa que a tela do analista não manda o valor pronto. Ela manda os dados, como a quantidade de atendimentos, e o servidor aplica a regra do contrato.

**Cliente:** E qual a diferença? O resultado não é o mesmo?

**Analista:** Pense num caixa de supermercado. Se o cliente pudesse dizer "essa compra deu vinte reais" e o caixa aceitasse, seria um problema. O certo é o caixa passar cada produto e o sistema dele somar. A tela do usuário está no computador dele, e uma pessoa com conhecimento técnico consegue alterar o que a tela envia. Se o servidor recalcula sempre, essa alteração não adianta.

**Cliente:** Entendi. Mas e se a pessoa mudar o contrato?

**Analista:** Aí está o outro ponto crítico. Os cadastros de contrato definem os valores, então quem altera contrato tem, na prática, poder sobre quanto se cobra. Quem pode alterar um contrato hoje?

**Cliente:** Deveriam ser só os administradores do sistema, com base em documento assinado pelo comercial.

**Analista:** Então vamos registrar: alteração de regra contratual só por perfil autorizado, com registro de quem alterou, quando, valor anterior e valor novo, e idealmente com anexo do documento que justificou a mudança.

**Cliente:** E se um lançamento for aprovado errado? Hoje, quando dá problema, a gente apaga e refaz. É mais rápido.

**Analista:** Esse é um ponto em que eu vou discordar de você, com todo o respeito. Você trabalha com contabilidade: quando um lançamento no livro-caixa está errado, vocês apagam?

**Cliente:** Não, claro que não. Faz o estorno e lança de novo.

**Analista:** Exatamente. O sistema precisa funcionar como um livro-caixa escrito a caneta. O fechamento mensal no sistema já funciona assim: os registros só podem ser **acrescentados**, nunca editados ou apagados. Chamamos isso de *append-only*. Para corrigir, você faz um novo registro que compensa o anterior. Se o sistema permitir apagar, quem quiser esconder uma fraude simplesmente apaga as pistas.

**Cliente:** Falando assim, com a palavra estorno, ficou óbvio. Eu só não tinha associado ao sistema.

**Analista:** E isso vale para depois que o mês fecha: um fechamento concluído não pode ser reaberto por qualquer pessoa. Se precisar de ajuste, é um lançamento de ajuste no mês seguinte ou uma reabertura formal, com aprovação e registro.

**Cliente:** Isso inclusive é o que a auditoria externa exige. Mês fechado é mês fechado.

---

## 6. Rastreabilidade e auditoria

**Analista:** O sistema já registra automaticamente toda alteração com o nome do usuário. Eu preciso entender, do lado do negócio: por quanto tempo esses registros precisam ser guardados?

**Cliente:** Pela área fiscal, no mínimo cinco anos. Nossa política interna fala em dez para tudo que é contábil.

**Analista:** Então vamos adotar dez anos para a trilha de auditoria do faturamento. E quem pode consultar esses registros?

**Cliente:** Eu, a controladoria e a auditoria externa, quando solicitar.

**Analista:** Perfeito. E aqui tem um detalhe de segurança: a trilha de auditoria precisa ser protegida até dos administradores. Se o administrador puder apagar o registro do que ele mesmo fez, a trilha perde valor.

**Cliente:** É o mesmo raciocínio do estorno.

**Analista:** Exatamente o mesmo. Você está pegando rápido.

**Cliente:** Tem uma coisa que eu quero perguntar. Nos cadastros tem nome de responsável, CPF, telefone, e-mail. Isso entra em LGPD?

**Analista:** Entra. A **LGPD** é a lei que protege dados pessoais, ou seja, qualquer informação que identifique uma pessoa física. Mesmo sendo um sistema de empresa para empresa, os responsáveis e contatos são pessoas. O que a lei pede, em resumo, é: coletar só o necessário, proteger bem, controlar quem vê e conseguir responder se alguém perguntar o que vocês guardam sobre ele.

**Cliente:** E a gente precisa do CPF mesmo?

**Analista:** Essa é a pergunta certa, e quem responde é você. Se não for necessário para o faturamento, o melhor dado pessoal é o que não se guarda.

**Cliente:** Vou verificar com o jurídico. Acho que só precisamos do CNPJ e de um contato.

**Analista:** E um último ponto: os dashboards e relatórios não devem exibir dados pessoais para quem não precisa deles. Um relatório de KPI não precisa mostrar CPF.

---

## 7. Arquivos e integrações

**Analista:** Vocês anexam arquivos aos lançamentos. Que tipos de arquivo?

**Cliente:** PDF de nota, planilha de atendimento, às vezes foto de documento assinado.

**Analista:** O sistema hoje verifica o tipo e a extensão do arquivo e limita o tamanho a 25 megabytes. Sabe por que isso importa?

**Cliente:** Para não encher o servidor?

**Analista:** Também, mas o principal é outro. Um arquivo pode ser um cavalo de Troia: parece um PDF inofensivo, mas é um programa disfarçado. Se alguém da sua equipe abrir, pode infectar o computador. É como receber uma encomenda: não basta a etiqueta dizer "livros", tem que conferir o que tem dentro.

**Cliente:** E o sistema confere?

**Analista:** Confere a etiqueta e o formato. Vou recomendar também passar os arquivos por um antivírus antes de ficarem disponíveis para download, porque a conferência de tipo sozinha não pega tudo.

**Cliente:** E a planilha do ERP? Ela sai do sistema e vai para o contábil.

**Analista:** Essa planilha é valiosa, porque ela vira lançamento contábil. Alguém consegue editar a planilha entre o momento em que ela sai do sistema e o momento em que entra no ERP?

**Cliente:** Hmm. Ela é baixada por um coordenador e enviada. Tecnicamente, dá para abrir e mexer.

**Analista:** Então existe uma brecha. O requisito é que o arquivo gerado tenha uma forma de conferência de integridade, como um código que muda se o conteúdo for alterado, e que o ERP ou quem importa confira esse código. Também vamos registrar quem baixou cada carga e quando.

**Cliente:** Nunca tinha pensado nisso. E o Oracle antigo? O sistema busca dados dele.

**Analista:** O sistema consulta o Oracle, que é o banco de dados antigo, para trazer a rede credenciada e os indicadores. Aí existe um risco chamado **injeção de SQL**.

**Cliente:** O que é isso?

**Analista:** SQL é a língua que o sistema usa para conversar com o banco de dados. Imagine um formulário em papel com um campo "Nome do cliente". Uma pessoa mal-intencionada, em vez de escrever o nome, escreve: "e também entregue a lista de todos os contratos". Se quem lê o formulário obedece tudo o que está escrito, ele entrega a lista. A injeção de SQL é isso: alguém escreve uma ordem onde deveria ter um dado.

**Cliente:** E como se evita?

**Analista:** O sistema precisa tratar tudo o que vem do usuário como dado, nunca como ordem. Tecnicamente, usamos consultas "parametrizadas", em que o campo do formulário nunca é lido como instrução. Vou pedir uma revisão de todas as consultas ao Oracle, e também que o usuário que o sistema usa para acessar o Oracle só tenha permissão de leitura. Assim, mesmo se alguém conseguir injetar algo, não consegue alterar nada.

**Cliente:** É o menor privilégio de novo.

**Analista:** Exatamente. A mesma ideia aparece em todo lugar.

---

## 8. Cenários "e se...?"

**Analista:** Agora quero fazer um exercício. Vou descrever três situações e quero saber qual seria o impacto para o negócio.

**Cliente:** Pode mandar.

**Analista:** Primeiro cenário: alguém de fora descobre a senha de um dos seus coordenadores e entra no sistema no dia 3, em pleno fechamento.

**Cliente:** Ele poderia aprovar lançamentos, certo? Se aprovar valores errados e isso for para o ERP, a controladoria fecha o mês com dado errado. Corrigir depois é retrabalho, e se a auditoria pegar, vira ressalva no balanço.

**Analista:** E se o segundo fator de autenticação estiver ativo?

**Cliente:** Aí ele fica só com a senha e não entra. Agora entendi por que você insistiu.

**Analista:** Segundo cenário: a chave secreta que assina as pulseiras de acesso vaza, por exemplo porque alguém copiou a configuração do servidor para um lugar inseguro.

**Cliente:** Pelo que você explicou, qualquer um vira administrador. Isso seria o pior caso, não é? Ele poderia mudar contrato, aprovar, gerar carga.

**Analista:** É um dos piores, sim. Por isso a chave precisa de troca imediata em caso de suspeita, o que invalida todas as pulseiras existentes. Todo mundo teria que fazer login de novo.

**Cliente:** Prefiro todo mundo logando de novo do que um administrador falso.

**Analista:** Terceiro cenário: um analista insatisfeito, antes de pedir demissão, altera a regra de um contrato de "percentual de 3%" para "percentual de 30%".

**Cliente:** Primeiro que ele não deveria conseguir alterar contrato. Segundo, mesmo que alterasse, o valor ia sair absurdo e o aprovador ia notar... espero.

**Analista:** Você tocou num ponto importante: "espero". A conferência humana ajuda, mas cansaço e volume de trabalho fazem erros passarem. Por isso usamos várias camadas: o perfil não permite alterar contrato, a alteração fica registrada, o aprovador confere, e podemos criar um alerta quando um valor fugir muito da média do cliente. Chamamos isso de **defesa em profundidade**.

**Cliente:** Como um prédio com portaria, catraca, câmera e segurança no andar.

**Analista:** Perfeito, melhor do que eu teria explicado. E isso também responde a uma coisa que você disse no começo: nenhuma camada é 100% segura. Por isso não confiamos em uma só.

**Cliente:** Eu cheguei a achar que, por ser sistema interno, não precisava de tudo isso. Só funcionário acessa.

**Analista:** É um pensamento comum. Mas dois dos três cenários que discutimos começaram com funcionário ou com a conta de um funcionário. O "interno" diminui a exposição, mas não elimina o risco.

**Cliente:** É, os números falam por si.

---

## 9. Encerramento

**Analista:** Vou resumir o que combinamos, em linguagem simples, e você me diz se esqueci algo.

1. Cada pessoa usa o próprio login. Nas férias, a substituição é formal e temporária.
2. Quem lança não aprova o próprio lançamento. Acima de cinquenta mil reais, são duas aprovações.
3. Coordenadores e administradores usam segundo fator de autenticação.
4. Pessoa desligada tem o acesso cortado no mesmo dia, incluindo as sessões abertas.
5. Nada se apaga: correção é feita por estorno ou ajuste, e mês fechado só reabre com aprovação formal.
6. Alteração de contrato é restrita, registrada e com documento anexo.
7. A trilha de auditoria é guardada por dez anos e nem administrador consegue apagá-la.
8. Guardamos só os dados pessoais necessários, e os relatórios não os expõem sem necessidade.
9. Arquivos anexados passam por antivírus, e a carga do ERP tem conferência de integridade.
10. As consultas ao Oracle são revisadas contra injeção de SQL, com acesso somente leitura.
11. O sistema precisa estar disponível, principalmente entre o primeiro e o quinto dia útil.

**Cliente:** Está completo. Só acrescentaria o alerta de valor fora da média, que você comentou. Esse eu quero.

**Analista:** Anotado. Vou transformar tudo isso num documento de requisitos e te enviar para validação. Obrigado, Márcia. Suas regras de negócio ajudaram muito.

**Cliente:** Eu que agradeço. Saio daqui entendendo bem mais do que quando entrei.

---

## Glossário para leigos

| Termo | Explicação simples | Analogia usada |
|-------|--------------------|----------------|
| Autenticação | Provar quem você é para o sistema | Passar o crachá na portaria |
| Autorização | Definir o que você pode fazer depois de identificado | Quais salas o crachá abre |
| Menor privilégio | Cada pessoa recebe apenas as permissões necessárias ao seu trabalho | Só as chaves de que você precisa |
| Segregação de funções | Tarefas críticas divididas entre pessoas diferentes | Quem paga não autoriza o pagamento |
| Rastreabilidade | Saber quem fez cada ação e quando | Cheque assinado pela própria pessoa |
| Força bruta | Tentar adivinhar uma senha testando muitas combinações | Tentar todas as combinações de um cofre |
| Limite de requisições (*rate limiting*) | Limitar quantas tentativas podem ser feitas por minuto | Cofre que trava após tentativas erradas |
| Segundo fator de autenticação | Confirmação extra, além da senha | Código do token do banco |
| Token (JWT) | Comprovante de acesso entregue após o login | Pulseira de show |
| Chave secreta (JWT_SECRET) | Chave que assina os tokens e impede falsificação | Carimbo oficial do cartório |
| Hash de senha | Transformação irreversível da senha antes de guardar | Moedor de carne |
| Ameaça interna | Risco vindo de quem já tem ou teve acesso legítimo | Funcionário desligado com crachá ativo |
| Append-only | Registros que só podem ser acrescentados, nunca editados ou apagados | Livro-caixa escrito a caneta, com estorno |
| Cálculo no servidor | O sistema calcula o valor em vez de aceitar o valor enviado pela tela | Caixa de supermercado que soma os produtos |
| Validação de upload | Conferir o tipo e o conteúdo de arquivos enviados | Conferir o que tem dentro da encomenda |
| Injeção de SQL | Inserir uma ordem onde o sistema espera um dado | Formulário em que alguém escreve uma ordem no campo "nome" |
| Defesa em profundidade | Várias camadas de proteção independentes | Portaria, catraca, câmera e segurança no andar |
| LGPD | Lei que protege dados de pessoas físicas | O melhor dado pessoal é o que não se guarda |
| Disponibilidade | O sistema funcionar quando é necessário | Sistema no ar durante o fechamento |

---

## Requisitos de segurança levantados

| ID | Requisito | Origem na conversa | Prioridade | Como verificar |
|----|-----------|--------------------|------------|----------------|
| RS-01 | O sistema deve impedir que o autor de um lançamento o aprove | Medo de fraude; segregação de funções exigida pela auditoria | Alta | Teste automatizado: usuário Manager tenta aprovar o próprio lançamento e recebe erro |
| RS-02 | Lançamentos acima de um limite configurável (atualmente R$ 50.000) devem exigir duas aprovações de usuários distintos | Regra interna trazida pela cliente | Alta | Teste: lançamento acima do limite permanece pendente após a primeira aprovação |
| RS-03 | Deve existir um perfil ou permissão para lançar que não inclua aprovar | Analistas lançam, mas não devem aprovar | Alta | Revisão da matriz de permissões e teste por perfil |
| RS-04 | O sistema deve permitir delegação temporária de permissões, com data de expiração e registro na auditoria | Compartilhamento de login nas férias | Média | Teste: delegação expira na data e as ações ficam registradas no nome do substituto |
| RS-05 | Usuários com perfil Manager e Admin devem usar segundo fator de autenticação | "Tem senha, então está seguro"; cenário de senha vazada | Alta | Verificar a política no provedor de identidade corporativo; teste de login sem o segundo fator |
| RS-06 | O acesso de funcionário desligado deve ser revogado no mesmo dia, com encerramento das sessões ativas | Demora entre o RH e a TI | Alta | Teste: após a revogação, um token emitido antes deixa de ser aceito |
| RS-07 | Os tokens devem ter validade curta e deve existir revogação por usuário | Pulseira que continua valendo após o bloqueio | Alta | Inspeção da configuração de expiração; teste de revogação |
| RS-08 | O JWT_SECRET deve ter acesso restrito, troca periódica e procedimento de troca emergencial documentado | Cenário de vazamento da chave | Alta | Revisão do procedimento; exercício simulado de troca da chave |
| RS-09 | Lançamentos aprovados e fechamentos não podem ser apagados ou editados; correções ocorrem por estorno ou ajuste | "A gente apaga e refaz" | Alta | Teste: tentativa de excluir ou editar um registro aprovado é negada |
| RS-10 | A reabertura de mês fechado exige aprovação formal e registro | "Mês fechado é mês fechado" | Alta | Teste: reabertura sem aprovação é negada; reabertura aprovada aparece na auditoria |
| RS-11 | Alterações de regras contratuais devem ser restritas a perfil autorizado e registrar valor anterior, valor novo, autor, data e documento anexo | Medo de alteração de contrato para inflar valores | Alta | Teste por perfil; inspeção do registro de auditoria após a alteração |
| RS-12 | O valor faturado deve ser sempre calculado no servidor, ignorando valores enviados pelo cliente | Integridade dos valores | Alta | Teste: requisição com valor adulterado resulta no valor correto calculado |
| RS-13 | A trilha de auditoria deve ser mantida por 10 anos e ser imutável, inclusive para administradores | Exigência fiscal e política interna | Alta | Teste de exclusão pelo Admin negado; verificação da política de retenção |
| RS-14 | O acesso à trilha de auditoria deve ser restrito à gerência, à controladoria e à auditoria | Quem pode ver os registros | Média | Teste por perfil |
| RS-15 | Os dados pessoais devem ser minimizados, e relatórios e dashboards não devem exibi-los sem necessidade | Dúvida sobre CPF e LGPD | Média | Revisão dos cadastros com o jurídico; inspeção dos relatórios |
| RS-16 | Os anexos devem passar por antivírus, além da validação de tipo, extensão e tamanho já existente | Arquivo malicioso disfarçado | Média | Teste com arquivo de teste de antivírus (EICAR) |
| RS-17 | As cargas do ERP devem ter verificação de integridade, e cada download deve ser registrado | Planilha pode ser editada antes da importação | Alta | Alterar a planilha e verificar que a importação é rejeitada; conferir o registro de download |
| RS-18 | Todas as consultas ao Oracle devem ser parametrizadas, e o usuário de conexão deve ter permissão somente de leitura | Risco de injeção de SQL | Alta | Revisão de código e varredura de segurança; verificar as permissões do usuário no Oracle |
| RS-19 | O sistema deve gerar alerta para lançamentos com valor muito acima da média histórica do cliente | Cenário do analista insatisfeito; pedido da cliente | Média | Teste com lançamento fora do padrão e verificação do alerta |
| RS-20 | O sistema deve ter alta disponibilidade entre o 1º e o 5º dia útil do mês | Prazo de fechamento | Alta | Monitoramento de disponibilidade e plano de contingência testado |

---

## Ameaças identificadas (STRIDE)

- **Falsificação de identidade (Spoofing):** uso de senha vazada de um coordenador; forja de token de administrador após o vazamento do JWT_SECRET; login compartilhado nas férias.
- **Adulteração (Tampering):** alteração de regra contratual para inflar valores; envio de valor adulterado pela tela; edição da planilha do ERP antes da importação; injeção de SQL nas consultas ao Oracle.
- **Repúdio (Repudiation):** usuário nega ter aprovado um lançamento feito com o login de outra pessoa; exclusão de lançamentos para apagar evidências.
- **Divulgação de informação (Information Disclosure):** exposição de dados pessoais (CPF, telefone) em relatórios; extração de dados via injeção de SQL.
- **Negação de serviço (Denial of Service):** indisponibilidade do sistema durante o fechamento; excesso de requisições ou uploads muito grandes.
- **Elevação de privilégio (Elevation of Privilege):** Manager aprovando o próprio lançamento; usuário recebendo perfil acima do necessário para conseguir lançar; ex-funcionário com sessão ainda ativa.
