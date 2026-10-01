
# Etapa 1 — Modelagem de ameaças e casos de abuso

## Escopo

## Tabela STRIDE Consolidada


| ID  | Categoria STRIDE       | Categoria secundária   | Ativos   | Ameaça                 | Impacto |
| --- | ---------------------- | ---------------------- |--------- | ---------------------- | ------- | 
| T01 | Tampering              | —                      | A1       | Usuário não autorizado altera lançamentos | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md), [Fraude/abuso por usuário autorizado](impacto-ameacas/fraude-usuario-autorizado.md) |
| T02 | Spoofing               | Elevation of Privilege | A1, A2, A3   | Usuário sem permissões para acesso obtêm o controle de usuário com permissões | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T03 | Information Disclosure | Elevation of Privilege | A1       | Usuário obtêm dados de lançamentos sem autorização | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T04 | Information Disclosure | —                      | A1       | Usuário vaza lançamentos do sistema | [Vazamento](impacto-ameacas/vazamento.md) |
| T05 | Repudiation            | —                      | A2       | Perda do timeline impede a identificação do que cada usuário fez no sistema | [Perda de rastreabilidade/repúdio](impacto-ameacas/perda-rastreabilidade.md) |
| T06 | Tampering              | —                      | A3       | Alteração não autorizada em regras de serviço | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md), [Fraude/abuso por usuário autorizado](impacto-ameacas/fraude-usuario-autorizado.md) |
| T07 | Information Disclosure | Elevation of Privilege | A4       | Acesso não autorizado a anexos | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T08 | Information Disclosure | —                      | A4       | Vazamento de informações dos anexos | [Vazamento](impacto-ameacas/vazamento.md) |
| T09 | Information Disclosure | Elevation of Privilege | A5       | Acesso não autorizado a CNPJs | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T10 | Information Disclosure | —                      | A5       | Vazamento de CNPJs | [Vazamento](impacto-ameacas/vazamento.md) |
| T11 | Information Disclosure | Elevation of Privilege | A6       | Acesso não autorizado a endereços de e-mail dos aprovadores | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T12 | Information Disclosure | —                      | A6       | Vazamento de endereços de e-mail dos aprovadores | [Vazamento](impacto-ameacas/vazamento.md) |
| T13 | Tampering              | —                      | A7       | Alteração em código de cálculo de valores | [Comprometimento da integridade do cálculo / cadeia de suprimentos](impacto-ameacas/integridade-calculo.md) |
| T14a | Denial of Service     | —                      | A8       | Saturação da máquina de estados impedindo o fluxo de autorização | [Impedimento](impacto-ameacas/impedimentos.md) |
| T14b | Elevation of Privilege | —                     | A8       | Guard de autorização que falha aberto (exceção tratada como permitido) | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T15 | Information Disclosure | —                      | A9       | Vazamento de segredo gerador de token  | [Sistema não autorizado](impacto-ameacas/sistema-nao-autorizado.md) |
| T16 | Spoofing               | —                      | A9       | Uso de segredo vazado para impersonificar usuário válido | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) | 
| T17 | Information Disclosure | —                      | A10      | Vazamento da chave de API interna | [Sistema não autorizado](impacto-ameacas/sistema-nao-autorizado.md) | 
| T18 | Spoofing               | —                      | A10      | Código não autorizado impersonificando chamadas válidas  | [Sistema não autorizado](impacto-ameacas/sistema-nao-autorizado.md) |
| T19 | Elevation of Privilege | —                      | A11      | Acesso não autorizado aos anexos extra sistema | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T20 | Denial of Service      | —                      | A12      | Ataque a infraestrutura, deixando o sistema inoperante | [Impedimento](impacto-ameacas/impedimentos.md) |
| T21 | Spoofing               | —                      | A13      | Envio de e-mails impersonificando sender válido | [Sistema não autorizado](impacto-ameacas/sistema-nao-autorizado.md) |
| T22 | Information Disclosure | —                      | A14      | Vazamento de informações sobre faturamento | [Vazamento](impacto-ameacas/vazamento.md) |
| T23 | Denial of Service      | —                      | A14      | Sobrecarga no EventBus impedindo operações válidas | [Impedimento](impacto-ameacas/impedimentos.md) | 
