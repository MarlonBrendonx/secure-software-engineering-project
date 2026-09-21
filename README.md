<div align="center">

<img src="./imgs/logo.png" alt="Logo do projeto" width="620">

# Faturamento de Redes

**Documentação de Engenharia de Software Seguro**

</div>

## Escopo

Este repositório reúne a documentação de engenharia de software seguro do sistema de
**Faturamento de Redes**, o processo pelo qual lançamentos de rede credenciada são
apurados por competência, provisionados e faturado. O sistema possibilita o gerenciamento das redes cadastradas e o controle de acesso por meio de diferentes perfis de usuário (Administrador, Analista e Gestor). Além disso, permite realizar o fluxo completo de lançamentos, incluindo sua criação, aprovação e reprovação.

O software foi construído sobre as sequintes stacks e arquitetura

**Backend:** Desenvolvido em **Python 3.11** com **FastAPI**, utilizando **Oracle** e **PostgreSQL** como bancos de dados. A aplicação foi estruturada seguindo os princípios de **Clean Architecture** e **Domain-Driven Design (DDD)**, com **TDD (Test-Driven Development)** aplicado ao desenvolvimento e à validação das funcionalidades.

Para gerenciamento de filas e processamento assíncrono, são utilizados **RabbitMQ** e **Celery**. O **Blob Storage** é empregado para armazenamento de arquivos e dados, enquanto a autenticação e o controle de acesso são realizados por meio de **SSO (Single Sign-On)**.

**Frontend:** Desenvolvido em **React.js**, utilizando a arquitetura **Feature-Sliced Design (FSD)** para organizar e estruturar a aplicação de forma modular e escalável. A arquitetura promove a separação clara das responsabilidades, facilitando a manutenção, reutilização de componentes e evolução do sistema.

O escopo atual é **documental**. O repositório descreve o sistema, seu vocabulário de
domínio, seus ativos e seus riscos. Porém, não contém, neste momento, implementação,
evidências de execução ou artefatos de verificação automatizada.

### Visão geral

| Documento                                                   | Status | O que responde                                                                       |
| ----------------------------------------------------------- | :----: | ------------------------------------------------------------------------------------ |
| [Visão Geral do Sistema](extra/visao-geral-do-sistema.md)   |   ✅   | O que o sistema é, o que faz, quais são os ativos importantes e onde estão os riscos |
| [Entrevista com o cliente](extra/entrevista-com-cliente.md) |   🟡   | Transcrição da entrevista com o cliente dono do sistema e pontos levantados          |

## Navegação por etapa

| Etapa                       | Descrição                                                            | Documentos                                                                                                                                          |
| --------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Base                        | Documentação e visão geral do sistema                                | [Visão geral do sistema](extra/visao-geral-do-sistema.md)                                                                                           |
| 1. Ameaças e casos de abuso | Casos de Abuso e Modelagem de Ameaças com STRIDE                     | [Identificação do Sistema](docs/etapa-1/etapa-1-identificacao-sistema.md), [Índice STRIDE e casos de abuso](docs/etapa-1/etapa-1-ameacas-stride.md) |
| 2. Riscos e NIST CSF 2.0    | Planejada Análise, Priorização e Tratamento de Riscos com o NIST CSF |

## Organização do repositório

```text
.
├── README.md      # este índice
├── extra/         # documentações extras ou complementares
├── docs/          # documentações md de cada etapa
├── diagramas/     # diagramas e fluxos de cada etapa
└── imgs/          # imagens no geral
```
