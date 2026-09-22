
# Modelagem de ameaças STRIDE


| ID  | Categoria STRIDE       | Ativo    | Ameaça                 | Impacto |
| --- | ---------------------- |--------- | ---------------------- | ------- | 
| T01 | Tampering              | A1       | Usuário não autorizado altera lançamentos |  |
| T02 | Elevation of Privilege | A1       | Usuário sem permissões para acesso obtêm o controle de usuário com permissões | |
| T03 | Information Disclosure | A1       | Usuário obtêm dados de lançamentos sem autorização | |
| T04 | Elevation of Privilege | A2       | Usuário sem permissões para acesso obtêm o controle de usuário com permissões | |
| T05 | Repudiation            | A2       | Perda do timeline impede a identificação do que cada usuário fez no sistema | |
| T06 | Elevation of Privilege | A3       | Usuário sem permissões para acesso obtêm o controle de usuário com permissões | |
| T07 | Tampering              | A3       | Alteração não autorizada em regras de serviço | |
| T08 | Elevation of Privilege | A4       | Acesso não autorizado a anexos | |
| T09 | Information Disclosure | A4       | Vazamento de informações dos anexos | |
| T10 | Elevation of Privilege | A5       | Acesso não autorizado a CNPJs | |
| T11 | Information Disclosure | A5       | Vazamento de CNPJs | |
| T12 | Information Disclosure | A6       | Vazamento de e-mails dos aprovadores | |
| T13 | Tampering              | A7       | Alteração em código de cálculo de valores | |
| T14 | Denial of Service      | A8       | Falha induzida no código impedindo o fluxo de autorização | |
| T15 | Information Disclosure | A9       | Vazamento de segredo gerador de token  | |
| T16 | Spoofing               | A9       | Uso de segredo vazado para impersonificar usuário válido | | 
| T17 | Information Disclosure | A10      | Vazamento da chave de API interna | | 
| T18 | Spoofing               | A10      | Código não autorizado impersonificando chamadas válidas  | |
| T19 | Information Disclosure | A11      | Acesso não autorizado a dados do sistema, permitindo vazamento de informações | |
| T20 | Denial of Service      | A12      | Ataque a infraestrutura, deixando o sistema inoperante | |
| T21 | Spoofing               | A13, A14 | Envio de e-mails impersonificando sender válido | |
| T22 | Information Disclosure | A15      | Vazamento de informações sobre faturamento | |
| T23 | Denial of Service      | A15      | Sobrecarga no EventBus impedindo operações válidas | | 

