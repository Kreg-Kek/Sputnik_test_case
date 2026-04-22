import os

from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine
)
from contextlib import asynccontextmanager
from typing import AsyncGenerator


Base = declarative_base()



dsn = (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER','')}:"
    f"{os.getenv('POSTGRES_PASSWORD','')}@{os.getenv('POSTGRES_HOST','localhost')}:"
    f"{os.getenv('PGPORT', int(os.getenv('POSTGRES_PORT', '5432')))}/{os.getenv('POSTGRES_DB','')}"
)

engine = create_async_engine(dsn, echo=False, future=True, pool_size=100)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def create_database() -> None:
    """Create tables."""

    async with engine.begin() as db_engine:
        await db_engine.run_sync(Base.metadata.drop_all) #Строка для пересоздания таблиц
        await db_engine.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get assync db session."""

    async with async_session() as session:
        yield session