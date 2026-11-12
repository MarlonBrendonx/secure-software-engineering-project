# Etapa 5 — Verificação de vulnerabilidades

Esta etapa continua a [Etapa 4, código seguro e testes de segurança](../etapa-4/etapa-4-codigo-seguro.md). Lá os testes foram apenas definidos. Aqui usamos uma ferramenta de teste de segurança, o ZAP, para observar alertas e configurações inseguras no protótipo PSP em execução.

O teste foi feito somente no protótipo do próprio grupo, executado localmente e com dados fictícios. Nenhum sistema de terceiros foi testado. Também não exploramos as vulnerabilidades até obter acesso indevido. O objetivo é interpretar os resultados da ferramenta.

## Resultado em uma frase

O scan passivo como `admin`, com MFA, percorreu login, cadastro e faturamento (64 mensagens, inclusive as rotas de escrita) e não achou nenhum alerta High. A lista de 11 alertas (3 Médios, 3 Baixos e 5 Informativos) vem da captura 04a. Escolhemos três deles, todos de configuração de cabeçalhos HTTP, e confirmamos cada um direto nos cabeçalhos da aplicação. O active scan como `analyst` não gerou alertas novos, mas quase todas as suas requisições às rotas protegidas receberam `401`. Como `admin`, o active scan alcançou essas rotas sem `401`, mas só com `GET` e, em sua maioria, com respostas `422`. Por isso, "sem alertas" no scan ativo não prova que as rotas estão livres de falhas (veja [Limitações](etapa-5-limitacoes.md)).

## Documentos desta etapa

|  #  | Documento                                                     | O que responde                                                                |
| :-: | ------------------------------------------------------------- | ----------------------------------------------------------------------------- |
|  1  | [Ambiente e configuração](etapa-5-ambiente-e-configuracao.md) | O que foi testado, com qual ferramenta e com qual configuração                |
|  2  | [Execução e evidências](etapa-5-execucao-e-evidencias.md)     | O que foi executado na sessão e quais capturas e relatórios comprovam         |
|  3  | [Análise dos achados](etapa-5-analise-dos-achados.md)         | Quais três alertas foram analisados e o que cada um significa                 |
|  4  | [Correções propostas](etapa-5-correcoes-propostas.md)         | Como corrigir cada achado e como verificar a correção                         |
|  5  | [Limitações e descartes](etapa-5-limitacoes.md)               | O que foi descartado, o que pode ser falso positivo e o que o teste não cobre |

As evidências ficam em [`evidencias/etapa-5/`](../../evidencias/etapa-5/).

## Rastreabilidade

A tabela liga cada achado à categoria OWASP, ao CWE e aos riscos e requisitos das etapas 2 e 3.

| Achado | Categoria OWASP / CWE                                  | Risco (etapa 2)   | Requisito (etapa 3) | Correção                                    |
| ------ | ------------------------------------------------------ | ----------------- | ------------------- | ------------------------------------------- |
| A01    | A05:2021 Security Misconfiguration / CWE-693           | sem risco dedicado; relacionado a R29 (defesa em profundidade) | sem requisito dedicado; relacionado a RS08 | CSP sem `'unsafe-inline'` e com `form-action` |
| A02    | A05:2021 Security Misconfiguration / CWE-693           | sem risco dedicado | sem requisito dedicado | `X-Content-Type-Options: nosniff` na API    |
| A03    | A05:2021 Security Misconfiguration / CWE-497           | sem risco dedicado | sem requisito dedicado | `poweredByHeader: false` no Next.js         |

**Lacuna encontrada.** Nenhum risco das etapas 2 e 3 trata de cabeçalhos HTTP de segurança. Os três achados vieram de um tipo de problema que o nosso registro de riscos não cobria. Como encaminhamento, registrar um risco de "configuração insegura de cabeçalhos HTTP" na próxima revisão da etapa 2.

---
