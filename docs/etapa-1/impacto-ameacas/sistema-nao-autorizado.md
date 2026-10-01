# Sistemas não autorizados

Esse documento descreve os impactos relacionados a sistemas não autorizados contra os [ativos](../etapa-1-identificacao-sistema.md) do sistema.

## Problema

Sistemas não autorizados, que façam uso de dados vazados, segredos ou chaves do sistema, podem interferir no funcionamento do sistema, quer gerando requisições inválidas, quer enviando SPAM, ou mesmo floodando subsistemas de forma a impedir o bom funcionamento do sistema.

## Ameaças relacionadas

T15, T17, T18, T21.

## Ativos afetados

A9, A10, A13.

## Dimensões de impacto

- **Financeiro:** operações forjadas e fraudes de cobrança por e-mail em nome da empresa.
- **Operacional:** estados falsos injetados no processamento assíncrono e necessidade de rotacionar segredos.
- **Legal/regulatório:** clientes e aprovadores vítimas de phishing enviado em nome da empresa.
- **Reputacional:** o canal de e-mail e a identidade da empresa passam a ser usados contra seus próprios clientes.

## Exemplo concreto

Com o `CELERY_CALLBACK_SECRET` vazado, um serviço externo chama os callbacks internos como se fosse um worker legítimo e marca tarefas de exportação como concluídas ou injeta notificações falsas para os usuários.

## Escala de severidade

| Nível | Descrição |
| :---: | --------- |
| 1 — Insignificante | Requisições forjadas rejeitadas ou sem efeito. |
| 2 — Baixo | Notificações ou mensagens falsas pontuais, sem alteração de dados. |
| 3 — Moderado | Estados falsos no processamento assíncrono ou envio de e-mails maliciosos em nome da empresa. |
| 4 — Grave | Forja de tokens com qualquer perfil, inclusive `admin`, comprometendo todo o sistema. |
