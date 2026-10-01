# Vazamentos

Esse documento descreve os impactos relacionados a vazamentos contra os [ativos](../etapa-1-identificacao-sistema.md) do sistema.

## Problema

Dados de fornecedores, lançamentos, pagamentos, regras de negócio, entre outros dados constituem propriedade intelectual do sistema ou de terceiros, com uso autorizado no sistema. O vazamento desses dados pode ajudar concorrentes a entenderem regras de negócio e adaptarem seus negócios de acordo; Colocar em risco pessoas chave do negócio, quer parar recrutamento por concorrentes, quer para engenharia social; Pode gerar processos judiciais contra a empresa, por conta de vazamento de dados de terceiros

## Ameaças relacionadas

T04, T08, T10, T12, T22.

## Ativos afetados

A1, A4, A5, A6, A14.

## Dimensões de impacto

- **Financeiro:** concorrentes podem usar valores e regras de negócio vazados para ajustar suas propostas, e a empresa pode arcar com indenizações.
- **Operacional:** o vazamento exige investigação, comunicação aos afetados e revisão de acessos.
- **Legal/regulatório:** exposição de dados de terceiros e, no caso de dados pessoais, sujeição à LGPD (ver enquadramento abaixo).
- **Reputacional:** clientes e fornecedores perdem confiança na proteção dos dados que confiaram à empresa.

### Enquadramento LGPD

- **CNPJ (A5)** em geral **não** é dado pessoal pela LGPD, por ser dado de pessoa jurídica, exceto quando identifica pessoa natural (MEI, empresário individual).
- **E-mails corporativos de aprovadores (A6)** **são** dados pessoais e atraem a LGPD.
- **Anexos (A4)** podem conter dados pessoais não previstos no modelo de dados, como comprovantes e notas.

## Exemplo concreto

Um usuário com acesso à listagem de lançamentos exporta os valores faturados por cliente e os CNPJs correspondentes e os repassa a um concorrente, que passa a conhecer a política de preços da empresa. Se a exportação incluir os e-mails dos aprovadores, esses dados pessoais também ficam expostos a phishing e engenharia social.

## Escala de severidade

| Nível | Descrição |
| :---: | --------- |
| 1 — Insignificante | Exposição de dado público ou sem valor de negócio. |
| 2 — Baixo | Exposição pontual de dado de negócio, de um único cliente ou período. |
| 3 — Moderado | Exposição de dados de negócio ou de terceiros de vários clientes, sem dados pessoais. |
| 4 — Grave | Exposição em volume de dados de terceiros ou de dados pessoais (e-mails de aprovadores, dados pessoais em anexos). |
