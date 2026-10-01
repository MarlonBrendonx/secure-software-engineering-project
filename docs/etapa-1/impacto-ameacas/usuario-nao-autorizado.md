# Usuários não autorizados

Esse documento descreve os impactos relacionados a usuários não autorizados contra os [ativos](../etapa-1-identificacao-sistema.md) do sistema.

## Problema

O sistema descrito é de uso exclusivo na rede corporativa e possui um susbsistema com perfis de permissões. Qualquer usuário que viole essa configuração e consiga o acesso indevido, quer acessar o sistema sem poder (sem ter usuário válido), quer com privilégios que ele não possui (possui usuário, mas não com as permissões que acessou), conforme descrito na lista de [ameaças](../etapa-1-ameacas-stride.md) expõe o sistema a possiveis atividades relacionadas a vazamento de informações, alterações/remoções indevidas, incluindo regras de negócio necessárias ao bom funcionamento do sistema.

Em suma, boa parte dos demais problemas de segurança no sistema, começam com o acesso de usuários não autorizados.

## Ameaças relacionadas

T01, T02, T03, T06, T07, T09, T11, T14b, T16, T19, T26, T27, T28, T29, T31, T33.

## Ativos afetados

A1, A2, A3, A4, A5, A6, A8, A9, A11, arquivos de carga ERP e sessão.

## Dimensões de impacto

- **Financeiro:** aprovação, reprovação ou alteração indevida de lançamentos e regras de serviço muda o valor faturado.
- **Operacional:** o fluxo de aprovação deixa de ser confiável e os lançamentos afetados precisam ser revistos.
- **Legal/regulatório:** acesso indevido a dados de terceiros (CNPJs, anexos, e-mails de aprovadores) expõe a empresa a processos judiciais e, no caso de dados pessoais, à LGPD.
- **Reputacional:** clientes e fornecedores perdem confiança no controle de acesso da empresa.

## Exemplo concreto

Um usuário não admin que consiga o acesso de administrador, poderá aprovar lançamentos que não deveriam ser aprovados ou reprovar lançamentos que deveriam ser aprovados. Esse tipo de coisa impacta severamente o faturamento da empresa e ainda pode permitir esconder atividades ilícitas, como a aprovação de lançamentos incorretos em benefício do próprio usuário.

Da mesma forma, um usuário com acesso a informações que não deveria possuir, como dados de fornecedores, regras de negócio, registros de pagamentos (em anexos) pode fornecer esses dados aos concorrentes ou outros interessados, trazendo não apenas riscos aos donos dos dados, mas também colocando a própria empresa sobre risco de processos judiciais por conta de vazamento de informações.

## Escala de severidade

| Nível | Descrição |
| :---: | --------- |
| 1 — Insignificante | Acesso indevido sem leitura ou alteração de dado relevante. |
| 2 — Baixo | Leitura indevida de dado pontual, sem alteração e com alcance restrito. |
| 3 — Moderado | Leitura indevida de dados de negócio ou de terceiros (anexos, CNPJs, e-mails), sem alteração de valor. |
| 4 — Grave | Alteração, aprovação ou remoção indevida de lançamentos e regras, ou controle de conta privilegiada. |
