# Etapa 5 — Retest autenticado e achados de vulnerabilidade

A primeira varredura ([Análise dos achados](etapa-5-analise-dos-achados.md)) encontrou só problemas de configuração (A01, A02 e A03) e o active scan não chegou à lógica das rotas de escrita. Para cobrir o que as [Limitações](etapa-5-limitacoes.md) deixaram em aberto, rodamos uma segunda rodada, com foco nas rotas de escrita, na autorização por recurso, no reuso de token, no MFA e nas dependências.

Usamos três apoios, no mesmo protótipo local e com os mesmos usuários fictícios:

- **ZAP 2.17 (desktop)**, dirigido pela própria API, para criar o contexto, importar o OpenAPI, autenticar pelo Replacer e rodar spider, passive e active scan.
- **Um conjunto de testes de API por perfil**, com o token renovado a cada chamada. Serviu para os casos que o scanner automático não cobre: JWT forjado, CSRF, reuso de refresh, IDOR, MFA e rate limit.
- **OWASP Dependency-Check**, para as dependências do backend.

As evidências estão em [`evidencias/etapa-5/retest-autenticado/`](../../evidencias/etapa-5/retest-autenticado/).

## O que o ZAP conseguiu, e o que não conseguiu

O active scan autenticado **não** fechou a lacuna das rotas de escrita. O token de acesso vale 15 minutos e expirou durante o scan, e o rate limit da API entrou no caminho. Das 14.912 mensagens enviadas ao backend, 8.306 receberam `429` (rate limit) e 5.632 receberam `401`, contra apenas 2 respostas `200`. Nas rotas de escrita o quadro é o mesmo: `PATCH` teve 1.695 `401` e 1.944 `429`; `POST`, 6.171 `429`; `DELETE`, 101 `401` e 191 `429`. Ou seja, o scanner mandou `POST`, `PATCH` e `DELETE` para as rotas certas ([captura `zap-05`](../../evidencias/etapa-5/retest-autenticado/zap-05-rotas-escrita-atacadas.png)), mas quase nada passou da autenticação e do limite de requisições. Isso repete a limitação da primeira rodada, e não prova que as rotas de escrita estão corretas.

O que o ZAP fez bem foi reconfirmar os achados de cabeçalho e CSP (A01 a A03) no spider e no passive scan do front ([captura `zap-06`](../../evidencias/etapa-5/retest-autenticado/zap-06-spider-passivo-front.png)), sem nenhum alerta Alto e com os mesmos três Médios de CSP. O resultado global do retest com o ZAP foi 0 Alto, 3 Médio e 2 Baixo. O relatório completo está em [`zap-desktop-report.html`](../../evidencias/etapa-5/retest-autenticado/zap-desktop-report.html).

Os achados de vulnerabilidade a seguir **não** vieram do ZAP. Vieram dos testes de API, com token renovado, e do Dependency-Check.

## Achados

| ID  | Achado                                         | Onde                        | Gravidade | Correção                                               |
| --- | ---------------------------------------------- | --------------------------- | :-------: | ------------------------------------------------------ |
| V01 | Refresh token aceito de novo após a rotação    | API, `POST /v1/auth/refresh`|   Média   | rotacionar o refresh e revogar o anterior              |
| V02 | `access_token` no corpo além do cookie         | API, `POST /v1/auth/login`  |   Média   | entregar o token só no cookie `HttpOnly`               |
| V03 | Biblioteca de JWT com CVE conhecida (PyJWT)    | Dependência do backend      |    Alta   | atualizar o `PyJWT` para a versão corrigida            |

---

## V01 — Refresh token reaproveitável

O refresh token é o crédito que o cliente usa para pedir um novo token de acesso quando o atual vence, sem refazer o login. A boa prática é rotacioná-lo: a cada uso o servidor devolve um refresh novo e invalida o antigo. Assim, um refresh que vaze deixa de valer assim que o dono fizer a próxima renovação.

No protótipo isso não acontece. Pegamos o refresh de um login, chamamos `/v1/auth/refresh` uma vez e, em seguida, chamamos de novo com o **mesmo** refresh antigo. As duas chamadas responderam `200`.

```bash
curl -s -c cookies -o /dev/null -X POST http://localhost:8000/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"analyst","password":"<senha>"}'
RT=$(grep refresh_token cookies | awk '{print $NF}')
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/v1/auth/refresh -b "refresh_token=$RT"  # 200
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/v1/auth/refresh -b "refresh_token=$RT"  # 200 (devia ser 401)
```

O efeito é uma janela maior para roubo de sessão. Um refresh capturado em um log, num proxy ou numa cópia de cookie continua servindo mesmo depois de o dono já ter renovado a sessão. O cookie é `HttpOnly` e tem o caminho preso a `/v1/auth/refresh`, o que reduz a exposição, então classificamos como Média e não Alta. Vale lembrar que o login aqui é um mock; no SSO corporativo a rotação do refresh fica a cargo do provedor, e esse ponto precisa ser verificado lá.

Este achado não é novidade no registro de riscos: é o **R25** (reuso de refresh token), que a [etapa 3](../etapa-3/etapa-3-requisitos.md) já tinha marcado como candidato e deixado para depois. O que o retest acrescenta é a confirmação prática de que, no protótipo, o refresh antigo de fato continua válido. O registro de sessões previsto em RS04 já reduziria o efeito, porque a renovação pode ficar condicionada ao `sid` ativo.

A correção é rotacionar o refresh a cada uso e marcar o anterior como revogado, guardando o identificador da sessão ou do token para recusar o reuso. Na classificação, é OWASP Top 10 2021 A07 (Identification and Authentication Failures) e CWE-613 (Insufficient Session Expiration).

## V02 — Token de acesso também no corpo da resposta

O login guarda a sessão num cookie `HttpOnly`, que o JavaScript da página não consegue ler. É a proteção certa contra um XSS que tente roubar a sessão. O problema é que a mesma resposta devolve o `access_token` também no corpo JSON.

```text
set-cookie: access_token=<token>; HttpOnly; Max-Age=900; Path=/; SameSite=strict
{"access_token":"<token>", ... , "mfa":false}
```

Com o token no corpo, o benefício do `HttpOnly` se perde: um script injetado na página alcança o token pela resposta e pode levá-lo embora. Esse mesmo ponto já tinha aparecido na [primeira análise](etapa-5-analise-dos-achados.md) e nas Limitações, como observação fora do ZAP. Aqui ele vira achado, porque confirmamos que o corpo traz o token.

A correção é não devolver o `access_token` no corpo. O front descobre quem é o usuário por `GET /v1/auth/get-session`, e o token viaja só no cookie. Na classificação, é OWASP Top 10 2021 A04 (Insecure Design) e CWE-522 (Insufficiently Protected Credentials). Mantemos Média, porque o risco só se concretiza junto com um XSS, que a CSP do A01 deveria conter.

## V03 — Dependência de JWT com CVE conhecida

O Dependency-Check analisou as bibliotecas instaladas do backend: 191 dependências, com 9 registros de CVE. A maioria é ruído de ferramental de build (por exemplo `wheel` e executáveis auxiliares), mas um achado pesa para este sistema. A biblioteca **`PyJWT` 2.15.1**, que o serviço de token usa para assinar e validar o JWT da sessão, consta com a **CVE-2025-45770**, classificada como Alta pelo NVD.

O relatório está em [`dependency-check-report.html`](../../evidencias/etapa-5/retest-autenticado/dependency-check-report.html) (dados em [`.json`](../../evidencias/etapa-5/retest-autenticado/dependency-check-report.json), captura em [`zap-07`](../../evidencias/etapa-5/retest-autenticado/zap-07-dependency-check.png)).

Como o JWT está no centro da autenticação, uma falha nessa biblioteca atinge o ponto mais sensível do sistema. O passo seguinte é checar, na descrição da CVE, se o caminho vulnerável é o que usamos e atualizar o `PyJWT` para a versão corrigida. Este achado é o risco T37 (dependência maliciosa ou vulnerável na cadeia de suprimentos) da [modelagem da etapa 1](../etapa-1/etapa-1-ameacas-stride.md), agora com um caso concreto. Na classificação, é OWASP Top 10 2021 A06 (Vulnerable and Outdated Components) e CWE-1395 (Dependency on Vulnerable Third-Party Component).

---

## Controles que se confirmaram

Os testes de API, com token renovado, também mostraram o que está funcionando, e isso é parte do resultado:

- **JWT forjado é recusado.** Um token com `alg=none`, um com a assinatura trocada e um com `role=admin` no corpo receberam `401` em `GET /v1/registry/clients/summary`. A assinatura HS256 é exigida (ameaças T02 e T16).
- **O escopo por recurso foi respeitado.** O `analyst` lê as regras de serviço de um cliente do seu escopo (`200`) e recebe `404` ao trocar o id para um cliente fora do escopo. É o único ponto em que o retest tocou a autorização por recurso (R03), que antes só os testes da etapa 4 cobriam. Não é uma varredura exaustiva de IDOR, mas é um caso real verificado (ameaça T26).
- **O MFA barra o token sem segundo fator.** O `admin` autenticado só com senha (`amr=["pwd"]`) recebeu `401 mfa_necessario` ao tentar escrever em regras de serviço (ameaça T02).
- **O rate limit está ativo.** No login, a 11ª tentativa seguida passou a `429`. O mesmo limite apareceu, de forma intensa, no active scan do ZAP (ameaças T14a e T23).
- **Campos só de servidor são ignorados.** Um `PATCH` em lançamento com `code`, `value` e `created_at` extras foi recusado com `422`, sem mexer no cálculo (ameaças T01 e T06).

## O que ainda não foi coberto

A autorização por recurso segue sem uma varredura ampla: verificamos um caso de leitura fora do escopo, não todos os recursos nem as rotas de escrita de outro cliente. A lógica das rotas de escrita continua sem um active scan autenticado de verdade, porque o token curto e o rate limit barram o scanner. Para alcançá-la seria preciso um script de autenticação no ZAP que renove o token sozinho, com menos threads e com `/v1/auth/logout` e `/v1/auth/refresh` fora do alcance. Fica como próximo passo, junto com os já listados nas [Limitações](etapa-5-limitacoes.md).
