# Usuários não autorizados

Esse documento descreve os impactos relacionados a usuários não autorizados contra os ![ativos](../etapa-1-identificacao-sistemas.md) do sistema.

## Problema

O sistema descrito é de uso exclusivo na rede corporativa e possui um susbsistema com perfis de permissões. Qualquer usuário que viole essa configuração e consiga o acesso indevido, quer acessar o sistema sem poder (sem ter usuário válido), quer com privilégios que ele não possui (possui usuário, mas não com as permissões que acessou), conforme descrito na lista de ![ameaças](../etapa-1-ameacas-stride.md) expõe o sistema a possiveis atividades relacionadas a vazamento de informações, alterações/remoções indevidas, incluindo regras de negócio necessárias ao bom funcionamento do sistema.

Por exemplo, um usuário não admin que consiga o acesso de administrador, poderá aprovar lançamentos que não deveriam ser aprovados ou reprovar lançamentos que deveriam ser aprovados. Esse tipo de coisa impacta severamente o faturamento da empresa e ainda pode permitir esconder atividades ilícitas, como a aprovação de lançamentos incorretos em benefício do próprio usuário.

Da mesma forma, um usuário com acesso a informações que não deveria possuir, como dados de fornecedores, regras de negócio, registros de pagamentos (em anexos) pode fornecer esses dados aos concorrentes ou outros interessados, trazendo não apenas riscos aos donos dos dados, mas também colocando a própria empresa sobre risco de processos judiciais por conta de vazamento de informações.

Em suma, boa parte dos demais problemas de segurança no sistema, começam com o acesso de usuários não autorizados.