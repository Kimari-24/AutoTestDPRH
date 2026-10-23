"""Entorno de ejecución de Alembic para AutoTest DPRH.

Toma la URL de conexión desde `app.core.config.settings` (que a su
vez lee el archivo `.env`), y usa `app.db.session.Base.metadata`
como fuente de verdad para el autogenerado de migraciones.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config.settings import get_settings  # noqa: E402
from app.db.session import Base  # noqa: E402

# Importa todos los modelos para que Alembic los detecte al hacer
# autogenerate (el paquete app.models ya se encarga de importar cada
# submódulo de modelo).
from app import models  # noqa: E402,F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
