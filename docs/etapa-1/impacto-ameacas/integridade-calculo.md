# Comprometimento da integridade do cálculo / cadeia de suprimentos

Esse documento descreve os impactos relacionados ao comprometimento da integridade do cálculo e da cadeia de suprimentos contra os [ativos](../etapa-1-identificacao-sistema.md) do sistema.

## Problema

O motor de cálculo é a autoridade sobre todo valor faturado. Uma alteração no seu código, feita por um insider com acesso ao repositório ou introduzida por meio da cadeia de build e de dependências, chega a produção como se fosse legítima. A partir daí, todos os lançamentos que usam o trecho afetado passam a ser calculados de forma errada, em escala e de forma silenciosa, gerando prejuízo financeiro e dificultando identificar a origem e o alcance do dano.
