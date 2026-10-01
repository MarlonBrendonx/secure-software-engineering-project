# Impedimentos

Esse documento descreve os impactos relacionados a impedimentos contra os [ativos](../etapa-1-identificacao-sistema.md) do sistema.

## Problema

Impedimentos interferem no bom funcionamento do sistema, impedindo que requisições válidas sejam processadas. Os principais impactos vão desde o sistema completamente inoperante, gerando prejuízos por seu não funcionamento, a experiência ruim do usuário por conta de lentidões no sistema, ou até mesmo falhas em software por conta da sobrecarga, como operações "incompletas" ou subsistemas danificados por conta de dados incorretos inseridos em meio a uma sobrecarga

## Ameaças relacionadas

T14a, T20, T23.

## Ativos afetados

A8, A12, A14.

## Dimensões de impacto

- **Financeiro:** atraso no faturamento enquanto o sistema ou o fluxo de aprovação estiver indisponível.
- **Operacional:** aprovações, lançamentos e notificações deixam de ser processados, e operações interrompidas podem deixar dados inconsistentes.
- **Legal/regulatório:** prazos de faturamento e de fechamento contábil podem ser descumpridos.
- **Reputacional:** usuários internos e clientes percebem o sistema como instável.

## Exemplo concreto

Uma sobrecarga no PostgreSQL, compartilhado por todo o sistema, deixa lançamentos e aprovações indisponíveis no fechamento do período. Operações em andamento durante a sobrecarga podem ficar incompletas e precisar ser revistas depois da recuperação.

## Escala de severidade

| Nível | Descrição |
| :---: | --------- |
| 1 — Insignificante | Lentidão momentânea, sem interrupção de operações. |
| 2 — Baixo | Indisponibilidade parcial e recuperável (notificações, fluxo de aprovação), sem perda de dados. |
| 3 — Moderado | Indisponibilidade prolongada de uma funcionalidade central, com atraso no faturamento. |
| 4 — Grave | Sistema inteiro inoperante ou com dados inconsistentes após a sobrecarga. |
