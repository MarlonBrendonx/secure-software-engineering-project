# Etapa 6 — Objetivos, eventos e fontes de dados

Este documento define o que o monitoramento precisa perceber, quais eventos a aplicação deve registrar para isso e de onde vêm os dados que as [regras de detecção](etapa-6-regras-de-deteccao.md) usam.

## Objetivos de monitoramento

O monitoramento proposto deve permitir:

- perceber o uso de uma conta privilegiada capturada (R02) antes que ela aprove ou altere lançamentos, a partir das falhas no segundo fator, das falhas de senha e dos logins fora do padrão;
- perceber a busca de dados fora do escopo (R03) e a extração em volume (R05), que a resposta `404` esconde do atacante, mas não deve esconder da equipe de segurança;
- perceber tentativas de mudar o valor faturado por fora da máquina de estados (R01, R18) e mudanças em regras de serviço (R09), que alteram valores de forma silenciosa;
- perceber o uso de tokens forjados, de sessões revogadas e de refresh tokens reaproveitados (R06, R07, R25 e o achado V01);
- perceber quando os próprios controles falham: guard indisponível (R28), auditoria com lacuna (R26) e carga do ERP divergente (R23);
- reconstruir, depois de um alerta, quem fez o quê, de onde, com qual sessão e sobre qual registro, para conter, corrigir e recompor os valores.

## Eventos mínimos a registrar

Cada evento deve ter estes campos, além do tipo:

| Campo                   | Para que serve                                                  | No protótipo (`AuditEvent`)                                                     |
| ----------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Data e hora (UTC)       | Ordenar a linha do tempo                                        | `created_at`                                                                    |
| Usuário e perfil        | Saber quem agiu e com qual privilégio                           | Só `user`; o perfil não é gravado                                               |
| Sessão (`sid`)          | Ligar ações da mesma sessão e revogá-la                         | Não é gravado                                                                   |
| Origem (IP)             | Correlacionar contas atacadas pela mesma origem                 | `origin`, só nos eventos de login e de MFA                                      |
| Rota e método           | Saber qual operação foi tentada                                 | `route`, só em `mfa_ausente`                                                    |
| Recurso e identificador | Saber qual registro foi lido ou alterado                        | `resource` e `resource_id`                                                      |
| Operação e resultado    | Distinguir tentativa de efetivação e o motivo da recusa         | Parte em `detail`; o resultado não tem campo próprio                            |
| `request_id`            | Ligar o evento ao log da aplicação e à resposta dada ao cliente | Gerado pelo middleware e devolvido em `X-Request-ID`, mas não gravado no evento |

Os eventos que precisam existir, por grupo:

1. **Autenticação:** login com sucesso (com `amr`), login recusado por credenciais, código MFA recusado, token de perfil privilegiado sem MFA, renovação de sessão, reuso de refresh token, logout e revogação de sessão.
2. **Token e sessão:** token recusado por assinatura, algoritmo, `iss`, `aud`, `exp` ou `kid`, e token recusado por `sid` revogado ou inexistente.
3. **Autorização:** negação por escopo (cliente ou período), negação por perfil (`403`) e negação por falha do guard (`503`).
4. **Integridade do faturamento:** criação, alteração e exclusão de lançamento, cada transição de status, tentativa recusada de alteração após o envio, transição recusada e autoaprovação recusada.
5. **Cadastros:** criação, alteração e exclusão de regra de serviço, com os nomes dos campos alterados.
6. **Leitura e exportação:** consultas e exportações de lançamentos, com o volume devolvido.
7. **Plataforma:** requisição recusada por origem ou por token anti-CSRF, conexão WebSocket recusada, limite de requisições excedido, erro interno (`500`), falha na gravação da auditoria, atraso da outbox e divergência na reconciliação.
8. **Carga do ERP:** geração do arquivo, conferência do manifesto e bloqueio da importação.

Os grupos 1 (exceto renovação, reuso e revogação), 3 (só a negação por escopo), 4 (só as operações efetivadas) e 5 já são gravados pelo protótipo. Os demais dependem de controles ainda não implementados ou do registro de eventos que hoje só aparecem no log ou na resposta HTTP.

O registro não deve conter senha, código OTP, token nem valor de campo sensível. O protótipo já segue essa regra: `regra_servico_atualizada` grava só os nomes dos campos alterados.

## Fontes de dados e cobertura

| Fonte                                                      | Eventos principais                                                                                            | Uso                                                                                    |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Auditoria da API (`audit_logs`; `psp:audit` no protótipo)  | Login, logout, MFA, negação por escopo, mudanças em lançamentos e regras de serviço                           | Base das regras D01 a D04, D07 e D08 e da reconstrução da linha do tempo               |
| Contadores e alertas (`SecurityMonitor`, `psp:alerts`)     | Contagem por usuário em janela de 10 minutos e alertas disparados                                             | Disparo de D01 e D02; modelo para as demais regras de contagem                         |
| Log da aplicação (`psp.api`, `psp.api.ws`, `psp.security`) | Exceção no guard, erro `500`, fechamento do WebSocket por origem ou autenticação                              | D10 e D12 enquanto esses eventos não forem para a auditoria                            |
| Gateway, APIM ou proxy reverso                             | Código de resposta por rota, origem e usuário (`401`, `403`, `404`, `429`), volume por origem                 | D06, D09 e D13; visão de quem nunca chega a se autenticar                              |
| SSO corporativo (Keycloak)                                 | Login, falha de senha, falha de MFA, bloqueio de conta, novo dispositivo                                      | D01, D03 e D04 no sistema real, onde o login mock do protótipo dá lugar ao SSO         |
| Cofre de chaves (KMS)                                      | Cada uso da chave de assinatura do token e da chave do gerador da carga                                       | D06 (uso da chave fora do emissor, previsto em RS04)                                   |
| Outbox e reconciliação (RS05)                              | Atraso de entrega, falha de entrega, lacuna entre versões dos lançamentos e `audit_logs`                      | D11                                                                                    |
| Entrega da carga ao ERP (RS07)                             | Assinatura inválida, hash divergente, total diferente da soma aprovada                                        | D14                                                                                    |
| Pipeline de CI (Gitleaks, Dependency-Check)                | Segredo no repositório, dependência com CVE (como o `PyJWT` do V03)                                           | Não é detecção em execução; abre incidente quando há segredo exposto ou CVE explorável |

A auditoria do protótipo fica em uma lista do Redis limitada a 5.000 entradas (`_AUDIT_MAX_ENTRIES`), sem encadeamento por hash. Ela serve para testar as regras, mas não é a trilha protegida de C6 e não guarda histórico suficiente para uma investigação.

---
