"""Comandos de manutenção. Uso: python -m app.cli <comando> [opções]

  iniciar-banco                         cria as tabelas (idempotente)
  criar-usuario LOGIN NOME PAPEL        cadastra um usuário na base local (ex.: o primeiro administrador)
  revogar-sessoes LOGIN                 encerra todas as sessões de um usuário (ex.: desligamento)
  revogar-todas-sessoes                 encerra todas as sessões do sistema (rotação emergencial de chave)
  limpar-logs                           remove registros de auditoria além do prazo de retenção
"""
import argparse
import sys
from datetime import timedelta

from .auditoria import registrar
from .config import get_settings
from .db import Base, get_engine, nova_sessao
from .models import LogAuditoria, Papel, Sessao, TipoAcao, Usuario, agora
from .routers.auth import revogar_sessoes_usuario


def iniciar_banco() -> None:
    Base.metadata.create_all(get_engine())
    print("Tabelas criadas/verificadas.")


def criar_usuario(login: str, nome: str, papel: str) -> None:
    with nova_sessao() as db:
        login = login.strip().lower()
        if db.query(Usuario).filter(Usuario.login == login).first():
            sys.exit(f"Usuário '{login}' já existe.")
        u = Usuario(login=login, nome=nome, papel=Papel(papel.upper()))
        db.add(u)
        db.flush()
        registrar(db, TipoAcao.CRIACAO, login="cli", entidade="usuarios", entidade_id=u.id,
                  detalhes={"origem": "linha_de_comando", "papel": u.papel.value})
        db.commit()
        print(f"Usuário '{login}' criado com papel {u.papel.value}. O segundo fator é cadastrado no primeiro login.")


def revogar_sessoes(login: str) -> None:
    with nova_sessao() as db:
        u = db.query(Usuario).filter(Usuario.login == login.strip().lower()).one_or_none()
        if u is None:
            sys.exit("Usuário não encontrado.")
        n = revogar_sessoes_usuario(db, u, "revogacao_cli")
        registrar(db, TipoAcao.SESSAO_REVOGADA, login="cli", entidade="usuarios", entidade_id=u.id,
                  detalhes={"sessoes_revogadas": n})
        db.commit()
        print(f"{n} sessão(ões) revogada(s).")


def revogar_todas() -> None:
    with nova_sessao() as db:
        sessoes = db.query(Sessao).filter(Sessao.revogada_em.is_(None)).all()
        for s in sessoes:
            s.revogada_em, s.motivo_revogacao = agora(), "revogacao_global"
        registrar(db, TipoAcao.SESSAO_REVOGADA, login="cli", detalhes={"global": True, "sessoes_revogadas": len(sessoes)})
        db.commit()
        print(f"{len(sessoes)} sessão(ões) revogada(s). Todos os usuários precisarão entrar de novo.")


def limpar_logs() -> None:
    anos = get_settings().retencao_logs_anos
    limite = agora() - timedelta(days=365 * anos)
    with nova_sessao() as db:
        n = db.query(LogAuditoria).filter(LogAuditoria.data_hora < limite).delete(synchronize_session=False)
        registrar(db, TipoAcao.REMOCAO, login="cli", entidade="log_auditoria",
                  detalhes={"motivo": "retencao", "anos": anos, "registros_removidos": n})
        db.commit()
        print(f"{n} registro(s) anteriores a {limite.date()} removido(s).")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("iniciar-banco")
    c = sub.add_parser("criar-usuario")
    c.add_argument("login")
    c.add_argument("nome")
    c.add_argument("papel", choices=[x.value for x in Papel])
    r = sub.add_parser("revogar-sessoes")
    r.add_argument("login")
    sub.add_parser("revogar-todas-sessoes")
    sub.add_parser("limpar-logs")
    a = p.parse_args(argv)
    {
        "iniciar-banco": iniciar_banco,
        "criar-usuario": lambda: criar_usuario(a.login, a.nome, a.papel),
        "revogar-sessoes": lambda: revogar_sessoes(a.login),
        "revogar-todas-sessoes": revogar_todas,
        "limpar-logs": limpar_logs,
    }[a.comando]()


if __name__ == "__main__":
    main()
