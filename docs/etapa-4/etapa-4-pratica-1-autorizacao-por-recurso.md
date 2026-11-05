# Prática 1 — autorização por recurso

## 1. Risco e requisito relacionados

| Item                     | Descrição                                                                                                                                                                                                                                            |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Risco                    | R03, acesso não autorizado a dados restritos (Alto, 3×3), conforme o [plano de tratamento](../etapa-2/etapa-2-plano-e-residual.md)                                                                                                                   |
| Requisito                | RS03. Em toda rota que lê ou altera lançamentos, anexos e consultas, a API confere no servidor a permissão sobre o recurso (cliente, período e responsável pelo registro) e não olha só o perfil. Ver [Requisitos](../etapa-3/etapa-3-requisitos.md) |
| Decisão de arquitetura   | D02, autorizar por recurso no servidor, na camada de casos de uso. [Decisões](../etapa-3/etapa-3-decisoes.md)                                                                                                                                        |
| Prática de código seguro | Controle de autorização por recurso                                                                                                                                                                                                                  |

Hoje o guard da API só confere o perfil do usuário. O perfil diz o que a pessoa pode fazer, mas não diz sobre quais registros. Por isso, quem tem o perfil certo poderia ler dados de outro cliente ou de outro período só trocando o identificador na requisição. Esta prática fecha essa brecha.

Para isso, precisamos saber quais clientes e períodos cada pessoa pode acessar, ou seja, o escopo do usuário. Se o sistema ainda não guarda essa informação, ela passa a fazer parte da implementação.

## 2. Testes de segurança definidos antes da implementação

Escrevemos os testes antes do código da seção 3. Os dados são fictícios e os caminhos das rotas são só exemplos.

**Cenário.** Uma analista pode acessar o cliente 1 no período 2026-09. O lançamento L1 é do cliente 1 nesse período, e o lançamento L2 é do cliente 2.

| Teste | Entrada ou ação                                                 | Resultado esperado                                                                                                                                                                               |
| ----- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| TS01  | A analista pede `GET /v1/lancamentos/{L1}`                      | Permitido. A resposta traz os dados de L1                                                                                                                                                        |
| TS02  | A mesma analista troca o identificador por L2 e repete o pedido | Recusado, com a mesma resposta de registro não encontrado que um identificador inexistente receberia. Nenhum dado de L2 aparece, e a tentativa fica registrada com usuário, rota e identificador |

Abaixo, um esboço de como esses testes ficariam no código usando a biblioteca Pytest

```python
def test_ts01_analista_le_lancamento_do_proprio_escopo(client, analista_cliente_1, l1):
    resposta = client.get(f"/v1/lancamentos/{l1.id}", auth=analista_cliente_1)
    assert resposta.status_code == 200
    assert resposta.json()["id"] == str(l1.id)


def test_ts02_analista_nao_le_lancamento_de_outro_cliente(
    client, analista_cliente_1, l2, auditoria
):
    fora_do_escopo = client.get(f"/v1/lancamentos/{l2.id}", auth=analista_cliente_1)
    inexistente = client.get(f"/v1/lancamentos/{uuid4()}", auth=analista_cliente_1)

    assert fora_do_escopo.status_code == 404
    assert fora_do_escopo.json() == inexistente.json()  # não confirma que o registro existe
    assert auditoria.ultimo_evento().tipo == "acesso_negado"
```

## 3. Implementação

### 3.1 Política central de acesso

A regra mora em um único lugar (Domain), para nenhuma rota precisar reescrevê-la. Na dúvida, o acesso é negado, e só é liberado quando o recurso está dentro do escopo da pessoa.

```python
class PoliticaDeAcesso:
    """Decide, no servidor, se um usuário pode agir sobre um recurso."""

    def __init__(self, escopos):
        self.escopos = escopos

    def pode_ler(self, usuario, recurso) -> bool:
        escopo = self.escopos.do_usuario(usuario.id)  # clientes e períodos permitidos
        return (
            recurso.cliente_id in escopo.clientes
            and recurso.periodo in escopo.periodos
        )
```

Nas operações de escrita, usamos a mesma política e acrescentamos a regra do responsável pelo registro, como a gestão definir.

### 3.2 Uso no caso de uso

O guard de perfil continua na rota. A conferência do recurso fica no caso de uso, na camada de aplicação. Assim, um endpoint novo que use esse caso de uso já herda a checagem.

```python
@router.get("/v1/lancamentos/{lancamento_id}")
def consultar_lancamento(
    lancamento_id: UUID,
    usuario=Depends(exigir_perfil("analista", "gestor", "admin")),  # primeiro, o perfil
    caso_de_uso=Depends(obter_consultar_lancamento),
):
    return caso_de_uso.executar(usuario, lancamento_id)


class ConsultarLancamento:
    def executar(self, usuario, lancamento_id):
        lancamento = self.lancamentos.buscar(lancamento_id)

        if lancamento is None or not self.politica.pode_ler(usuario, lancamento):
            self.auditoria.registrar(
                "acesso_negado", usuario.id, recurso="lancamento", id=lancamento_id
            )
            raise NaoEncontrado()  # mesma resposta para inexistente e fora do escopo

        return lancamento
```

### 3.3 Listagens filtradas pelo escopo

Quando a consulta devolve vários registros, o filtro de escopo vai dentro da própria consulta, com parâmetros vinculados. Desse jeito, dados de outros clientes nem chegam à aplicação.

```python
def listar_lancamentos(self, usuario, filtros):
    escopo = self.escopos.do_usuario(usuario.id)
    return self.lancamentos.listar(
        clientes=escopo.clientes,   # vira cliente_id = ANY(:clientes)
        periodos=escopo.periodos,   # vira periodo = ANY(:periodos)
        filtros=filtros,
    )
```

### 3.4 Identificadores não sequenciais e teste de cobertura

Os identificadores que a API mostra devem ser UUIDs aleatórios, o que dificulta adivinhar o registro de outra pessoa. Isso ajuda, mas não substitui a política.

Um teste de cobertura roda no CI e falha se existir uma rota com identificador na URL que não tenha teste de autorização.

```python
def test_toda_rota_com_identificador_tem_teste_de_autorizacao(app):
    rotas_com_id = {r.path for r in app.routes if "{" in r.path}
    assert rotas_com_id - ROTAS_COM_TESTE_DE_AUTORIZACAO == set()
```

## 4. Resultado esperado

- O TS01 passa, então quem tem permissão continua usando o sistema normalmente.
- O TS02 passa, então trocar o identificador por um recurso de outro cliente não funciona, em nenhuma rota.
- A resposta para um recurso fora do escopo é igual à de um recurso que não existe, então ninguém descobre se o registro existe.
- Cada tentativa negada fica registrada, com usuário, rota e identificador, e pode ser consultada na auditoria.
- Uma rota nova com identificador e sem teste de autorização reprova o pipeline.
- A probabilidade de R03 cai de 3 para 1. É uma estimativa, que só se confirma quando os testes forem executados.

## 5. Referência da OWASP utilizada

- [Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), que ensina a negar por padrão e a validar a permissão em toda requisição.
- [Insecure Direct Object Reference Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html), que trata de conferir se o recurso é mesmo da pessoa e de usar identificadores difíceis de adivinhar.
- [OWASP ASVS 5.0, capítulo V8 (Autorização)](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8-Authorization.md), em especial o requisito 8.2.2, que limita o acesso a cada dado a quem tem permissão explícita para ele e assim evita IDOR, e o requisito 8.3.1, que manda aplicar as regras de autorização em uma camada de serviço confiável.
