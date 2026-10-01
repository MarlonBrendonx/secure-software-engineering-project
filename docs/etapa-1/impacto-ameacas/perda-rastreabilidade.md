# Perda de rastreabilidade/repúdio

Esse documento descreve os impactos relacionados à perda de rastreabilidade e ao repúdio de ações contra os [ativos](../etapa-1-identificacao-sistema.md) do sistema.

## Problema

A timeline de transições e a auditoria são a prova de quem fez o quê no sistema. A perda, remoção ou corrupção desses registros não deixa o sistema indisponível, mas faz com que ele deixe de provar a autoria das ações. Sem essa prova, um usuário pode negar ter alterado, enviado ou aprovado um lançamento, atividades ilícitas ficam sem responsabilização e a empresa perde a capacidade de auditar e contestar valores faturados.

## Ameaças relacionadas

T05, T34, T35.

## Ativos afetados

A1, A2.

## Dimensões de impacto

- **Financeiro:** valores faturados indevidamente não podem ser contestados nem atribuídos a um responsável.
- **Operacional:** investigações de incidentes ficam sem base para reconstruir o que aconteceu.
- **Legal/regulatório:** a empresa perde a prova exigida em auditorias e disputas com clientes.
- **Reputacional:** a confiança no fluxo de aprovação depende de a trilha de auditoria ser íntegra.

## Exemplo concreto

Um aprovador aprova um lançamento irregular e, em seguida, os registros correspondentes da timeline são removidos. Quando a divergência é percebida, não há como provar quem aprovou nem quando.

## Escala de severidade

| Nível | Descrição |
| :---: | --------- |
| 1 — Insignificante | Perda de registros sem relevância para auditoria. |
| 2 — Baixo | Lacuna pontual na trilha, reconstruível por outras fontes. |
| 3 — Moderado | Perda de registros de transições de um conjunto de lançamentos. |
| 4 — Grave | Remoção ou corrupção da trilha que impede provar a autoria de ações críticas. |
