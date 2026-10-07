from alembic import context
from sqlalchemy import create_engine

from nbb.config import get_settings

config = context.config


def run_migrations_online() -> None:
    # Migrations rodam com o usuário dono do schema, nunca com o da aplicação.
    url = config.attributes.get("url") or get_settings().database_owner_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
