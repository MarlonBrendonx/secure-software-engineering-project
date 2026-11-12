# Etapa 6 — Limitações

As regras e o roteiro desta etapa são planejamento. Este documento mostra o que eles ainda não garantem.

## Limitações

- **Só D01 está implementada e testada.** D02 tem alerta, mas sem teste do alerta. As outras doze regras são propostas.
- **O alerta do protótipo não chega a ninguém.** Ele vai para o log e para uma lista no Redis. Não há SIEM, fila de tratamento nem plantão, e o tempo de resposta não pode ser medido.
- **A auditoria do protótipo não serve como evidência.** Fica no Redis, em lista limitada a 5.000 entradas, sem encadeamento por hash e gravada depois da operação, não na mesma transação. Quem tem acesso ao Redis apaga o próprio rastro, que é exatamente o R08 e o R26.
- **Faltam campos para correlacionar.** O evento não grava perfil, `sid`, `request_id` nem resultado, e a origem só aparece nos eventos de login e de MFA.
- **Os limites não foram calibrados.** Os números das regras são estimativas. Sem histórico de uso real, não se sabe quantos falsos positivos D03, D08 e D09 gerariam.
- **O contador é por usuário e com janela fixa.** O `SecurityMonitor` não pega um ataque espalhado por várias contas nem um ataque lento que fique abaixo do limite em cada janela. D03 e D06 pedem contagem também por origem.
- **O login é simulado.** No sistema real, as falhas de senha e de MFA acontecem no SSO, e D01, D03 e D04 dependem dos eventos do Keycloak, que não foram observados.
- **Não há detecção de rede nem de host.** Esta etapa cobre só eventos da aplicação. Um acesso direto ao banco, ao Redis ou ao storage, fora da API, não é percebido por nenhuma regra.
- **O roteiro de resposta não foi exercitado.** Não houve simulação de incidente, e os papéis da tabela de [responsabilidades](etapa-6-resposta-a-incidentes.md#responsabilidades) ainda não têm pessoas nomeadas.

## Próximas etapas

- Escrever o teste do alerta de D02 e passar as negações de período da listagem pelo `SecurityMonitor`.
- Acrescentar ao `AuditEvent` os campos perfil, `sid`, `request_id` e resultado, e gravar a origem em todos os eventos.
- Levar para a auditoria os sinais que hoje só aparecem no log ou na resposta HTTP (`401`, `503`, `4403` e `429`), para habilitar D06, D10, D12 e D13.
- Rodar os testes de [validação das regras](etapa-6-validacao-das-regras.md) no CI (etapa 7), para que uma regra que deixe de disparar seja percebida.
- Fazer um exercício de mesa com um dos cenários (por exemplo, o reuso de refresh token do V01) para testar o roteiro de resposta e medir o tempo até a contenção.

---
