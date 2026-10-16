# Etapa 2 — Plano de tratamento e risco residual

Este documento contempla o plano de tratamento de cada risco (R01–R29), a ordem de implementação dos controles e a estimativa do risco residual. As estratégias escolhidas e o mapeamento ao NIST CSF 2.0 estão no  documento [Estratégias de tratamento e NIST CSF](etapa-2-nist-csf.md); as pontuações atuais e a priorização, em [Avaliação e priorização](etapa-2-avaliacao-e-priorizacao.md).

## 9. Plano de tratamento por risco

### 9.1 Premissas

Os controles abaixo são propostas. As estimativas residuais pressupõem implementação e validação satisfatórias; não representam controles existentes nem aceitação automática. Mantém-se o impacto e estima-se redução da probabilidade para 1, pois a consequência continua possível se o controle falhar. A classificação segue os critérios da Etapa 2.

### 9.2 Plano dos riscos R01–R23

| Risco | Estágio | Responsável proposto | Tratamento | Evidência para validar | Residual estimado (P×I) |
| --- | --- | --- | --- | --- | --- |
| R01 | 2 | Equipe de backend e segurança com gestão de negócio | Definir a matriz de quem escreve lançamentos e restringir a escrita ao mínimo necessário por perfil; impedir alteração ou remoção após o envio sem que o lançamento volte à aprovação; alertar sobre alterações fora do padrão de valor, volume ou horário; diante de abuso, bloquear o usuário, congelar o período e recompor o valor pela auditoria antes do envio ao ERP. | Perfil sem permissão não altera lançamento; alteração após o envio devolve o lançamento à aprovação; alteração anômala gera alerta; valor recomposto pela auditoria confere com o original. | 1×4 = 4 (Médio) |
| R02 | 1 | Equipe de segurança e identidade (SSO) | Exigir MFA no SSO, obrigatório para `admin` e `gestor`; detectar sessão anômala (dispositivo, local, horário) e falhas repetidas no segundo fator; diante de comprometimento, bloquear o usuário, revogar as sessões ativas e congelar o período. | Login de perfil privilegiado sem segundo fator é negado; falhas repetidas no segundo fator geram alerta; conta bloqueada perde as sessões ativas. | 1×4 = 4 (Médio) |
| R03 | 3 | Equipe de backend e segurança | Verificar, além do guard `require_role`, o escopo do recurso (cliente, período, dono) em cada requisição, inclusive nos endpoints de anexo e nas consultas; usar identificadores não sequenciais onde forem expostos; criar testes automatizados de autorização por rota com troca de identificadores entre usuários. | Requisição com identificador de outro escopo é negada em todas as rotas; a suíte de testes de autorização cobre todas as rotas e roda no CI. | 1×3 = 3 (Baixo) |
| R04 | 3 | Equipe de infraestrutura e backend | Emitir URLs assinadas de curta duração, de uso único quando possível, com escopo restrito ao objeto e somente após a autorização da aplicação; bloquear o acesso público ao contêiner; guardar as credenciais do storage no cofre, com rotação; registrar a emissão de cada URL. | URL expirada ou de outro objeto é recusada; acesso direto ao contêiner sem assinatura falha; a emissão da URL fica registrada com usuário e anexo. | 1×3 = 3 (Baixo) |
| R05 | 3 | Equipe de backend e segurança com encarregado de dados (LGPD) | Limitar volume de leitura, paginação e exportação por usuário e período; monitorar as ações de cada usuário para detectar extração anômala; bloquear temporariamente o usuário e acionar a resposta a incidentes, com comunicação ao encarregado de dados quando houver dado pessoal. | Exportação acima do limite é bloqueada; extração em volume gera alerta e bloqueio temporário; o procedimento de comunicação LGPD está definido e testado. | 1×4 = 4 (Médio) |
| R06 | 1 | Equipe de segurança e DevOps | Manter o `JWT_SECRET` apenas no cofre corporativo, sem cópia em repositório, imagem, log ou configuração; definir rotação periódica e rotação emergencial; manter o Gitleaks local e no CI, estendendo a varredura ao histórico do repositório e às imagens; restringir e registrar a leitura do segredo no cofre. | Varredura de repositório, histórico e imagens não encontra o segredo; cada leitura do segredo fica registrada no cofre; a rotação é executada sem interromper o serviço. | 1×4 = 4 (Médio) |
| R07 | 1 | Equipe de backend e segurança | Validar no token, além da assinatura, emissor, audiência e expiração curta, e vinculá-lo a uma sessão registrada no servidor; monitorar ações anômalas por usuário; com vazamento confirmado (R06), substituir o `JWT_SECRET`, invalidar os tokens emitidos e reverter as operações de escrita feitas com tokens forjados. | Token sem sessão registrada ou assinado com a chave antiga é rejeitado; a rotação emergencial invalida os tokens anteriores; o procedimento de reversão foi testado. | 1×4 = 4 (Médio) |
| R08 | 2 | Equipe de backend e segurança | Gravar a timeline de auditoria em armazenamento somente de inserção, sem operação de alteração ou remoção pela aplicação; encadear os registros por hash para detectar lacunas; separar quem administra a auditoria de quem opera lançamentos. | Tentativa de alterar ou remover registro é negada; a verificação do encadeamento detecta registro removido ou alterado; nenhum perfil da aplicação apaga a timeline. | 1×4 = 4 (Médio) |
| R09 | 2 | Equipe de backend com gestão de negócio | Definir a matriz de quem altera regras de serviço e faixas; versionar as regras com vigência e exigir aprovação de um segundo usuário antes de ativar uma versão; registrar alterações em log protegido e alertar sobre cada mudança; recalcular os faturamentos afetados a partir da versão correta. | Alteração sem segunda aprovação não entra em vigor; cada cálculo identifica a versão da regra usada; reversão de versão e recálculo do período afetado foram testados. | 1×4 = 4 (Médio) |
| R10 | 2 | Equipe de desenvolvimento e DevOps | Manter os controles existentes (Mypy strict, testes, PR-Agent, Trivy, cooldown de dependências) e acrescentar proteção da branch principal com revisão obrigatória por outra pessoa, bloqueio de merge com teste ou varredura falhando, testes de regressão do motor de cálculo com valores de referência, assinatura dos artefatos de build e inventário de dependências (SBOM). | Merge sem revisão ou com teste falhando é bloqueado; o teste de referência detecta mudança no resultado do cálculo; artefato sem assinatura não é implantado. | 1×4 = 4 (Médio)¹ |
| R11 | 4 | Equipe de backend | Aplicar rate limit por usuário e por operação também às transições da máquina de estados, além dos limites já existentes para lote e criação; reduzir o custo dos guards com cache de permissões de curta duração, invalidado na mudança de perfil; monitorar picos de requisições. | Excesso de transições recebe resposta 429 sem afetar outros usuários; em teste de carga, o fluxo de aprovação continua disponível. | 1×2 = 2 (Baixo) |
| R12 | 1 | Equipe de segurança e DevOps | Aplicar o mesmo tratamento de R06 ao `CELERY_CALLBACK_SECRET`: cofre, rotação periódica e emergencial, varredura com Gitleaks e leitura do segredo restrita aos serviços que emitem callbacks. | Varredura de repositório, histórico e imagens não encontra o segredo; somente os serviços autorizados leem o segredo; a rotação é executada sem perda de callbacks. | 1×4 = 4 (Médio) |
| R13 | 1 | Equipe de backend e infraestrutura | Validar a origem dos callbacks por rede interna restrita ou mTLS, além da chave; assinar o corpo com HMAC e carimbo de tempo para impedir repetição; aplicar idempotência por identificador da tarefa; monitorar callbacks anômalos; substituir o segredo se o vazamento for confirmado. | Callback de origem não autorizada é rejeitado mesmo com a chave correta; callback repetido não gera nova operação; corpo alterado invalida a assinatura. | 1×3 = 3 (Baixo) |
| R14 | 4 | Equipe de infraestrutura e DBA | Configurar pool e limite de conexões por aplicação, tempo máximo de consulta e limites para consultas pesadas; adotar serviço de banco escalável, com réplica, failover e backups testados; monitorar carga, conexões e lentidão com alertas; definir plano de recuperação com tempo e ponto de recuperação. | Teste de carga não esgota as conexões; o failover para a réplica funciona em teste; a restauração de backup cumpre o tempo definido. | 1×4 = 4 (Médio) |
| R15 | 5 | Equipe de segurança com o provedor de e-mail | Manter a `EMAIL_SERVICE_API_KEY` no cofre, com rotação e escopo mínimo no provedor; publicar SPF, DKIM e DMARC com política de rejeição para o domínio; monitorar volume e destinos de envio; prever em contrato a detecção de abuso da conta pelo provedor. | E-mail forjado enviado de outro servidor é rejeitado pelo DMARC; a chave rotacionada deixa de funcionar; pico de envio gera alerta. | 1×3 = 3 (Baixo) |
| R16 | 4 | Equipe de backend e infraestrutura | Exigir autenticação na abertura da conexão WebSocket; limitar conexões por usuário e por IP e aplicar quota de mensagens por conexão; confirmar que o rate limit global de 60/min por IP cobre o `/ws`; garantir que o frontend recarregue o estado pela API REST quando a notificação falhar. | Conexões acima do limite são recusadas; teste de carga no `/ws` não derruba o EventBus; a falha do WebSocket não impede consultar o estado do faturamento. | 1×2 = 2 (Baixo) |
| R17 | 3 | Equipe de backend | Verificar, na inscrição, o perfil e o escopo do usuário para o canal `billing:{AAAA-MM}`, negando por padrão; revalidar a autorização quando a sessão ou o perfil mudar; registrar as inscrições negadas. | Usuário sem permissão não recebe eventos do canal; a perda do perfil encerra a inscrição; a tentativa negada fica registrada. | 1×2 = 2 (Baixo) |
| R18 | 2 | Equipe de backend com gestão de negócio | Formalizar a política de segregação de funções: quem cria ou envia um lançamento não o aprova, inclusive o `admin`; aplicar a regra no servidor, na transição de aprovação, comparando autor e aprovador; exigir dois aprovadores distintos acima de um valor definido pela gestão; alertar sobre tentativas de autoaprovação. | O autor do lançamento, inclusive `admin`, recebe negativa ao aprovar; a tentativa fica registrada e gera alerta; o fluxo com aprovador distinto funciona. | 1×4 = 4 (Médio) |
| R19 | 3 | Equipe de backend | Usar bindvars em todas as consultas de `queries/`, sem concatenar valores; validar por lista permitida os parâmetros que não aceitam bind (ordenação, nomes de coluna); manter o usuário Oracle somente leitura e restrito às visões necessárias; incluir no CI análise estática para SQL concatenado e testes com entradas maliciosas. | A análise estática não encontra SQL concatenado; teste com carga de injeção não altera o resultado da consulta; o usuário Oracle não lê objetos fora do escopo. | 1×3 = 3 (Baixo) |
| R20 | 1 | Equipe de DevOps e backend | Retirar o provedor `local` e o modo `DEBUG` do build de produção, ou impedir a inicialização quando estiverem ativos nesse ambiente; validar as variáveis de ambiente no pipeline e bloquear o deploy inseguro; desativar `/docs` em produção; orientar a equipe sobre a verificação antes do deploy. | Deploy para produção com `DEBUG=true` ou provedor `local` é bloqueado no pipeline; a aplicação não inicia com essa configuração; `/docs` não responde em produção. | 1×4 = 4 (Médio)² |
| R21 | 4 | Equipe de infraestrutura e DBA | Separar produção e QA em instâncias distintas e, até essa separação, limitar recursos por usuário (conexões, tempo de consulta); usar credenciais diferentes por ambiente, guardadas no cofre, sem permissão de QA no schema de produção; executar migrations e testes de carga apenas na instância de QA. | A credencial de QA não acessa o schema de produção; teste de carga em QA não altera a latência de produção; o inventário confirma credenciais distintas por ambiente. | 1×4 = 4 (Médio) |
| R22 | 3 | Equipe de segurança e backend | Varrer os anexos com antivírus e detecção de conteúdo ativo (macros, polyglot) antes de disponibilizá-los; colocar arquivos suspeitos em quarentena e bloquear o download; converter documentos para formato sem conteúdo ativo ou abri-los em visualizador isolado; registrar e reportar o usuário que anexou o arquivo. | O arquivo de teste EICAR e um documento com macro ficam em quarentena; o aprovador não baixa arquivo suspeito; o evento registra o usuário que enviou o anexo. | 1×3 = 3 (Baixo) |
| R23 | 2 | Equipe de backend com a equipe do ERP | Tratar os campos textuais exportados para que não sejam interpretados como fórmula (escapar valores iniciados por `=`, `+`, `-` ou `@`); calcular hash ou assinar o arquivo de carga na geração e verificá-lo antes da importação no ERP; restringir a escrita no local de armazenamento; reportar tentativas de inserir conteúdo malicioso; regenerar o arquivo pelo sistema quando a verificação falhar. | Campo iniciado por `=` é exportado como texto; arquivo alterado após a geração é recusado na importação; o arquivo regenerado confere com o original. | 1×4 = 4 (Médio) |

¹ A probabilidade de R10 já era 1, de modo que a pontuação residual não muda. Os controles reforçam a confiança nessa estimativa e encurtam o tempo de detecção, mas o risco permanece Médio e depende de aceitação(seção 12).

² R20 tem estratégia **Evitar**: os controles eliminam a condição em produção. A escala não tem valor abaixo de 1, por isso a probabilidade residual é 1, e o risco restante corresponde a uma falha do próprio bloqueio no pipeline.

### Plano dos riscos acrescentados (R24–R29)

Esta seção contempla os seis riscos acrescentados para completar a cobertura dos casos de abuso. O plano de R01–R23 ainda precisa ser elaborado neste documento.


| Risco | Estágio | Responsável proposto | Tratamento | Evidência para validar | Residual estimado (P×I) |
| --- | --- | --- | --- | --- | --- |
| R24 | 5 | Equipe de backend e segurança com gestão de negócio | Validar destinatários autorizados por cliente no servidor; registrar destinatário, usuário e lançamento; alertar sobre desvios. | Envio para terceiro é negado; envio autorizado funciona e fica registrado. | 1×3 = 3 (Baixo) |
| R25 | 1 | Equipe de backend e segurança | Rotacionar refresh tokens e detectar reutilização; revogar a família de tokens e as sessões comprometidas. | Token reutilizado é rejeitado e sua família é revogada; sessão revogada não é renovada. | 1×4 = 4 (Médio) |
| R26 | 2 | Equipe de backend e segurança | Persistir evento de auditoria de forma durável e vinculada à operação; usar entrega com repetição e reconciliação; alertar sobre falhas. | Interrupção após alteração não perde evento; repetição não duplica registro e falha gera alerta. | 1×4 = 4 (Médio) |
| R27 | 2 | Equipe de backend e segurança com gestão de negócio | Exigir reautenticação adicional em aprovações críticas; preservar identidade, sessão, horário e conteúdo aprovado em trilha protegida. | Aprovação crítica exige reautenticação e preserva vínculo entre identidade, sessão e conteúdo. | 1×3 = 3 (Baixo) |
| R28 | 2 | Equipe de backend e segurança | Negar acesso quando a autorização falhar; testar exceções e indisponibilidade de dependências dos guards; registrar tentativas negadas. | Exceções no guard negam acesso e nenhuma operação restrita é efetivada. | 1×4 = 4 (Médio) |
| R29 | 2 | Equipe de backend e segurança | Aplicar proteção anti-CSRF e validação de origem nas rotas autenticadas por cookie; configurar SameSite adequado e testar requisições entre origens. | Requisição induzida de outra origem é rejeitada; fluxo legítimo continua funcionando. | 1×4 = 4 (Médio) |

A aceitação de qualquer residual depende do registro de motivo, aprovador, condição e data de revisão, conforme a seção 6.3 do documento de estratégias e NIST CSF.

---

## 10. Ordem de implementação

A implementação segue os estágios da seção 5.3. Dentro de cada estágio, os riscos aparecem na ordem da [tabela de priorização](etapa-2-avaliacao-e-priorizacao.md#52-tabela-de-priorização) (seção 5.2), respeitando as dependências: R06 antes de R07, R12 antes de R13 e R21 antes de R14.

| Estágio | Tema | Riscos, em ordem de implementação | Entrega que encerra o estágio |
| :--: | ---- | --------------------------------- | -------------------------- |
| 1 | Identidade e segredos | R02, R06, R12, R07, R20, R13, R25 | MFA ativo para perfis privilegiados, segredos em cofre com rotação testada, tokens vinculados a sessão, deploy inseguro bloqueado, callbacks com origem validada e HMAC, rotação de refresh token |
| 2 | Integridade do valor faturado | R01, R18, R09, R10, R08, R23, R26, R27, R28, R29 | Segregação de funções, regras versionadas com dupla aprovação, revisão obrigatória no pipeline, auditoria imutável e durável, arquivo do ERP com verificação de integridade, guards que negam em falha, proteção anti-CSRF |
| 3 | Confidencialidade | R03, R05, R22, R04, R19, R17 | Testes de autorização por rota, limites de exportação, varredura de anexos, URLs de curta duração, bindvars verificados no CI, autorização por canal |
| 4 | Disponibilidade | R21, R14, R11, R16 | Instâncias de produção e QA separadas, limites de conexão, réplica com failover, rate limit nas transições e no `/ws` |
| 5 | Canal externo | R15, R24 | SPF/DKIM/DMARC com política de rejeição, destinatário vinculado ao cadastro do cliente |

Consideando que os riscos R19, R20, R21, R22 e R23 não constam da tabela da seção 5.3, eles foram encaixados nos estágios pelo controle que compartilham:

- **R20, estágio 1:** reabre a autenticação local, o que o coloca no tema identidade.
- **R23, estágio 2:** a adulteração da carga atinge o valor que chega ao ERP.
- **R19 e R22, estágio 3:** expõem dados legados (R19) e atacam pelos anexos, o mesmo ponto de R04 (R22).
- **R21, estágio 4:** a seção 5.2 já o trata antes de R14, como causa de indisponibilidade do banco de produção.

A ordem leva em conta a dependência entre riscos: o estágio 1 vem primeiro porque uma conta capturada ou um segredo vazado contornam os controles dos estágios seguintes.

---

## 11. Risco residual depurado

| Risco | Atual (P×I) | Nível atual | Residual (P×I) | Nível residual |
| ----- | :---------: | ----------- | :------------: | -------------- |
| R01 | 3×4 = 12 | Crítico | 1×4 = 4 | Médio |
| R02 | 3×4 = 12 | Crítico | 1×4 = 4 | Médio |
| R03 | 3×3 = 9 | Alto | 1×3 = 3 | Baixo |
| R04 | 2×3 = 6 | Médio | 1×3 = 3 | Baixo |
| R05 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R06 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R07 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R08 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R09 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R10 | 1×4 = 4 | Médio | 1×4 = 4 | Médio |
| R11 | 2×2 = 4 | Médio | 1×2 = 2 | Baixo |
| R12 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R13 | 2×3 = 6 | Médio | 1×3 = 3 | Baixo |
| R14 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R15 | 2×3 = 6 | Médio | 1×3 = 3 | Baixo |
| R16 | 3×2 = 6 | Médio | 1×2 = 2 | Baixo |
| R17 | 2×2 = 4 | Médio | 1×2 = 2 | Baixo |
| R18 | 3×4 = 12 | Crítico | 1×4 = 4 | Médio |
| R19 | 2×3 = 6 | Médio | 1×3 = 3 | Baixo |
| R20 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R21 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R22 | 2×3 = 6 | Médio | 1×3 = 3 | Baixo |
| R23 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R24 | 2×3 = 6 | Médio | 1×3 = 3 | Baixo |
| R25 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R26 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R27 | 2×3 = 6 | Médio | 1×3 = 3 | Baixo |
| R28 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |
| R29 | 2×4 = 8 | Alto | 1×4 = 4 | Médio |

| Nível | Riscos atuais | Riscos residuais |
| ----- | :-----------: | :--------------: |
| Crítico | 3 | 0 |
| Alto | 15 | 0 |
| Médio | 11 | 18 |
| Baixo | 0 | 11 |
| **Total** | **29** | **29** |

Após o tratamento, nenhum risco permanece Alto ou Crítico. Os 18 riscos
residuais Médios têm impacto 4: a probabilidade foi reduzida ao mínimo da
escala, mas a consequência, se o controle falhar, continua grave. Por isso eles
exigem aceitação formal e acompanhamento (seção 12), e não apenas registro.

---

## 12. Aceitação do risco residual

As aceitações abaixo são **propostas**: só valem depois de aprovadas por quem
consta na coluna Aprovador, com os quatro itens exigidos pela
[regra de aceitação](etapa-2-nist-csf.md#63-regra-para-aceitação-de-risco)
(seção 6.3). Em todas, a condição inclui a validação da evidência prevista no
plano; sem ela, vale a pontuação atual, e não a residual.

### 12.1 Residuais Médios

| Riscos | Motivo | Aprovador | Condição | Data de revisão |
| ------ | ------ | --------- | -------- | --------------- |
| R01, R09, R18, R23 | Escrever lançamentos, manter regras e gerar a carga do ERP são funções do negócio; o resíduo é o abuso por quem tem permissão legítima e consegue contornar a segregação. | Gestão da área de negócio com o líder técnico | Segregação de funções, dupla aprovação de regras, auditoria imutável e verificação do arquivo do ERP validadas e ativas | 15/04/2027 ou após incidente de fraude |
| R02, R07, R25 | Autenticação por SSO e token é necessária; o resíduo é o roubo de sessão que passa pelo MFA e pela detecção de anomalia. | Gestão de segurança | MFA obrigatório para perfis privilegiados, tokens vinculados a sessão e rotação de refresh token validados | 15/04/2027 ou após comprometimento de conta |
| R06, R12 | Os segredos precisam existir para assinar tokens e callbacks; o resíduo é o vazamento por quem tem acesso ao cofre. | Gestão de segurança | Segredos apenas no cofre, leitura registrada e rotação emergencial testada | 15/04/2027 ou após vazamento confirmado |
| R05 | Leitura e exportação atendem ao negócio; o resíduo é a extração lenta, abaixo dos limites. | Gestão de segurança com o encarregado de dados | Limites de exportação e alertas de extração ativos | 15/04/2027 ou após incidente com dado pessoal |
| R08, R26 | A auditoria existe e passa a ser imutável e durável; o resíduo é a falha simultânea do armazenamento e da reconciliação. | Líder técnico com gestão de segurança | Encadeamento por hash verificado e reconciliação de eventos sem lacunas | 15/04/2027 |
| R10 | O núcleo de cálculo depende de código e dependências de terceiros; o resíduo é um ataque à cadeia de suprimentos que passe pela revisão e pelos testes. | Líder técnico | Proteção de branch, testes de referência e assinatura de artefatos ativos | 15/04/2027 ou após alerta de dependência comprometida |
| R14, R21 | O sistema depende do banco de dados; o resíduo é a falha simultânea da instância principal e da réplica. | Gestão de infraestrutura | Failover e restauração testados, instâncias de produção e QA separadas | 15/04/2027 |
| R20 | Os modos `local` e `DEBUG` seguem úteis fora de produção; o resíduo é a falha do bloqueio no pipeline. | Líder técnico | Verificação de configuração obrigatória no pipeline de produção | 15/04/2027 ou após mudança no pipeline |
| R28, R29 | O guard e a proteção anti-CSRF passam a negar em caso de falha; o resíduo é uma rota nova sem cobertura de teste. | Líder técnico com gestão de segurança | Testes de falha do guard e de requisição entre origens cobrindo todas as rotas mutantes | 15/04/2027 ou ao incluir rota mutante |

### 12.2 Residuais Baixos

R03, R04, R11, R13, R15, R16, R17, R19, R22, R24 e R27 ficam em nível Baixo e podem ser aceitos em bloco, com o motivo de que o custo de controles adicionais supera o benefício. O aprovador proposto é o líder técnico, e a condição é manter ativos os controles da seção 9. A revisão ocorre em 15/04/2027 ou quando a avaliação mudar (nova rota, novo canal ou novo provedor).
