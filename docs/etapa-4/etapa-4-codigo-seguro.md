# Etapa 4 — Código seguro e testes de segurança

Esta etapa continua a [Etapa 3, arquitetura segura](../etapa-3/etapa-3-arquitetura-segura.md). Lá decidimos como o sistema deveria ser organizado para reduzir os riscos mais graves. Aqui mostramos como duas dessas decisões virariam código seguro na prática. Para cada uma, partimos de um risco e de um requisito que já definimos, escrevemos os testes antes do código e usamos as cheat sheets da OWASP como guia.

Não vamos implementar o sistema completo. Os testes estão definidos, e o código aparece como pseudocódigo e trechos de exemplo, que ainda não foram executados nem aplicados ao sistema real. Por isso o risco residual continua sendo uma estimativa. Ele só se confirma depois de implementar, rodar os testes e reunir as evidências.

## Documentos desta etapa

|  #  | Documento                                                                            | O que responde                                                                                                     |
| :-: | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
|  1  | [Prática 1, autorização por recurso](etapa-4-pratica-1-autorizacao-por-recurso.md)   | Como o servidor passa a conferir se o usuário pode mesmo acessar cada registro, e não só o perfil dele (risco R03) |
|  2  | [Prática 2, validação de token e MFA](etapa-4-pratica-2-validacao-de-token-e-mfa.md) | Como a API passa a exigir o segundo fator de autenticação nos perfis privilegiados (risco R02)                     |

## Práticas escolhidas

Escolhemos duas práticas da lista de exemplos da etapa, a autorização por recurso e a proteção de sessões. Elas vêm de riscos de áreas diferentes, confidencialidade e identidade, e correspondem às decisões D02 e D01 da etapa 3.

As duas práticas seguem a mesma ordem, para deixar claro que os testes vêm antes da solução.

1. Risco e requisito relacionados.
2. Testes de segurança definidos antes da implementação.
3. Implementação, em pseudocódigo e com a descrição passo a passo.
4. Resultado esperado.
5. Referência da OWASP utilizada.

## Rastreabilidade

A tabela mostra o caminho completo de cada prática, da decisão de arquitetura até os testes e a referência usada.

| Prática                     | Decisão (etapa 3) | Requisito | Risco | Testes      | Referência OWASP                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| --------------------------- | ----------------- | --------- | ----- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Autorização por recurso  | D02               | RS03      | R03   | TS01 e TS02 | [Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [IDOR Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html) e [ASVS 5.0, capítulo V8 (Autorização)](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8-Authorization.md)                                                                                                                                                                                                                                     |
| 2. Validação de token e MFA | D01               | RS02      | R02   | TS03 e TS04 | [Multifactor Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html), [Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [REST Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html) e ASVS 5.0, capítulos [V6 (Autenticação)](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x15-V6-Authentication.md) e [V7 (Gerenciamento de sessão)](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x16-V7-Session-Management.md) |

---
