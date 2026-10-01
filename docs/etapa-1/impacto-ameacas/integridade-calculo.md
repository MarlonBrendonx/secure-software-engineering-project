# Comprometimento da integridade do cálculo / cadeia de suprimentos

Esse documento descreve os impactos relacionados ao comprometimento da integridade do cálculo e da cadeia de suprimentos contra os [ativos](../etapa-1-identificacao-sistema.md) do sistema.

## Problema

O motor de cálculo é a autoridade sobre todo valor faturado. Uma alteração no seu código, feita por um insider com acesso ao repositório ou introduzida por meio da cadeia de build e de dependências, chega a produção como se fosse legítima. A partir daí, todos os lançamentos que usam o trecho afetado passam a ser calculados de forma errada, em escala e de forma silenciosa, gerando prejuízo financeiro e dificultando identificar a origem e o alcance do dano.

## Ameaças relacionadas

T13.

## Ativos afetados

A7, A1.

## Dimensões de impacto

- **Financeiro:** faturamento incorreto em escala, para todos os clientes e períodos que usam o trecho afetado.
- **Operacional:** necessidade de identificar e recalcular todos os lançamentos afetados.
- **Legal/regulatório:** cobranças indevidas a clientes e lançamentos contábeis errados no ERP.
- **Reputacional:** perda de confiança no valor apurado pelo sistema.

## Exemplo concreto

Uma alteração no cálculo do tipo `porcentagem` arredonda sempre para cima. Todos os lançamentos com esse tipo de regra passam a ser faturados com um valor ligeiramente maior, sem gerar erro ou alerta.

## Escala de severidade

| Nível | Descrição |
| :---: | --------- |
| 1 — Insignificante | Alteração sem efeito sobre valores calculados. |
| 2 — Baixo | Erro de cálculo restrito a um caso pouco usado e detectado antes do faturamento. |
| 3 — Moderado | Erro de cálculo em um tipo de regra, afetando parte dos lançamentos. |
| 4 — Grave | Erro silencioso no núcleo do cálculo, afetando todos os lançamentos em escala. |
