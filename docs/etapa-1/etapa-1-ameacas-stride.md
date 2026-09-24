
# Etapa 1 — Modelagem de ameaças e casos de abuso

## Escopo

## Tabela STRIDE Consolidada


| ID  | Categoria STRIDE       | Ativos   | Ameaça                 | Impacto |
| --- | ---------------------- |--------- | ---------------------- | ------- | 
| T01 | Tampering              | A1       | Usuário não autorizado altera lançamentos | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T02 | Elevation of Privilege | A1, A2, A3   | Usuário sem permissões para acesso obtêm o controle de usuário com permissões | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T03 | Elevation of Privilege | A1       | Usuário obtêm dados de lançamentos sem autorização | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T04 | Information Disclosure | A1       | Usuário vaza lançamentos do sistema | [Vazamento](impacto-ameacas/vazamento.md) |
| T05 | Repudiation            | A2       | Perda do timeline impede a identificação do que cada usuário fez no sistema | [Impedimento](impacto-ameacas/impedimento.md) |
| T06 | Tampering              | A3       | Alteração não autorizada em regras de serviço | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T07 | Elevation of Privilege | A4       | Acesso não autorizado a anexos | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T08 | Information Disclosure | A4       | Vazamento de informações dos anexos | [Vazamento](impacto-ameacas/vazamento.md) |
| T09 | Elevation of Privilege | A5       | Acesso não autorizado a CNPJs | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T10 | Information Disclosure | A5       | Vazamento de CNPJs | [Vazamento](impacto-ameacas/vazamento.md) |
| T11 | Elevation of Privilege | A6       | Acesso não autorizado a endereços de e-mail dos aprovadores | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T12 | Information Disclosure | A6       | Vazamento de endereços de e-mail dos aprovadores | [Vazamento](impacto-ameacas/vazamento.md) |
| T13 | Tampering              | A7       | Alteração em código de cálculo de valores | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) |
| T14 | Denial of Service      | A8       | Falha induzida no código impedindo o fluxo de autorização | [Impedimento](impacto-ameacas/impedimento.md) |
| T15 | Information Disclosure | A9       | Vazamento de segredo gerador de token  | [Sistema não autorizado](impacto-ameacas/sistema-nao-autorizado.md) |
| T16 | Spoofing               | A9       | Uso de segredo vazado para impersonificar usuário válido | [Usuário não autorizado](impacto-ameacas/usuario-nao-autorizado.md) | 
| T17 | Information Disclosure | A10      | Vazamento da chave de API interna | [Sistema não autorizado](impacto-ameacas/sistema-nao-autorizado.md) | 
| T18 | Spoofing               | A10      | Código não autorizado impersonificando chamadas válidas  | [Sistema não autorizado](impacto-ameacas/sistema-nao-autorizado.md) |
| T19 | Elevation of Privilege | A11      | Acesso não autorizado aos anexos extra sistema | [Vazamento](impacto-ameacas/vazamento.md) |
| T20 | Denial of Service      | A12      | Ataque a infraestrutura, deixando o sistema inoperante | [Impedimento](impacto-ameacas/impedimento.md) |
| T21 | Spoofing               | A13, A14 | Envio de e-mails impersonificando sender válido | [Sistema não autorizado](impacto-ameacas/sistema-nao-autorizado.md) |
| T22 | Information Disclosure | A15      | Vazamento de informações sobre faturamento | [Vazamento](impacto-ameacas/vazamento.md) |
| T23 | Denial of Service      | A15      | Sobrecarga no EventBus impedindo operações válidas | [Impedimento](impacto-ameacas/impedimento.md) | 

## Casos de Abuso

| ID  | Título | Ator e objetivo resumidos | Ameaças |
| --- | ------ | ------------------------- | ------- |
| C01 | Alteração de lançamentos | Ator altera ou remove lançamentos financeiros prejudicando as operações de faturamento no sistema | T01 |
| C02 | Captura de usuário do SSO | Ator não autorizado obtêm o controle de usuário com privilégios via SSO | T02 |
| C03 | Acesso não autorizado | Ator com usuário capturado ou acesso direto, acessa dados que não deveria no sistema como lançamentos, anexos, etc  | T03, T07, T09, T11, T19 |
| C04 | Vazamento de informações | Ator com usuário capturado ou acesso direto vaza informações críticas do sistema | T04, T08, T10, T12, T15, T17, T22  |
| C05 | Remoção de timeline | Ator remove timeline impedindo a audição do sistema | T05 |
| C06 | Alteração de regras de serviço | Ator altera regras de serviço prejudicando operações do sistema | T06 |
| C07 | Tampering no código | Ator altera os módulos do código responsáveis pelos cálculos de valores | T13 | 
| C08 | Sobrecarga no fluxo de autorização | Ator sobrecarrega a máquina de estados com os guards de autorização impedindo o fluxo de aprovação de lançamentos | T14 |
| C09 | Acesso Fake | Ator com segredo vazado consegue obter acesso não autorizado ao sistema | T16 |
| C10 | Chamadas Fake | Código malicioso com segredo do API consegue forjar requisições falsas no sistema | T18 |
| C11 | Banco offline | Ator consegue sobrecarregar o banco de dados, deixando o sistema inteiro inoperante | T20 |
| C12 | Envio malicioso | Ator consegue enviar e-mails maliciosos em nome da empresa | T21 |
| C13 | Sobrecarga no EventBus | Ator consegue sobrecarregar o EventBus impedindo o processamento de operações válidas | T23 |