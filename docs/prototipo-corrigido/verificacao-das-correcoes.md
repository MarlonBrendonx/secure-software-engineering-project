# Protótipo corrigido — Verificação das correções

Este documento registra a rodada de verificação do [protótipo corrigido](../../extra/prototipo-psp-corrigido/README.md). O objetivo é mostrar, com evidências, que parte dos controles propostos na [arquitetura segura da etapa 3](../etapa-3/etapa-3-arquitetura-segura.md) funciona quando implementada.

O [protótipo original](../../extra/prototipo-psp/README.md) fica como estava nas etapas 4 e 5, porque o objetivo daquelas etapas era mostrar as falhas e propor soluções, não corrigi-las. O protótipo corrigido é uma cópia dele com três correções. As duas versões passaram pelos mesmos testes, e a comparação entre elas é o resultado principal desta rodada.

## Resumo

| Requisito | Decisão e controle (etapa 3) | Original | Corrigido |
| --------- | ---------------------------- | -------- | --------- |
| **RS01**: nada muda depois do envio para aprovação, só pela transição "reabrir" | D01, C4 | `PATCH` e `DELETE` aceitos (`200` e `204`) | recusados (`422`); reabrir funciona (`200`) |
| **R18** (premissa de RS01): quem criou, enviou ou alterou não aprova | D01 | admin aprova o próprio lançamento (`200`) | recusado (`403`) e registrado na auditoria |
| **RS05**: auditoria na mesma transação da operação | D05, C11 | operação efetivada mesmo com falha na auditoria | operação desfeita quando a auditoria falha |
| RS02, RS03 e validação de RS04 (já existiam) | D02, D03, D04 | funcionam | continuam funcionando |
| RS04 assimétrico e RS08 (CSRF) | D04, D08 | não implementados | continuam não implementados |

Nenhum alerta Alto foi encontrado pelo ZAP, e nenhuma requisição da varredura derrubou o servidor. As duas CVEs que o Dependency-Check aponta são falsos positivos (veja a [seção 5](#5-análise-de-dependências)).

---

## 1. O que foi corrigido

As correções ficaram no backend. O frontend é o mesmo do original.

| Requisito | Onde | O que mudou |
| --------- | ---- | ----------- |
| RS01 | `src/domain/entities/billing.py` | Só os estados de rascunho (`New` e `Rejected`) aceitam `PATCH` e `DELETE` diretos. Foi criada a transição "reabrir", que devolve o lançamento a `New` a partir de `ManagementApproval`, `ClientApproval` ou `FinancialReview`. Só analista e admin podem reabrir, e o lançamento reaberto precisa ser enviado e aprovado de novo. |
| R18 | `ensure_segregation_of_duties` em `billing.py`, aplicada em `change_item_status.py` | Antes de qualquer transição que aprova (`ClientApproval`, `FinancialReview` ou `Approved`), o servidor lê a timeline do lançamento. Quem aparece como autor da criação, de uma alteração ou do envio recebe `403`, mesmo sendo admin. A tentativa fica registrada como `autoaprovacao_negada`. Em lote, um item nessa condição barra o lote inteiro. |
| RS05 | `queue_audit` em `security_gateways.py`, usada em `billing_gateways.py` | O evento de auditoria do lançamento entra no mesmo `MULTI/EXEC` do Redis que grava o item e a timeline. Ou os três são gravados, ou nenhum. Antes, a auditoria era gravada depois, em chamada separada. |

Na etapa 3, o RS01 fala em lançamento "enviado" e em estado `Rascunho`. No protótipo, o rascunho corresponde aos status `New` e `Rejected`.

## 2. Ambiente e ferramentas

Rodada executada em 12/11/2026, na máquina local, com os dados fictícios do seed (`analyst`, `manager`, `admin`).

| Item | Valor |
| ---- | ----- |
| Sistema testado | `extra/prototipo-psp-corrigido/` (e `extra/prototipo-psp/` para a comparação) |
| Backend | FastAPI, Python 3.14, em `http://localhost:8000` |
| Frontend | Next.js em modo de desenvolvimento (`pnpm dev`), em `http://localhost:3000` |
| Dados | Redis 7 em contêiner (`redis:7-alpine`) |
| Testes automatizados | pytest, com `fakeredis` |
| Verificação na API | script [`verificar_controles.py`](../../extra/prototipo-psp-corrigido/verificacao/verificar_controles.py) contra a API em execução |
| Varredura | ZAP 2.17.0 desktop |
| Navegador | Google Chrome 157, aberto com `--proxy-server=http://localhost:8080` e `--proxy-bypass-list="<-loopback>"` |
| Análise de dependências | OWASP Dependency-Check 13.0.0, em contêiner |

**Diferenças em relação à etapa 5**, todas escolhidas para corrigir limitações que a própria etapa 5 registrou:

| Item | Etapa 5 | Agora | Motivo |
| ---- | ------- | ----- | ------ |
| Validade do token de acesso | 15 minutos | 120 minutos (`ACCESS_TOKEN_EXPIRE_MINUTES=120`, só para a varredura) | o token expirava no meio do scan e gerava `401` |
| Rotas excluídas do contexto | nenhuma | `/v1/auth/logout` e `/v1/auth/refresh` | o scan derrubava a própria sessão |
| Threads por host no active scan | padrão | 2 | o scan atingia o limite de requisições (`429`) |
| Navegador | Firefox aberto pelo ZAP | Chrome configurado manualmente | o Firefox instalado como snap não abre o perfil temporário do ZAP, e o ChromeDriver do ZAP (143) não corresponde ao Chrome instalado (157). O navegador só gera tráfego pelo proxy e não muda o que o ZAP analisa. |
| Python do backend | 3.11 | 3.14 | versão disponível na máquina; muda o ferramental de build instalado no ambiente virtual (veja a seção 5) |

## 3. Verificação dos requisitos

### 3.1 Testes automatizados

A suíte do protótipo roda a aplicação real sobre `fakeredis`. O corrigido acrescenta o arquivo [`test_rs01_r18_rs05_integridade_do_lancamento.py`](../../extra/prototipo-psp-corrigido/backend/tests/test_rs01_r18_rs05_integridade_do_lancamento.py), que transforma em testes os critérios de verificação da [tabela de requisitos da etapa 3](../etapa-3/etapa-3-requisitos.md).

| Protótipo | Resultado |
| --------- | --------- |
| Original | 75 passaram |
| Corrigido | 88 passaram, 2 `xfail` |

Os 13 testes novos que passam cobrem:

- **RS01:**
  - `PATCH` e `DELETE` recusados em `ManagementApproval` e em `FinancialReview`;
  - rascunho e reprovado continuam editáveis;
  - reabrir exige novo envio e nova aprovação, e o gestor não pode reabrir;
  - `Approved` não reabre.
- **R18:**
  - o admin não aprova o próprio lançamento, e a tentativa fica na auditoria;
  - o admin que alterou o lançamento de outra pessoa também não o aprova;
  - o admin aprova normalmente o lançamento de outra pessoa;
  - um lote com um item de autoaprovação não muda nenhum item.
- **RS05:**
  - a alteração grava o item, a timeline e a auditoria juntos;
  - com uma falha injetada na gravação da auditoria, a alteração, a mudança de status e a exclusão não são efetivadas, e a versão do lançamento não muda.

Os dois `xfail` documentam o que não foi implementado: a assinatura assimétrica de RS04 e a proteção anti-CSRF de RS08. Eles são estritos, ou seja, passam a falhar se alguém implementar o controle sem remover a marcação.

O RS05 só pode ser verificado dessa forma. Não há como provocar, por uma requisição HTTP, uma falha na gravação da auditoria.

### 3.2 Ataques contra a API em execução

O script [`verificar_controles.py`](../../extra/prototipo-psp-corrigido/verificacao/verificar_controles.py) repete os ataques que motivaram os requisitos contra a API rodando de verdade, com o Redis limpo antes de cada execução. A mesma sequência rodou primeiro no original e depois no corrigido. A senha e o OTP do login mock foram gerados aleatoriamente para a execução e não ficam registrados.

| ID | Requisito | Ataque | Esperado | Original | Corrigido |
| -- | --------- | ------ | :------: | :------: | :-------: |
| V-01 | RS01 | `PATCH` em lançamento enviado para aprovação | 422 | 200 ✗ | 422 ✓ |
| V-02 | RS01 | `DELETE` em lançamento enviado para aprovação | 422 | 204 ✗ | 422 ✓ |
| V-03 | RS01 | reabrir o lançamento enviado (status `New`) | 200 | 422 ✗ | 200 ✓ |
| V-04 | R18 | admin aprova o próprio lançamento | 403 | 200 ✗ | 403 ✓ |
| V-05 | RS03 | analista lê lançamento de cliente fora do escopo | 404 | 404 ✓ | 404 ✓ |
| V-06 | RS02 | admin sem MFA escreve regra de serviço | 401 | 401 ✓ | 401 ✓ |
| V-07 | RS04 | token com `alg=none` | 401 | 401 ✓ | 401 ✓ |
| V-08 | RS08 | `PATCH` só com o cookie e `Origin` de outro site | 403 | 200 ✗ | 200 ✗ |

V-01 a V-04 mostram o efeito das correções. V-05 a V-07 mostram que as correções não quebraram os controles que já funcionavam. V-08 continua falhando nos dois protótipos, como esperado. Na V-08, o cliente HTTP do script não aplica o `SameSite=Strict` do cookie, como um navegador aplicaria. O resultado mostra que falta ao servidor a checagem própria que a D08 propõe para o caso de outro subdomínio do mesmo site.

### 3.3 Ataques manuais no ZAP

Os ataques V-01 e V-04 também foram repetidos à mão no Editor Manual de Requisições do ZAP, a mesma ferramenta da etapa 5. O lançamento foi criado pela tela como `admin` (cliente Drogaria Gama, 09/2026) e enviado para aprovação. Depois, a requisição de envio foi reenviada com outro conteúdo.

| Ataque | Requisição | Resposta | Evidência |
| ------ | ---------- | -------- | --------- |
| V-04 (R18) | `POST /v1/billing/items/batch-status` com `"new_status": "FinancialReview"` no lançamento que o próprio `admin` criou e enviou | `403 Forbidden`: "Quem criou, enviou ou alterou o lançamento não pode aprová-lo" | `zap-07-v04-autoaprovacao-req.png` e `-403.png` |
| V-01 (RS01) | `PATCH /v1/billing/items/{id}` com `{"version": 2, "notes": "alterado depois do envio"}` | `422`: "Lançamento com status 'ManagementApproval' não pode ser alterado nem excluído. Reabra o lançamento (status 'New') para alterá-lo." | `zap-06-v01-patch-apos-envio-req.png` e `-422.png` |

A tela envia a mudança de status pela rota de lote (`batch-status`), e não pela rota individual. A segregação de funções vale nas duas, como mostram o teste do lote e a V-04 do script.

## 4. Varredura com o ZAP

### 4.1 Configuração

- **Contexto:** `Faturamento-Corrigido`, com `http://localhost:3000.*` e `http://localhost:8000.*`, em modo Protegido.
- **Exclusões:** `/v1/auth/logout` e `/v1/auth/refresh`.
- **Rotas:** importadas de `http://localhost:8000/openapi.json`.
- **Autenticação:** regra "Token Admin" no Replacer, que injeta `Authorization: Bearer <token>` em todas as requisições. O token foi obtido no login do `admin` com MFA.
- **Varreduras:**
  - active scan no backend, com a política padrão;
  - Spider tradicional no frontend, com o passive scan ativo durante toda a navegação.

### 4.2 Alertas

| Alerta | Risco | Retest da etapa 5 | Agora |
| ------ | ----- | :---------------: | :---: |
| CSP: Failure to Define Directive with No Fallback | Médio | sim | sim |
| CSP: script-src unsafe-inline | Médio | sim | sim |
| CSP: style-src unsafe-inline | Médio | sim | sim |
| CSP: script-src unsafe-eval | Médio | não | sim |
| X-Powered-By no cabeçalho de resposta | Baixo | sim | sim |
| X-Content-Type-Options Header Missing | Baixo | sim | sim |
| Divulgação de Data e Hora (Unix) | Baixo | não | sim |
| Informativos | Info | 3 | 6 |
| **Total** | | **0 Alto, 3 Médio, 2 Baixo** | **0 Alto, 4 Médio, 3 Baixo** |

Os alertas que já existiam continuam, como esperado. Eles tratam de cabeçalhos HTTP e da política de CSP, que estão nas [correções propostas da etapa 5](../etapa-5/etapa-5-correcoes-propostas.md) e não fazem parte de RS01, R18 e RS05.

Os alertas novos não estão ligados às correções:
- **CSP `unsafe-eval`:** vem do modo de desenvolvimento do Next.js, que acrescenta `'unsafe-eval'` ao `script-src`. É a mesma ressalva registrada no [ambiente da etapa 5](../etapa-5/etapa-5-ambiente-e-configuracao.md).
- **Divulgação de Data e Hora e informativos a mais:** aparecem porque o spider desta rodada cobriu mais páginas do frontend.

### 4.3 Cobertura do active scan

| | Retest da etapa 5 | Agora |
| --- | :---: | :---: |
| Requisições no histórico exportado | 25 | 998 |
| Respostas `401` | muitas (token expirado) | nenhuma |
| Respostas `500` | — | nenhuma |

Distribuição das 998 respostas: `404` (454), `422` (186), `200` (155), `405` (96), `429` (96) e `101` (12, WebSocket).

A autenticação funcionou durante todo o scan, e nenhuma requisição derrubou o servidor. Mesmo assim, a cobertura das rotas de escrita foi rasa:
- os 120 `POST` terminaram em `429` (96) ou `404` (24), porque bateram no limite de requisições da API;
- os `PATCH` e `DELETE` foram montados a partir do OpenAPI com identificadores vazios (por exemplo `/v1/billing/items//status`), o que gerou `404` e `405`.

Por isso, a evidência de que RS01 e R18 funcionam vem dos testes, do script e dos ataques manuais, e não da varredura automática. O ZAP também não testa regras de negócio como "quem criou não aprova".

## 5. Análise de dependências

| | Etapa 5 (Python 3.11) | Agora (Python 3.14) |
| --- | :---: | :---: |
| Dependências analisadas | 191 | 187 |
| Registros de CVE | 9 | 3 (2 CVEs distintas) |

As seis ocorrências que deixaram de aparecer (`wheel`, `certifi` 2023, `jaraco.context` e os executáveis `cli-*.exe`) eram o ferramental de build que vinha no ambiente virtual do Python 3.11. A etapa 5 já classificava esses itens como ruído. O ambiente do Python 3.14 não traz esses pacotes, então eles saíram por mudança de ambiente, e não por alguma correção.

As duas CVEs que restam são **falsos positivos**. O Dependency-Check as associou aos pacotes pelo CPE, e a descrição de cada uma trata de outro software:

| CVE | Associada a | Software real da CVE | Por que não se aplica |
| --- | ----------- | -------------------- | --------------------- |
| CVE-2025-45770 (Alta) | `PyJWT` 2.15.1, pelos CPEs `jwt_project:jwt` e `pyjwt_project:pyjwt` | `lcobucci/jwt` 5.4.3, biblioteca PHP | a descrição e as referências apontam para a biblioteca PHP, e a CVE está marcada como contestada (*disputed*): o tamanho da chave cabe à aplicação, não à biblioteca. O protótipo já exige `JWT_SECRET` com pelo menos 32 caracteres. |
| CVE-2026-54285 (Média) | `opentelemetry-api` 1.45.2 (Python, dependência do FastAPI) | `@opentelemetry/core` (opentelemetry-js), versões anteriores à 2.8.0 | o CPE vulnerável é `opentelemetry:...:node.js`. O pacote Python não contém o código afetado. |

**Consequência para a etapa 5.** O achado V03 do [retest autenticado](../etapa-5/etapa-5-retest-autenticado.md) tratou a CVE-2025-45770 como uma vulnerabilidade real do `PyJWT`. Pela descrição da própria CVE, ela não se aplica a esse pacote. Mantivemos a etapa 5 como foi entregue e registramos a correção da leitura aqui.

Essa conclusão vem da descrição, das referências e dos CPEs presentes no relatório do Dependency-Check. Para confirmá-la formalmente, os dois casos podem ser registrados em um arquivo de supressão do Dependency-Check, com a justificativa acima.

## 6. Rastreabilidade

| Requisito | Risco | Decisão | Controles | Evidências |
| --------- | ----- | ------- | --------- | ---------- |
| RS01 | R01 | D01 | C4 | testes RS01, V-01 a V-03 (script), V-01 (ZAP manual) |
| RS01 (premissa R18) | R18 | D01 | C4 | testes R18, V-04 (script e ZAP manual), evento `autoaprovacao_negada` |
| RS05 | R26 | D05 | C11 | testes RS05 (falha injetada na auditoria) |
| RS02, RS03, RS04 (validação) | R02, R03, R06, R07 | D02, D03, D04 | C2, C3, C10 | suíte existente, V-05 a V-07 |

## 7. Limitações

- **É um protótipo:** o Redis substitui o banco relacional, e a "mesma transação" de RS05 é um `MULTI/EXEC`. O comportamento demonstrado vale para o protótipo, não para o sistema em produção.
- **RS05 parcial:** só cobre os lançamentos. Nas regras de serviço e no login, a auditoria continua gravada em chamada separada. Também não há *outbox* para o monitoramento nem encadeamento por *hash* (C6).
- **Reabrir só pela API:** a tela não tem o botão de reabrir. Editar pela tela um lançamento já enviado devolve `422`. Um lançamento `Approved` não reabre, porque a retirada da versão aprovada da carga do ERP depende de um componente que o protótipo não tem.
- **R18 só pela timeline:** a segregação usa a timeline do lançamento, que guarda o usuário de cada ação. Não há aprovação em dois níveis por valor, como o plano de tratamento da etapa 2 também previa para R18.
- **O que não foi implementado:** a assinatura assimétrica com chave em cofre (RS04), a carga do ERP com manifesto assinado (RS07) e a proteção anti-CSRF (RS08).
- **Ataques manuais só como `admin`:** foram feitos com o token injetado pelo Replacer. O RS01 vale para qualquer perfil, e os testes automatizados também o verificam como `analyst`.
- **Cobertura do active scan:** as rotas de escrita foram atingidas de forma rasa (seção 4.3). O ZAP não substitui os testes de regra de negócio.
- **Ambiente diferente da etapa 5:** a validade do token, o navegador e a versão do Python mudaram. Essas mudanças afetam a comparação de cobertura e de dependências, mas não o resultado dos ataques V-01 a V-08.

## 8. Índice de evidências

Todos os caminhos são relativos a [`evidencias/prototipo-corrigido/`](../../evidencias/prototipo-corrigido/).

| Arquivo | O que mostra |
| ------- | ------------ |
| `testes/pytest-original.txt`, `testes/junit-original.xml` | suíte do original: 75 passaram |
| `testes/pytest-corrigido.txt`, `testes/junit-corrigido.xml` | suíte do corrigido: 88 passaram, 2 `xfail` |
| `testes/pytest-criterios-rs01-r18-rs05.txt` | os 13 testes de critério de RS01, R18 e RS05, e os 2 `xfail` |
| `verificacao-api/resultado-original.json` | V-01 a V-08 contra a API original |
| `verificacao-api/resultado-corrigido.json` | V-01 a V-08 contra a API corrigida |
| `zap/zap-01-contexto-e-rotas.png` | contexto `Faturamento-Corrigido` com as duas URLs |
| `zap/zap-02-replacer-token-admin.png` | regra "Token Admin" no Replacer |
| `zap/zap-03-active-scan.png` | active scan concluído |
| `zap/zap-04-spider-front.png` | spider do frontend concluído |
| `zap/zap-05-alertas.png` | alertas da rodada |
| `zap/zap-06-v01-patch-apos-envio-req.png`, `-422.png` | V-01: requisição e resposta `422` |
| `zap/zap-07-v04-autoaprovacao-req.png`, `-403.png` | V-04: requisição e resposta `403` |
| `zap/zap-report.html` | relatório do ZAP (0 Alto, 4 Médio, 3 Baixo, 6 Informativo) |
| `zap/active_scan.csv` | histórico das 998 requisições do active scan |
| `dependency-check/dependency-check-report.html`, `.json` | Dependency-Check: 187 dependências e 3 registros de CVE, todos falsos positivos |

### Como reproduzir

```bash
# Testes (não precisam de Redis)
cd extra/prototipo-psp-corrigido/backend && .venv/bin/python -m pytest -v

# Ataques contra a API (com Redis e a API no ar; repita apontando para o original)
PSP_PASSWORD=... PSP_OTP=... .venv/bin/python ../verificacao/verificar_controles.py \
    --base http://localhost:8000 --rotulo corrigido --saida resultado-corrigido.json
```

A senha e o OTP são os valores de `MOCK_LOGIN_PASSWORD` e `MOCK_OTP_CODE` do `.env`. Limpe o Redis (`redis-cli FLUSHALL`) e reinicie a API antes de cada execução, para o seed começar do zero.
