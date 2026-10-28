# Etapa 3 — Decisões de arquitetura

Este documento faz parte da [Etapa 3](etapa-3-arquitetura-segura.md).

## D01 — Exigir o MFA no SSO e conferi-lo também na API

| Item                  | Descrição                                                                                                                                                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Problema ou risco     | Em R02, uma conta de administrador ou gestor capturada por phishing ou reuso de credenciais dá controle sobre aprovações e habilita a maioria dos outros abusos. Hoje não há MFA nem detecção de sessão anômala.                          |
| Decisão               | Configurar o MFA obrigatório para esses perfis no Keycloak e fazer a API validar, no token, a indicação de que o MFA foi concluído, em vez de confiar só no login.                                                              |
| Motivo                | O MFA fica em um único ponto, o SSO corporativo, e não é reimplementado na aplicação. A API também confere o token, porque um token emitido por outro fluxo, sem MFA, contornaria a proteção.                                            |
| Componente afetado    | Keycloak e OAuth Service .NET (configuração do fluxo de login), provedor de autenticação e guards da API (`src/core/auth`).                                                                                                             |
| Resultado esperado    | Um atacante que tenha só a senha não obtém sessão de administrador ou gestor. Tentativas repetidas na segunda etapa geram alerta. Reduz a probabilidade de R02 de 3 para 1.                                                              |

## D02 — Autorizar por recurso no servidor, na camada de casos de uso

| Item                  | Descrição                                                                                                                                                                                                                                                      |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Problema ou risco     | Em R03, o guard atual confere o perfil (`require_role`), mas uma rota, um anexo ou uma consulta pode devolver dados de outro cliente ou período se o identificador for trocado. Uma rota nova sem a verificação de recurso expõe os dados direto.                |
| Decisão               | Fazer cada caso de uso verificar, no servidor, a permissão do usuário sobre o recurso (cliente, período e responsável) antes de ler ou gravar. Usar identificadores não sequenciais nas respostas e cobrir todas as rotas com testes de autorização no CI. |
| Motivo                | O perfil responde "o que o usuário pode fazer" e não "sobre quais registros". Colocar a regra no caso de uso, e não só na rota, evita que um endpoint novo esqueça a checagem. Esconder opções na interface não impede o acesso direto à API.                   |
| Componente afetado    | Casos de uso da camada de aplicação, gateways de leitura de lançamentos e anexos, guards de `presentation` e a suíte de testes do CI.                                                                                                                         |
| Resultado esperado    | Uma requisição com o identificador de outro escopo é negada em todas as rotas, e a negação fica registrada. Reduz a probabilidade de R03 de 3 para 1.                                                                                                          |

## D03 — Tratar a máquina de estados como única via de mudança de um lançamento enviado

| Item                  | Descrição                                                                                                                                                                                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Problema ou risco     | Em R01, o perfil analista já tem escrita sobre os lançamentos, então a alteração ou remoção depois do envio chega ao ERP sem nova aprovação. O abuso não exige capacidade técnica, só má intenção.                                                            |
| Decisão               | Fazer o servidor aceitar a alteração ou exclusão de um lançamento enviado somente por uma transição da máquina de estados que o devolva à aprovação, registrando a transição e o autor na trilha de auditoria. A carga do ERP lê só a versão aprovada. |
| Motivo                | A regra de negócio fica em um ponto único e verificável, que não depende da interface. O valor já é recalculado no servidor, e a transição obrigatória garante que um segundo usuário veja a mudança antes de o valor sair do sistema.                      |
| Componente afetado    | Casos de uso de alteração e de mudança de status, objeto de valor `billing_status`, tabela `audit_logs` e gerador da carga do ERP.                                                                                                                           |
| Resultado esperado    | Nenhuma alteração posterior ao envio chega ao ERP sem nova aprovação, e cada tentativa fica atribuída a um usuário. Reduz a probabilidade de R01 de 3 para 1.                                                                                                |
