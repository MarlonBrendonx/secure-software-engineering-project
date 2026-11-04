# Etapa 3 — Arquitetura segura

Esta etapa dá continuidade à [Etapa 2 — Riscos e NIST CSF 2.0](../etapa-2/etapa-2-riscos-nist.md), transformando os riscos e os controles do plano de tratamento em **requisitos de segurança** e **decisões de arquitetura**. O sistema, os ativos e os riscos (R01–R29) são os mesmos já descritos nas etapas anteriores.

Nesta etapa não se implementam controles. O objetivo é mostrar como o sistema seria organizado para reduzir os riscos prioritários. Os requisitos e as decisões são **propostas**, e a redução do risco só se confirma depois de implementação, testes e evidências.

## Documentos desta etapa

|  #  | Documento                                                   | O que responde                                                                                                     |
| :-: | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
|  1  | [Requisitos de segurança](etapa-3-requisitos.md)            | Quais riscos prioritários foram escolhidos e quais requisitos verificáveis (RS01–RS08) derivam deles               |
|  2  | [Vulnerabilidades catalogadas](etapa-3-vulnerabilidades.md) | A quais vulnerabilidades de catálogos reconhecidos (CWE e OWASP) cada requisito se relaciona                       |
|  3  | [Diagrama da arquitetura segura](etapa-3-diagrama.md)       | Como usuários, aplicação, autenticação, autorização, dados e monitoramento se organizam, e onde ficam os controles |
|  4  | [Decisões de arquitetura](etapa-3-decisoes.md)              | Quais decisões (D01–D08) tratam os riscos escolhidos e por que foram tomadas                                       |

## Riscos tratados

Os riscos foram escolhidos em duas rodadas, e todos percorrem os quatro documentos acima. Na primeira, R01, R02 e R03: R01 e R02 estão entre os riscos Críticos, e R03 é o Alto de maior pontuação. Na segunda, R06 e R07 (tratados juntos), R23, R26, R28 e R29, que são riscos Altos dos estágios 1 e 2 dos quais os controles da primeira rodada dependem: um token que não possa ser forjado, uma auditoria que seja de fato gravada, guards que neguem o acesso quando falham, uma carga do ERP igual à que foi gerada e requisições feitas de propósito pelo usuário. Com eles, a arquitetura cobre cinco das seis categorias STRIDE. Denial of Service ficou de fora, e o motivo está no [documento de requisitos](etapa-3-requisitos.md#segunda-rodada-riscos-dos-quais-os-controles-dependem).

Cada risco, ou par de riscos, gera um requisito no documento 1, é ligado a uma vulnerabilidade catalogada no documento 2, aparece no diagrama do documento 3 e é tratado por uma decisão no documento 4. Requisito e decisão têm a mesma numeração: R01, RS01 e D01; R02, RS02 e D02; R03, RS03 e D03; R06 e R07, RS04 e D04; R26, RS05 e D05; R28, RS06 e D06; R23, RS07 e D07; R29, RS08 e D08.

R18 também é Crítico (3×4), mas não foi escolhido como risco próprio. O motivo está no [documento de requisitos](etapa-3-requisitos.md#riscos-prioritários-selecionados), e a segregação de funções que ele exige entra como premissa de D01 e de C4.

## Rastreabilidade

| Requisito | Risco | Vulnerabilidade                  | Decisão | Controles (C1–C14) | Controle da arquitetura                                                                                    | Controle do plano da Etapa 2 (seção 9.2)                             |
| --------- | ----- | -------------------------------- | ------- | ------------------ | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| RS01      | R01   | CWE-841, OWASP A06:2025          | D01     | C4, C5, C6, C7, C8 | Transição obrigatória pela máquina de estados, carga do ERP só com a versão aprovada e trilha de auditoria | Aprovação obrigatória após o envio, alertas e auditoria              |
| RS02      | R02   | CWE-308, OWASP A07:2025          | D02     | C1, C2, C7         | MFA no SSO, validação do MFA na API e alertas                                                              | MFA para administrador e gestor, monitoramento de acessos suspeitos  |
| RS03      | R03   | CWE-639, CWE-862, OWASP A01:2025 | D03     | C3, C6, C7, C8     | Autorização por recurso nos casos de uso, registro das negações e testes por rota no CI                    | Verificação de permissão por recurso e testes automatizados por rota |
| RS04      | R06, R07 | CWE-522, CWE-347, OWASP A04:2025 | D04  | C9, C10, C7, C8    | Assinatura assimétrica com chave privada no cofre, validação estrita do token e sessão revogável           | `JWT_SECRET` no cofre com rotação; validação de emissor, audience e expiração; sessão registrada no servidor |
| RS05      | R26   | CWE-778, CWE-223, OWASP A09:2025 | D05     | C11, C6, C7, C8    | Auditoria na mesma transação da operação, *outbox* com entrega repetida e reconciliação                   | Persistência durável vinculada à operação, entrega com repetição e reconciliação |
| RS06      | R28   | CWE-636, CWE-755, OWASP A10:2025 | D06     | C12, C6, C7, C8    | Guards que negam por padrão, política declarada em toda rota e injeção de falha no CI                      | Negação de acesso em falhas dos guards e testes de falha no CI |
| RS07      | R23   | CWE-345, CWE-353, CWE-1236, OWASP A08:2025 | D07 | C13, C5, C7, C8 | Campos de texto sem fórmula, manifesto assinado em área imutável e conferência antes da importação | Tratamento dos campos exportados, hash ou assinatura do arquivo e bloqueio da importação divergente |
| RS08      | R29   | CWE-352, OWASP A01:2025          | D08     | C14, C6, C7, C8    | Token anti-CSRF ligado à sessão, verificação de `Origin`, cookies `SameSite=Strict` e CORS restrito       | Proteção anti-CSRF, validação de origem, cookies `SameSite`/`Secure`/`HttpOnly` e testes entre origens |

Os controles C1–C14 estão descritos na [seção 2 do diagrama](etapa-3-diagrama.md#2-controles-posicionados-no-diagrama).

A ordem de implementação segue os estágios da [seção 10 do plano](../etapa-2/etapa-2-plano-e-residual.md), na qual R02, R06 e R07 ficam no estágio 1, R01, R23, R26, R28 e R29 no estágio 2 e R03 no estágio 3. Dentro do estágio 2, R26 e R28 vêm antes de R01, porque C11 e C12 são a base de que C4 e C6 dependem. R29 vem logo depois de R01, porque protege as mesmas rotas, e R23 vem por último no estágio, porque estende C5 até o ERP.

---
