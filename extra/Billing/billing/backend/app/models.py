"""Modelo de dados: base local de usuários, sessões, auditoria, cadastros e billing."""
import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON, BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def agora() -> datetime:
    return datetime.now(UTC)


def utc(dt: datetime | None) -> datetime | None:
    """Normaliza datas lidas do banco (o SQLite devolve sem fuso)."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class Papel(str, enum.Enum):
    ADMINISTRADOR = "ADMINISTRADOR"   # cadastros de base e gestão de usuários
    OPERACIONAL = "OPERACIONAL"       # lançamentos e planilha ERP
    GESTOR = "GESTOR"                 # validação e aprovação
    AUDITOR = "AUDITOR"               # consulta da trilha de auditoria
    OPERACAO = "OPERACAO"             # time de Operação/SRE


class StatusLancamento(str, enum.Enum):
    RASCUNHO = "RASCUNHO"
    SUBMETIDO = "SUBMETIDO"
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"


class TipoAcao(str, enum.Enum):
    LOGIN_OK = "LOGIN_OK"
    LOGIN_FALHA = "LOGIN_FALHA"
    LOGIN_BLOQUEADO = "LOGIN_BLOQUEADO"        # limite de tentativas atingido
    MFA_CADASTRADO = "MFA_CADASTRADO"
    MFA_FALHA = "MFA_FALHA"
    LOGOUT = "LOGOUT"
    SESSAO_REVOGADA = "SESSAO_REVOGADA"
    ACESSO_NEGADO = "ACESSO_NEGADO"
    CRIACAO = "CRIACAO"
    EDICAO = "EDICAO"
    REMOCAO = "REMOCAO"
    SUBMISSAO = "SUBMISSAO"
    APROVACAO = "APROVACAO"
    REPROVACAO = "REPROVACAO"
    EXPORTACAO_ERP = "EXPORTACAO_ERP"
    DOWNLOAD_ERP = "DOWNLOAD_ERP"


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(120), unique=True, index=True)  # login corporativo
    nome: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    papel: Mapped[Papel] = mapped_column(Enum(Papel, native_enum=False, length=20))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_segredo_cifrado: Mapped[str | None] = mapped_column(Text)
    mfa_ativo: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, onupdate=agora)


class Sessao(Base):
    __tablename__ = "sessoes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), index=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # limite absoluto
    ultimo_uso: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_revogacao: Mapped[str | None] = mapped_column(String(100))

    usuario: Mapped[Usuario] = relationship()


class LogAuditoria(Base):
    __tablename__ = "log_auditoria"
    __table_args__ = (
        Index("ix_log_data", "data_hora"),
        Index("ix_log_usuario_data", "usuario_id", "data_hora"),
        Index("ix_log_tipo_data", "tipo_acao", "data_hora"),
        Index("ix_log_papel_data", "papel", "data_hora"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    usuario_id: Mapped[int | None] = mapped_column(Integer)
    login: Mapped[str | None] = mapped_column(String(120))  # guardado também para tentativas falhas
    papel: Mapped[str | None] = mapped_column(String(20))
    ip: Mapped[str | None] = mapped_column(String(64))
    tipo_acao: Mapped[TipoAcao] = mapped_column(Enum(TipoAcao, native_enum=False, length=30))
    entidade: Mapped[str | None] = mapped_column(String(60))
    entidade_id: Mapped[str | None] = mapped_column(String(60))
    detalhes: Mapped[dict | None] = mapped_column(JSON)


# ---------------------------------------------------------------------------
# Cadastros de base (perfil Administrador)
# ---------------------------------------------------------------------------
class _Cadastro:
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, onupdate=agora)


class Empresa(_Cadastro, Base):
    __tablename__ = "empresas"
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)


class Segmento(_Cadastro, Base):
    __tablename__ = "segmentos"


class Programa(_Cadastro, Base):
    __tablename__ = "programas"


class GrupoEconomico(_Cadastro, Base):
    __tablename__ = "grupos_economicos"


class CentroCusto(_Cadastro, Base):
    __tablename__ = "centros_custo"
    codigo: Mapped[str] = mapped_column(String(40), unique=True)


class UnidadeNegocio(_Cadastro, Base):
    __tablename__ = "unidades_negocio"


class Fornecedor(_Cadastro, Base):
    __tablename__ = "fornecedores"
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)


class Cliente(_Cadastro, Base):
    __tablename__ = "clientes"
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    grupo_economico_id: Mapped[int | None] = mapped_column(ForeignKey("grupos_economicos.id"))
    segmento_id: Mapped[int | None] = mapped_column(ForeignKey("segmentos.id"))


class Contrato(_Cadastro, Base):
    __tablename__ = "contratos"
    numero: Mapped[str] = mapped_column(String(60), unique=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    programa_id: Mapped[int | None] = mapped_column(ForeignKey("programas.id"))
    centro_custo_id: Mapped[int | None] = mapped_column(ForeignKey("centros_custo.id"))
    unidade_negocio_id: Mapped[int | None] = mapped_column(ForeignKey("unidades_negocio.id"))
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("fornecedores.id"))
    vigencia_inicio: Mapped[datetime | None] = mapped_column(Date)
    vigencia_fim: Mapped[datetime | None] = mapped_column(Date)


class RegraServico(_Cadastro, Base):
    __tablename__ = "regras_servico"
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contratos.id"))
    unidade_medida: Mapped[str] = mapped_column(String(40), default="unidade")
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4))


# ---------------------------------------------------------------------------
# Billing (Operacional e Gestor)
# ---------------------------------------------------------------------------
class Lancamento(Base):
    __tablename__ = "lancamentos"
    __table_args__ = (UniqueConstraint("cliente_id", "periodo", "regra_servico_id", name="uq_lanc_cli_per_regra"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)  # AAAA-MM
    regra_servico_id: Mapped[int] = mapped_column(ForeignKey("regras_servico.id"))
    quantidade: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    valor_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    observacao: Mapped[str | None] = mapped_column(Text)
    status: Mapped[StatusLancamento] = mapped_column(
        Enum(StatusLancamento, native_enum=False, length=20), default=StatusLancamento.RASCUNHO
    )
    criado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora, onupdate=agora)
    submetido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Aprovacao(Base):
    __tablename__ = "aprovacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lancamento_id: Mapped[int] = mapped_column(ForeignKey("lancamentos.id"), index=True)
    gestor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    decisao: Mapped[StatusLancamento] = mapped_column(Enum(StatusLancamento, native_enum=False, length=20))
    observacao: Mapped[str | None] = mapped_column(Text)
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)


class ExportacaoErp(Base):
    __tablename__ = "exportacoes_erp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    gerada_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    gerada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=agora)
    quantidade_lancamentos: Mapped[int] = mapped_column(Integer)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    conteudo_csv: Mapped[str] = mapped_column(Text)
