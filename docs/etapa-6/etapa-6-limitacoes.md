# Etapa 6 — Limitações

As regras e o roteiro desta etapa são planejamento. O código proposto nos diretórios desta etapa foi testado em cópias dos protótipos, mas ainda não foi aplicado a nenhum deles: a substituição depende do consenso do grupo sobre qual protótipo segue. Este documento mostra o que ainda não está garantido.

## Limitações

- **O código proposto não está nos protótipos.** No repositório, só D01 está implementada e testada, e D02 tem alerta sem teste do alerta. Com o código aplicado, D01 a D05 e D13 ficam implementadas e testadas, D06, D07, D08 e D12 ficam parciais, e D09, D10, D11 e D14 continuam só propostas (ver [regras de detecção](etapa-6-regras-de-deteccao.md#código-proposto)).
- **O alerta do protótipo não chega a ninguém.** Ele vai para o log e para uma lista no Redis. Não há SIEM, fila de tratamento nem plantão, e o tempo de resposta não pode ser medido.
- **A auditoria do protótipo não serve como evidência.** Fica no Redis, em lista limitada a 5.000 entradas e sem encadeamento por hash. No original, ela é gravada depois da operação, não na mesma transação; no corrigido, isso vale para as regras de serviço, mas não para os lançamentos. Quem tem acesso ao Redis apaga o próprio rastro, que é exatamente o R08 e o R26. O script de exportação tira uma cópia com hash, mas não impede a alteração antes da cópia.
- **Os campos de correlação só existem com o código proposto.** Sem ele, o evento não grava perfil, `sid`, `request_id` nem resultado, e a origem só aparece nos eventos de login e de MFA. Com ele, eventos gravados fora de uma requisição HTTP (como os do WebSocket, que não passa pelo middleware) continuam sem `request_id`, e o `result` fica vazio nos eventos que não passam pelo `SecurityMonitor` nem pelo login.
- **Os limites não foram calibrados.** Os números das regras são estimativas. Sem histórico de uso real, não se sabe quantos falsos positivos D03, D08 e D09 gerariam.
- **A contagem usa janela fixa.** A janela começa no primeiro evento e não desliza. Um ataque lento, que fique abaixo do limite em cada janela, não é percebido. O alerta dispara uma vez por janela, então um ataque que continua depois do alerta só gera novo alerta na janela seguinte. D03 e D06 contam por origem, mas uma origem que troca de IP escapa da contagem.
- **D04 aprende a origem no primeiro login.** Sem histórico, o primeiro login da conta não gera alerta. Se o primeiro login registrado já for o do atacante, a origem dele passa a ser conhecida.
- **A rotação do refresh pode derrubar uma sessão legítima.** Duas abas que renovam ao mesmo tempo apresentam o mesmo refresh, e a segunda renovação é tratada como reuso: a sessão é revogada e D05 dispara. Não há janela de tolerância.
- **As regras rodam na requisição.** A avaliação acontece logo depois da gravação da auditoria, no mesmo fluxo. Um Redis lento deixa a resposta lenta. Uma falha nas regras não desfaz a operação, mas o evento fica sem avaliação, e isso só aparece no log.
- **Eventos gravados dentro da transação do lançamento não passam pelas regras.** No corrigido, os eventos de lançamento entram no mesmo `MULTI/EXEC` da operação, sem passar pelo gateway que entrega os eventos às regras. Hoje nenhuma regra usa esses eventos, mas uma regra futura sobre eles precisaria de outro caminho.
- **O login é simulado.** No sistema real, as falhas de senha e de MFA acontecem no SSO, e D01, D03 e D04 dependem dos eventos do Keycloak, que não foram observados.
- **Não há detecção de rede nem de host.** Esta etapa cobre só eventos da aplicação. Um acesso direto ao banco, ao Redis ou ao storage, fora da API, não é percebido por nenhuma regra.
- **Os testes usaram Redis falso.** A validação rodou com `fakeredis`, não com um Redis real, e sem carga concorrente.
- **O roteiro de resposta não foi exercitado.** Não houve simulação de incidente, e os papéis da tabela de [responsabilidades](etapa-6-resposta-a-incidentes.md#responsabilidades) ainda não têm pessoas nomeadas.

## Próximas etapas

- Decidir em grupo em qual protótipo o código entra e aplicar os diretórios na ordem indicada no [índice](etapa-6-deteccao-de-intrusoes.md#como-aplicar-o-código-proposto).
- Corrigir o V02 junto com a autenticação do WebSocket, para o frontend deixar de ler o token do corpo da resposta.
- Atualizar o `PyJWT` (V03) e confirmar no Dependency-Check.
- Criar a revogação de todas as sessões de um usuário e uma janela de tolerância para renovações simultâneas.
- Gravar as leituras com volume (D09), as recusas de alteração e de transição de lançamento (D07) e levar a falha do guard para uma fonte fora do Redis (D10).
- Rodar os testes de [validação das regras](etapa-6-validacao-das-regras.md) no CI (etapa 7), para que uma regra que deixe de disparar seja percebida.
- Fazer um exercício de mesa com um dos cenários (por exemplo, o reuso de refresh token do V01) para testar o roteiro de resposta e medir o tempo até a contenção.

---
