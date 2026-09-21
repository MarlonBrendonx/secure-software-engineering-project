## 1 Descrição do sistema

### Qual problema o sistema resolve

O sistema centraliza o registro, o cálculo e a aprovação dos valores que a empresa fatura a cada cliente da rede, por período. Antes de existir um sistema autoritativo, o valor faturado dependia de
planilhas manuais, sujeitas a erro de cálculo, a falta de auditoria de quem alterou o quê e
a ausência de um fluxo formal de aprovação antes de o valor chegar ao ERP. O software resolve
isso ao tornar o **servidor a autoridade sobre o valor** (todo valor é recalculado a
partir da regra de serviço contratada) e ao submeter cada lançamento a uma **máquina de
estados de aprovação** com auditoria completa.

### Quem utiliza o sistema

Usuários corporativos internos, autenticados por SSO corporativo

| Perfil     | Uso típico no PSP                                                                           |
| ---------- | ------------------------------------------------------------------------------------------- |
| `admin`    | Acesso total; opera criação, edição, todas as transições de status e rotas administrativas. |
| `analista` | Cria e edita lançamentos, envia para aprovação da gestão                                    |
| `gerente`  | Aprova e reprova lançamentos                                                                |
| `none`     | Sem acesso ao negócio, só pode solicitar acesso.                                            |

### Principais funcionalidades

- **Listagem e consulta** de clientes, serviços ativos e lançamentos por período, com o
  valor agregado por cliente e um resumo por status.
- **Criação de lançamento** para um cliente × regra de serviço
  × período de referência.
- **Cálculo de valores** por tipo de regra: `valor fixo`, `valor variável`,
  `multiplicação`, `porcentagem` e `faixas`.
- **Alteração, exclusão e replicação** de lançamentos, com bloqueio otimista.
- **Criação, Alteração e exclusão** de serviços.
- **Máquina de estados de aprovação** e registro de cada transição .
- **Anexos** ao lançamento, com validação de tipo e tamanho.
- **Notificação em tempo real** de faturamento via websocket

### Quais informações são armazenadas ou transmitidas

- **Informações armazenadas:** faturamentos de cliente por período, serviços, lançamentos e seus
  valores, histórico de transições (auditoria), anexos e seus metadados
- **Transmitidas:** payloads REST de criação/alteração/remoção, eventos WebSocket,
  com o resumo de status e os dados do cliente afetado, URLs assinadas temporárias para
  download de anexos

### Quais recursos precisam ser protegidos

Os valores financeiros e sua trilha de aprovação, os CNPJs de clientes e fornecedores, os
anexos, as credenciais/segredos de assinatura de token e de callback, e o próprio motor de
cálculo — detalhados na seção 8.3.

---

## Usuários, ativos e pontos de interação

### Usuários e perfis de acesso

| Ação / Transição                    | `admin` | `gestor` | `analista` | `none` |
| ----------------------------------- | :-----: | :------: | :--------: | :----: |
| **Enviar para aprovação da gestão** |   ✅    |    ❌    |     ✅     |   ❌   |
| **Aprovar**                         |   ✅    |    ✅    |     ❌     |   ❌   |
| **Reprovar**                        |   ✅    |    ✅    |     ❌     |   ❌   |

### Inventário de ativos

Legenda de criticidade: 🔴 alta · 🟡 média.

| Identificador | Ativo                                                      | Tipo                 | Crít. | Por que importa (impacto se comprometido)                                      |
| ------------- | ---------------------------------------------------------- | -------------------- | :---: | ------------------------------------------------------------------------------ |
| A1            | Lançamentos e faturamentos (valores por cliente × período) | Dado                 |  🔴   | Adulteração muda o valor real faturado ao cliente.                             |
| A2            | Timeline de transições e auditoria                         | Dado                 |  🔴   | Prova de quem fez o quê, sua perda inviabiliza auditoria e contestação.        |
| A3            | Regras de serviço e faixas (base do cálculo)               | Dado                 |  🔴   | Erro/adulteração se propaga silenciosamente para todo valor calculado.         |
| A4            | Anexos dos lançamentos                                     | Dado                 |  🟡   | Documentos de suporte ao faturamento, podem conter dados de negócio sensíveis. |
| A5            | CNPJ de clientes e fornecedores                            | Dado pessoal/negócio |  🟡   | Dado identificável de pessoa jurídica, exposição indevida e vazamento.         |
| A6            | E-mails corporativos de aprovadores                        | Dado pessoal         |  🟡   | Alvo de phishing, usado no fluxo de aprovação por e-mail.                      |
| A7            | Motor de cálculo de valores                                | Código               |  🔴   | Core de todo calculo, bug ou adulteração fatura errado em escala.              |
| A8            | Máquina de estados com guards de autorização               | Código               |  🔴   | Único ponto entre o token e a mutação, falha pode burla o fluxo de aprovação.  |
| A9            | `JWT_SECRET`                                               | Segredo              |  🔴   | Vazamento permite forjar token com roles de `admin`.                           |
| A10           | `CELERY_CALLBACK_SECRET`                                   | Chave                |  🔴   | Única barreira dos callbacks internos.                                         |
| A11           | Credenciais/URLs de storage                                | Chave                |  🔴   | Acesso direto aos anexos fora do controle da aplicação.                        |
| A12           | PostgreSQL                                                 | Infra                |  🔴   | Dados dos lançamentos, serviços e roles                                        |
| A13           | `EMAIL_SERVICE_API_KEY`                                    | Chave                |  🔴   | Permite enviar e-mail em nome da empresa, spoofing de cobrança ao cliente.     |
| A14           | `EMAIL_SERVICE_API_KEY`                                    | Chave                |  🔴   | Permite enviar e-mail em nome da empresa, spoofing de cobrança ao cliente.     |
| A15           | EventBus WebSocket, validação canal `billing:{AAAA-MM}`    | Código / Infra       |  🟡   | inscrição indevida vaza o estado de faturamento do período.                    |

---

## Visão geral da arquitetura

Esta seção apresenta os principais diagramas que representam a arquitetura e os fluxos do sistema.

### Diagrama geral

O diagrama abaixo apresenta uma visão geral da arquitetura do sistema, destacando seus principais componentes e a comunicação entre eles.

![Diagrama geral da arquitetura](./diagramas/fluxo-geral.png)

### Fluxo de criação de lançamento

O diagrama de sequência apresenta o fluxo de criação de um lançamento, detalhando a interação entre os principais componentes envolvidos no processo.

![Diagrama de sequência — criação de lançamento](./diagramas/diagrama-sequencia.png)

### Fluxo de regra de serviço

O diagrama abaixo apresenta o fluxo de execução das regras de serviço, destacando a interação entre os principais componentes envolvidos no processamento.

![Diagrama de sequência — regra de serviço](./diagramas/diagrama-regra-servico.png)
