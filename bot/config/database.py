# config/database.py
"""
Конфигурация базы данных.
Этот файл содержит настройки подключения к PostgreSQL и создаёт основной движок БД.
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей (таблиц).
    Все наши модели (User, Team, Event) будут наследоваться от этого класса.
    """
    pass


# Получаем URL базы данных из переменной окружения или используем значение по умолчанию
# Формат: postgresql+asyncpg://username:password@host:port/database_name
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/hackathon_bot"
    # postgresql+asyncpg:// - протокол PostgreSQL с асинхронным драйвером asyncpg
    # postgres:password      - логин:пароль для подключения к БД
    # localhost:5432        - хост (компьютер) и порт где работает PostgreSQL
    # hackathon_bot         - имя базы данных
)

# Создаём асинхронный движок (engine) для подключения к БД
# echo=True означает, что все SQL-запросы будут выводиться в консоль (удобно для отладки)
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаём фабрику сессий (session factory)
# Сессия - это объект, через который мы выполняем все операции с БД
AsyncSessionLocal = async_sessionmaker(
    engine,  # используем наш движок
    class_=AsyncSession,  # тип сессии (асинхронная)
    expire_on_commit=False  # объекты не сбрасываются после коммита
)


async def get_db() -> AsyncSession:
    """
    Функция-генератор для получения сессии БД.
    Используется как dependency в FastAPI.

    Пример использования:
    async with get_db() as session:
        user = await session.get(User, 1)

    Важно: сессия автоматически закрывается после использования.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session  # отдаём сессию тому, кто её запросил
        finally:
            await session.close()  # обязательно закрываем соединение