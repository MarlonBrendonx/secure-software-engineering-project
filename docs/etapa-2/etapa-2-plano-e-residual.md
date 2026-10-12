# Etapa 2 — Plano de tratamento e risco residual

## Plano dos riscos acrescentados (R24–R29)

Esta seção contempla os seis riscos acrescentados para completar a cobertura dos casos de abuso. O plano de R01–R23 ainda precisa ser elaborado neste documento.

Os controles abaixo são propostas. As estimativas residuais pressupõem implementação e validação satisfatórias; não representam controles existentes nem aceitação automática. Mantém-se o impacto e estima-se redução da probabilidade para 1, pois a consequência continua possível se o controle falhar. A classificação segue os critérios da Etapa 2.

| Risco | Onda | Responsável proposto | Tratamento | Evidência para validar | Residual estimado (P×I) |
| --- | --- | --- | --- | --- | --- |
| R24 | 5 | Equipe de backend e segurança com gestão de negócio | Validar destinatários autorizados por cliente no servidor; registrar destinatário, usuário e lançamento; alertar sobre desvios. | Envio para terceiro é negado; envio autorizado funciona e fica registrado. | 1×3 = 3 (Baixo) |
| R25 | 1 | Equipe de backend e segurança | Rotacionar refresh tokens e detectar reutilização; revogar a família de tokens e as sessões comprometidas. | Token reutilizado é rejeitado e sua família é revogada; sessão revogada não é renovada. | 1×4 = 4 (Médio) |
| R26 | 2 | Equipe de backend e segurança | Persistir evento de auditoria de forma durável e vinculada à operação; usar entrega com repetição e reconciliação; alertar sobre falhas. | Interrupção após alteração não perde evento; repetição não duplica registro e falha gera alerta. | 1×4 = 4 (Médio) |
| R27 | 2 | Equipe de backend e segurança com gestão de negócio | Exigir reautenticação adicional em aprovações críticas; preservar identidade, sessão, horário e conteúdo aprovado em trilha protegida. | Aprovação crítica exige reautenticação e preserva vínculo entre identidade, sessão e conteúdo. | 1×3 = 3 (Baixo) |
| R28 | 2 | Equipe de backend e segurança | Negar acesso quando a autorização falhar; testar exceções e indisponibilidade de dependências dos guards; registrar tentativas negadas. | Exceções no guard negam acesso e nenhuma operação restrita é efetivada. | 1×4 = 4 (Médio) |
| R29 | 2 | Equipe de backend e segurança | Aplicar proteção anti-CSRF e validação de origem nas rotas autenticadas por cookie; configurar SameSite adequado e testar requisições entre origens. | Requisição induzida de outra origem é rejeitada; fluxo legítimo continua funcionando. | 1×4 = 4 (Médio) |

A aceitação de qualquer residual depende do registro de motivo, aprovador, condição e data de revisão, conforme a seção 6.3 do documento de estratégias e NIST CSF.
