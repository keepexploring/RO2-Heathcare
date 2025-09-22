import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from dotenv import load_dotenv
load_dotenv()  # ensures DATABASE_URL is loaded


# Add FastAPI app to path so we can import models
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "fastapi", "app"))

from db import Base  # Your SQLAlchemy Base
from models import *  # Import all models to ensure they're registered with Base
target_metadata = Base.metadata

# Read DATABASE_URL from environment
def get_url():
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sensordb")

# Alembic Config object
config = context.config

# Set up Python logging from config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
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
