# Etapa 3 — Arquitetura segura

Esta etapa dá continuidade à [Etapa 2 — Riscos e NIST CSF 2.0](../etapa-2/etapa-2-riscos-nist.md), transformando os riscos e os controles do plano de tratamento em **requisitos de segurança** e **decisões de arquitetura**. O sistema, os ativos e os riscos (R01–R29) são os mesmos já descritos nas etapas anteriores.

Nesta etapa não se implementam controles. O objetivo é mostrar como o sistema seria organizado para reduzir os riscos prioritários. Os requisitos e as decisões são **propostas**, e a redução do risco só se confirma depois de implementação, testes e evidências.

## Documentos desta etapa

|  #  | Documento                                                   | O que responde                                                                                                     |
| :-: | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
|  1  | [Requisitos de segurança](etapa-3-requisitos.md)            | Quais riscos prioritários foram escolhidos e quais requisitos verificáveis (RS01–RS03) derivam deles               |
|  2  | [Vulnerabilidades catalogadas](etapa-3-vulnerabilidades.md) | A quais vulnerabilidades de catálogos reconhecidos (CWE e OWASP) cada requisito se relaciona                       |
|  3  | [Diagrama da arquitetura segura](etapa-3-diagrama.md)       | Como usuários, aplicação, autenticação, autorização, dados e monitoramento se organizam, e onde ficam os controles |
|  4  | [Decisões de arquitetura](etapa-3-decisoes.md)              | Quais decisões (D01–D03) tratam os riscos escolhidos e por que foram tomadas                                       |

## Riscos tratados

Os três riscos escolhidos (R01, R02 e R03) percorrem os quatro documentos acima. R01 e R02 estão entre os riscos Críticos, e R03 é o Alto de maior pontuação. Cada um gera um requisito no documento 1, é ligado a uma vulnerabilidade catalogada no documento 2, aparece no diagrama do documento 3 e é tratado por uma decisão no documento 4, com a mesma numeração (R01, RS01 e D01; R02, RS02 e D02; R03, RS03 e D03).

R18 também é Crítico (3×4), mas não foi escolhido como risco próprio. O motivo está no [documento de requisitos](etapa-3-requisitos.md#riscos-prioritários-selecionados), e a segregação de funções que ele exige entra como premissa de D01 e de C4.

## Rastreabilidade

| Requisito | Risco | Vulnerabilidade                  | Decisão | Controles (C1–C8)  | Controle da arquitetura                                                                                    | Controle do plano da Etapa 2 (seção 9.2)                             |
| --------- | ----- | -------------------------------- | ------- | ------------------ | ---------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| RS01      | R01   | CWE-841, OWASP A06:2025          | D01     | C4, C5, C6, C7, C8 | Transição obrigatória pela máquina de estados, carga do ERP só com a versão aprovada e trilha de auditoria | Aprovação obrigatória após o envio, alertas e auditoria              |
| RS02      | R02   | CWE-308, OWASP A07:2025          | D02     | C1, C2, C7         | MFA no SSO, validação do MFA na API e alertas                                                              | MFA para administrador e gestor, monitoramento de acessos suspeitos  |
| RS03      | R03   | CWE-639, CWE-862, OWASP A01:2025 | D03     | C3, C6, C7, C8     | Autorização por recurso nos casos de uso, registro das negações e testes por rota no CI                    | Verificação de permissão por recurso e testes automatizados por rota |

Os controles C1–C8 estão descritos na [seção 2 do diagrama](etapa-3-diagrama.md#2-controles-posicionados-no-diagrama).

A ordem de implementação segue os estágios da [seção 10 do plano](../etapa-2/etapa-2-plano-e-residual.md), na qual R02 fica no estágio 1, R01 no estágio 2 e R03 no estágio 3.

---
