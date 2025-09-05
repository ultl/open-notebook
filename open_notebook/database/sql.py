from __future__ import annotations

from os import getenv
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (  # type: ignore[import-not-found]
  AsyncEngine,
  AsyncSession,
  async_sessionmaker,
  create_async_engine,
)
from sqlmodel import SQLModel

if TYPE_CHECKING:
  from collections.abc import AsyncGenerator


def _database_url() -> str:
  # Expect a standard async URL, e.g. postgresql+psycopg://user:pass@host:5432/db
  url = getenv('DATABASE_URL')
  if not url:
    # Provide a sensible default for local development
    url = 'postgresql+psycopg://postgres:pw@127.0.0.1:5432/postgres'
  return url


engine: AsyncEngine = create_async_engine(_database_url(), echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
  async with SessionLocal() as session:
    yield session


async def init_db() -> None:
  # Import models to ensure SQLModel.metadata is populated
  from . import models  # noqa: F401

  async with engine.begin() as conn:
    await conn.run_sync(SQLModel.metadata.create_all)
