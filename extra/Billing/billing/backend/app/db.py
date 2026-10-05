from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: sessionmaker | None = None


def configurar_engine(url: str | None = None, **kwargs):
    """Cria o engine. Os testes chamam com SQLite em memória."""
    global _engine, _SessionLocal
    url = url or get_settings().database_url
    if url.startswith("sqlite") and "connect_args" not in kwargs:
        # Implantação em contêiner único: a API atende requisições em várias threads
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    _engine = create_engine(url, pool_pre_ping=True, **kwargs)
    if url.startswith("sqlite") and url not in ("sqlite://", "sqlite:///:memory:"):
        @event.listens_for(_engine, "connect")
        def _pragmas(conexao, _):
            cur = conexao.cursor()
            cur.execute("PRAGMA journal_mode=WAL")    # leituras não bloqueiam a escrita
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.close()
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_engine():
    if _engine is None:
        configurar_engine()
    return _engine


def get_db() -> Iterator[Session]:
    if _SessionLocal is None:
        configurar_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def nova_sessao() -> Session:
    if _SessionLocal is None:
        configurar_engine()
    return _SessionLocal()
