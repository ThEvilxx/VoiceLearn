"""SQLite + SQLAlchemy async database setup."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Auto-migration: add sources column when upgrading from older schema
        def _migrate(connection):
            try:
                connection.exec_driver_sql(
                    "ALTER TABLE messages ADD COLUMN sources TEXT"
                )
                logger.info("Migration: added sources column to messages table")
            except Exception:
                pass  # column already exists
        await conn.run_sync(_migrate)
