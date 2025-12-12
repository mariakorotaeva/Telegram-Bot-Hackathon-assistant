# config/database.py
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Используй нового пользователя
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # Измени на свои данные:
    "postgresql+asyncpg://hackathon_user:hackathon123@localhost:5432/hackathon_bot"
    # Или если хочешь использовать postgres:
    # "postgresql+asyncpg://postgres:password123@localhost:5432/hackathon_bot"
)

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def create_tables():
    """Создаёт все таблицы в БД."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Все таблицы созданы!")