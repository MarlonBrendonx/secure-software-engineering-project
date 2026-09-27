# Etapa 1 — Casos de abuso e considerações finais

Este documento detalha os casos de abuso do sistema e apresenta a síntese
final da análise. Ele complementa a
[modelagem de ameaças STRIDE](etapa-1-ameacas-stride.md) e a
[identificação do sistema](etapa-1-identificacao-sistema.md), que definem os
ativos (A1–A15) e as ameaças (T01–T23) referenciados aqui.

Os casos de abuso descrevem formas pelas quais um agente mal intencionado, um
usuário indevido ou até um usuário legítimo poderia usar o sistema para causar
dano e prejuízos. Cada caso de uso segue a seguinte estrutura:

- **Identificador:** código único de identificação do caso.
- **Título:** nome descritivo do caso.
- **Ator:** entidade que executa ou participa da ação.
- **Objetivo:** finalidade do caso de uso.
- **Condições necessárias:** pré-requisitos para sua execução.
- **Sequência de ações:** etapas que compõem o fluxo de execução.
- **Impacto esperado:** consequências potenciais para o sistema.
- **Relação com o STRIDE:** categoria(s) de ameaça associada(s), conforme o modelo STRIDE.

## Casos de abuso

### CA01 — Alteração ou remoção de lançamentos

- **Ator:** analista legítimo mal intencionado , ou usuário com acesso indevido a
  uma conta com permissão de escrita.
- **Objetivo:** alterar ou remover lançamentos financeiros para mudar o valor
  faturado a um cliente em benefício próprio ou de terceiros.
- **Condições necessárias:** o ator tem sessão válida com permissão,
  o controle de acesso não impedem a edição do
  lançamento no estado em que ele se encontra.
- **Sequência de ações:**
  1. O ator autentica-se no sistema com uma conta com permissão de gestor ou admin.
  2. O ator localiza o lançamento alvo na listagem por período.
  3. O ator altera o valor, o período ou a regra do lançamento, ou o remove.
  4. O valor adulterado segue no fluxo e chega ao ERP como se fosse legítimo.
- **Impacto esperado:** cobrança incorreta ao cliente, prejuízo financeiro
  direto e perda de confiança no valor apurado pelo sistema.
- **Categorias STRIDE:** Tampering (T01).

### CA02 — Captura de usuário privilegiado via SSO

- **Ator:** atacante externo ou interno que busca assumir o controle de uma
  conta com privilégios (`admin` ou `gestor`).
- **Objetivo:** obter uma sessão com privilégios maiores que os seus para
  operar transições de status e rotas administrativas.
- **Condições necessárias:** o atacante consegue capturar credenciais, token ou
  sessão de SSO de um usuário privilegiado (phishing, sessão vazada).
- **Sequência de ações:**
  1. O atacante obtém credenciais ou token de SSO de um usuário privilegiado.
  2. O atacante usa o token para autenticar-se no sistema.
  3. O sistema reconhece a conta como legítima e concede o perfil associado.
  4. O atacante executa ações restritas ao perfil capturado (aprovar, reprovar,
     remover).
- **Impacto esperado:** aprovação ou reprovação indevida de lançamentos,
  execução de rotas administrativas e possibilidade de encobrir atividade
  ilícita sob a identidade da vítima.
- **Categorias STRIDE:** Spoofing e Elevation of Privilege (T02).

### CA03 — Acesso não autorizado a dados restritos

- **Ator:** usuário sem permissão adequada, ou atacante com conta capturada, ou
  agente com acesso direto a um componente interno.
- **Objetivo:** ler dados que o seu perfil não deveria acessar, lançamentos,
  anexos, CNPJs, e-mails de aprovadores e anexos fora do controle da aplicação.
- **Condições necessárias:** falha ou ausência de verificação de autorização em
  uma rota, endpoint de anexo, consulta de dados ou URL de storage.
- **Sequência de ações:**
  1. O ator obtém acesso ao sistema (conta própria sem permissão, conta
     capturada ou acesso direto a um componente).
  2. O ator requisita um recurso restrito ao seu perfil.
  3. A verificação de autorização falha ou está ausente.
  4. O ator lê ou copia o dado restrito.
- **Impacto esperado:** exposição de valores financeiros, dados de negócio,
  CNPJs e informações pessoais, base para vazamento (CA04) e para fraude.
- **Categorias STRIDE:** Elevation of Privilege (T03, T07, T09, T11, T19).

### CA04 — Vazamento de informações críticas

- **Ator:** usuário legítimo agindo de forma mal intencionada, atacante com conta capturada, ou
  agente com acesso direto a dados ou secrets.
- **Objetivo:** extrair e divulgar dados sensíveis do sistema para terceiros, como:
  concorrentes, criminosos ou o próprio benefício.
- **Condições necessárias:** o ator já tem acesso de leitura aos dados (por
  permissão, por conta capturada ou por CA03) e não há controle que impeça a
  extração em volume.
- **Sequência de ações:**
  1. O ator acessa lançamentos, anexos, CNPJs, e-mails de aprovadores, segredos
     ou dados de faturamento.
  2. O ator exporta ou copia os dados.
  3. O ator transmite os dados para fora do ambiente corporativo.
- **Impacto esperado:** perda de propriedade intelectual e de dados de
  terceiros, exposição de pessoas chave a phishing e recrutamento, risco de
  processos judiciais por vazamento e dano reputacional a empresa.
- **Categorias STRIDE:** Information Disclosure (T04, T08, T10, T12, T15, T17,
  T22).

### CA05 — Remoção da timeline de auditoria

- **Ator:** usuário legítimo agindo de má fé, ou atacante que quer apagar o
  próprio rastro no sistema.
- **Objetivo:** eliminar ou corromper a timeline de transições para impedir a
  identificação de quem fez o quê.
- **Condições necessárias:** o ator tem acesso a uma operação capaz de remover
  ou alterar registros de auditoria, ou consegue agir sobre o armazenamento da
  timeline.
- **Sequência de ações:**
  1. O ator executa ações indevidas no sistema (por exemplo, aprovações
     irregulares).
  2. O ator remove ou corrompe os registros da timeline correspondentes.
  3. A trilha que ligaria o ator às ações desaparece.
- **Impacto esperado:** perda da capacidade de auditoria e de contestação,
  atividades ilícitas ficam sem prova de autoria e sem responsabilização.
- **Categorias STRIDE:** Repudiation (T05).

### CA06 — Alteração de regras de serviço

- **Ator:** usuário com permissão de escrita sobre serviços, ou
  atacante com conta capturada.
- **Objetivo:** alterar regras de serviço ou faixas para que todo valor
  calculado a partir delas fique errado de forma silenciosa.
- **Condições necessárias:** o ator tem permissão para criar, alterar ou
  excluir serviços, a alteração em uma regra propaga-se nos cálculos futuros.
- **Sequência de ações:**
  1. O ator acessa a funcionalidade de gestão de serviços.
  2. O ator altera uma regra de serviço ou uma faixa de cálculo.
  3. Os próximos lançamentos passam a ser calculados sobre a regra adulterada.
  4. O valor incorreto se propaga sem alertar os usuários.
- **Impacto esperado:** faturamento sistematicamente errado em escala, difícil
  de detectar, com impacto financeiro amplo
- **Categorias STRIDE:** Tampering (T06).

### CA07 — Adulteração do motor de cálculo

- **Ator:** agente com acesso ao código ou ao pipeline de entrega (insider com
  acesso ao repositório, ou atacante que comprometeu a cadeia de build).
- **Objetivo:** alterar os módulos responsáveis pelo cálculo de valores para
  faturar errado de forma intencional.
- **Condições necessárias:** o ator consegue introduzir uma alteração no código
  do motor de cálculo que chega a produção sem ser detectada em revisão ou
  testes.
- **Sequência de ações:**
  1. O ator modifica o código de cálculo (valor fixo, variável, multiplicação,
     porcentagem ou faixas).
  2. A alteração passa pela entrega sem detecção.
  3. Todos os lançamentos que usam o trecho afetado são calculados de forma
     errada.
- **Impacto esperado:** faturamento incorreto em escala a partir do núcleo do
  sistema, com impacto financeiro grave e difícil rastreio da causa.
- **Categorias STRIDE:** Tampering (T13).

### CA08 — Sobrecarga do fluxo de autorização

- **Ator:** atacante interno ou externo que consiga disparar requisições em
  volume contra a máquina de estados de aprovação.
- **Objetivo:** sobrecarregar a máquina de estados e seus guards de autorização
  para impedir o fluxo de aprovação de lançamentos.
- **Condições necessárias:** o ator consegue enviar requisições em volume às
  transições de status, sobrecarregando o endpoint e impossibilitante as aprovações
- **Sequência de ações:**
  1. O ator dispara um volume alto de requisições de transição de status.
  2. Os guards de autorização e a máquina de estados ficam saturados.
  3. Requisições legítimas de aprovação deixam de ser processadas.
- **Impacto esperado:** paralisação do fluxo de aprovação, atraso no
  faturamento e risco de operações incompletas sob sobrecarga.
- **Categorias STRIDE:** Denial of Service (T14).

### CA09 — Acesso não autorizado por meio de token de autenticação vazado

- **Ator:** atacante de posse do `JWT_SECRET` vazado.
- **Objetivo:** forjar tokens válidos para impersonar qualquer usuário,
  inclusive com papel de `admin`.
- **Condições necessárias:** o `JWT_SECRET` foi exposto (repositório, log,
  variável de ambiente ou vazamento de configuração).
- **Sequência de ações:**
  1. O atacante obtém o `JWT_SECRET`.
  2. O atacante gera um token assinado com o perfil desejado.
  3. O atacante apresenta o token forjado ao sistema.
  4. O sistema aceita o token como legítimo e concede o acesso.
- **Impacto esperado:** acesso total ao sistema sob identidade forjada,
  habilitando todos os demais abusos (acesso indevido, vazamento, alteração).
- **Categorias STRIDE:** Spoofing (T16).

### CA10 — Requisições internas forjadas com chave de callback vazada

- **Ator:** código ou serviço malicioso de posse do `CELERY_CALLBACK_SECRET` que é
  responsável pro retornos de processamentos asíncronos
- **Objetivo:** forjar chamadas de callback internas para injetar operações
  falsas no sistema.
- **Condições necessárias:** o `CELERY_CALLBACK_SECRET` foi exposto, a chave é a
  única barreira de validação dos callbacks internos.
- **Sequência de ações:**
  1. O ator obtém o `CELERY_CALLBACK_SECRET`.
  2. O ator monta requisições de callback assinadas com a chave.
  3. O sistema aceita as chamadas como internas e legítimas.
  4. O ator injeta operações ou estados falsos no fluxo.
- **Impacto esperado:** operações internas forjadas, corrupção de estado do
  processamento e execução de ações que deveriam ser exclusivas de componentes
  internos.
- **Categorias STRIDE:** Spoofing (T18).

### CA11 — Indisponibilidade do banco de dados

- **Ator:** atacante interno ou externo capaz de alcançar e sobrecarregar o
  PostgreSQL, ou de atacar a infraestrutura.
- **Objetivo:** derrubar ou saturar o banco de dados para deixar o sistema
  inteiro inoperante.
- **Condições necessárias:** o ator consegue gerar carga suficiente sobre o
  banco ou atingir a infraestrutura que o sustenta.
- **Sequência de ações:**
  1. O ator gera carga excessiva ou ataca a infraestrutura do banco.
  2. O PostgreSQL fica indisponível ou lento demais para responder.
  3. As funcionalidades que dependem do banco param.
- **Impacto esperado:** sistema inteiro inoperante, prejuízo por não
  funcionamento e risco de operações incompletas ou dados inconsistentes durante
  a sobrecarga.
- **Categorias STRIDE:** Denial of Service (T20).

### CA12 — Envio de e-mails maliciosos em nome da empresa

- **Ator:** atacante de posse do `EMAIL_SERVICE_API_KEY` vazado.
- **Objetivo:** enviar e-mails em nome da empresa para aplicar phishing ou
  spoofing de cobrança contra clientes e aprovadores.
- **Condições necessárias:** a chave do serviço de e-mail foi exposta, ela
  permite enviar mensagens como remetente legítimo da empresa.
- **Sequência de ações:**
  1. O atacante obtém o `EMAIL_SERVICE_API_KEY`.
  2. O atacante usa a chave para enviar e-mails pelo serviço.
  3. As mensagens chegam às vítimas como se fossem da empresa.
  4. As vítimas confiam no remetente e agem sobre o conteúdo malicioso.
- **Impacto esperado:** phishing e fraude de cobrança contra clientes,
  comprometimento de aprovadores e dano reputacional a empresa
- **Categorias STRIDE:** Spoofing (T21)

### CA13 — Sobrecarga do EventBus WebSocket

- **Ator:** Atacante capaz de estabelecer conexões ou enviar um grande volume de eventos pelo EventBus WebSocket.
- **Objetivo:** Sobrecarregar o EventBus e impedir que as notificações de faturamento sejam processadas e entregues em tempo real.
- **Condições necessárias:** O atacante consegue estabelecer conexões, inscrever-se em canais ou publicar eventos em grande volume. Além disso, o sistema não possui mecanismos suficientes de controle de acesso aos canais, limitação de requisições ou proteção contra excesso de mensagens.
- **Sequência de ações:**
  1. O atacante abre diversas conexões WebSocket ou começa a enviar eventos em grande volume.
  2. O EventBus fica sobrecarregado, comprometendo sua capacidade de processar e distribuir mensagens.
  3. As notificações legítimas de faturamento sofrem atrasos ou deixam de ser entregues aos usuários.
- **Impacto esperado:** As notificações de faturamento podem deixar de chegar em tempo real, prejudicando o acompanhamento das operações e a experiência dos usuários. Dependendo de como os eventos são armazenados e tratados, também pode haver perda de notificações e inconsistências no processamento do faturamento.
- **Categorias STRIDE:** Denial of Service (T23).

## Considerações finais

### Ameaças mais preocupantes

As ameaças de maior preocupação são as que comprometem a integridade do valor
faturado e a identidade dos usuários:

- **Vazamento do `JWT_SECRET` (T16 / CA09)** e **da chave de callback
  (T18 / CA10)**, que quebram a autenticação e habilitam quase todos os demais
  abusos.
- **Adulteração do motor de cálculo (T13 / CA07)** e **das regras de serviço
  (T06 / CA06)**, que corrompem o faturamento em escala de forma silenciosa.
- **Captura de usuário privilegiado (T02 / CA02)**, porta de entrada para
  aprovação indevida e para encobrir fraude.

### Ativos mais importantes

Os ativos mais críticos são os que sustentam a autoridade do sistema sobre o
valor e sobre quem pode agir:

- **A9 (`JWT_SECRET`) e A10 (`CELERY_CALLBACK_SECRET`)**: base da
  autenticação e da confiança nas chamadas internas.
- **A7 (motor de cálculo) e A3 (regras de serviço)**: core das funcionalidades, qualquer adulteração se propaga a todos os cálculos.
- **A1 (lançamentos) e A2 (auditoria)**: o dado faturado e a prova
  de quem o alterou.

### Tipos de abuso de maior impacto

- **Adulteração silenciosa** do cálculo ou das regras (CA06, CA07): fatura
  errado em escala e é difícil de detectar.
- **Falsificação de perfil por chave vazada** (CA09, CA10): concede acesso total sob
  identidade forjada.
- **Vazamento de dados críticos** (CA04): expõe dados de terceiros e a empresa a
  risco jurídico e reputacional.
- **Remoção da auditoria** (CA05): elimina a prova que permitiria
  responsabilizar os demais abusos.

### Principais dificuldades encontradas

- Delimitar o **escopo** entre o que é responsabilidade da aplicação e o que
  depende da infraestrutura e do SSO corporativo.
- Mapear as **relações entre ameaças e casos de abuso** sem duplicar cenários,
  já que um mesmo caso (por exemplo, CA03 e CA04) cobre várias ameaças de
  ativos diferentes.
- Avaliar a **criticidade** de cada ativo de forma consistente e definir quais
  abusos teriam maior impacto real no faturamento.

### Possíveis medidas de proteção

Não é objetivo desta etapa apresentar uma solução completa. Ainda assim, algumas medidas podem ajudar a reduzir os riscos identificados, como por exemplo manter as chaves (A9, A10 e A13) em um cofre corporativo, com rotação periódica. Garantir que a autorização seja verificada de forma consistente em todas as rotas e endpoints de anexos. Manter uma auditoria imutável, como somente adição para os eventos da timeline. Aplicar limites de requisições nas mudanças de status e no EventBus. Exigir revisão das alterações feitas no motor de cálculo e nas regras de serviço.
