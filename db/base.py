from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import DB_URL


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DB_URL, echo=False, pool_pre_ping=True)
session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Jadvallar bo'lmasa yaratadi."""
    from db import models  # noqa: F401  (modellar ro'yxatga tushishi uchun)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
