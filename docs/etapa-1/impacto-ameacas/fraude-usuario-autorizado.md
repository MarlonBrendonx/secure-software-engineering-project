# Fraude/abuso por usuário autorizado

Esse documento descreve os impactos relacionados à fraude ou ao abuso cometidos por usuários autorizados contra os [ativos](../etapa-1-identificacao-sistema.md) do sistema.

## Problema

Nem todo abuso vem de quem não deveria ter acesso. Um usuário legítimo, com as permissões corretas para o seu perfil, pode agir de má-fé e usar operações normais do sistema, como editar lançamentos ou alterar regras de serviço, para mudar valores faturados em benefício próprio ou de terceiros. Como a ação é feita com credenciais válidas e dentro das permissões, o controle de acesso não a impede, e a fraude passa com aparência de operação legítima, gerando cobrança incorreta, prejuízo financeiro e perda de confiança no valor apurado pelo sistema.

## Ameaças relacionadas

T01, T06, T24, T30.

## Ativos afetados

A1, A3, A8 e arquivos de carga ERP.

## Dimensões de impacto

- **Financeiro:** valores faturados alterados em benefício do próprio usuário ou de terceiros.
- **Operacional:** a fraude tem aparência de operação legítima e só é detectada por revisão ou auditoria.
- **Legal/regulatório:** cobrança incorreta a clientes e responsabilização do usuário e da empresa.
- **Reputacional:** perda de confiança no valor apurado e no fluxo de aprovação.

## Exemplo concreto

Um analista com permissão de escrita reduz o valor do lançamento de um cliente com quem tem relação pessoal e envia o lançamento para aprovação, que segue o fluxo normal até o ERP.

## Escala de severidade

| Nível | Descrição |
| :---: | --------- |
| 1 — Insignificante | Alteração sem efeito sobre o valor faturado. |
| 2 — Baixo | Alteração pontual detectada antes da aprovação. |
| 3 — Moderado | Alteração de valor de um lançamento que chega ao ERP. |
| 4 — Grave | Alteração de regras de serviço ou de vários lançamentos, com efeito em escala. |
