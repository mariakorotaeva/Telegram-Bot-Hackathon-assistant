# config/database.py
"""
Конфигурация базы данных для проекта Хакатон-ассистент.
Этот файл содержит все настройки для подключения к PostgreSQL.
"""

# 1. Импортируем необходимые модули
import os
# Эти модули из SQLAlchemy позволяют работать с БД асинхронно
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


# 2. Создаём базовый класс для всех наших моделей (таблиц)
class Base(DeclarativeBase):
    """
    Базовый класс для всех моделей (таблиц) в нашем проекте.
    Все модели (User, Team, Event) будут наследоваться от этого класса.
    Это нужно, чтобы SQLAlchemy знал, какие таблицы создавать.
    """
    pass


# 3. Настраиваем подключение к базе данных
# Формат строки подключения: postgresql+asyncpg://логин:пароль@хост:порт/имя_базы
DATABASE_URL = os.getenv(
    "DATABASE_URL",  # Сначала пытаемся взять из переменной окружения
    # Если переменной нет, используем значение по умолчанию:
    "postgresql+asyncpg://postgres:password@localhost:5432/hackathon_bot"
    # Разберём по частям:
    # postgresql+asyncpg:// - протокол PostgreSQL с асинхронным драйвером asyncpg
    # postgres:password     - логин и пароль для подключения к PostgreSQL
    # localhost:5432       - хост (компьютер) и порт, где работает PostgreSQL
    # hackathon_bot        - имя нашей базы данных (её нужно будет создать)
)

# 4. Создаём "движок" (engine) для подключения к БД
# Engine - это основной объект, который управляет подключениями к БД
engine = create_async_engine(
    DATABASE_URL,  # Используем нашу строку подключения
    echo=True  # Выводит все SQL-запросы в консоль (очень полезно для отладки!)
)

# 5. Создаём фабрику сессий (session factory)
# Сессия (session) - это объект, через который мы выполняем все операции с БД
# (добавление, удаление, изменение, поиск данных)
AsyncSessionLocal = async_sessionmaker(
    engine,  # Используем наш движок
    class_=AsyncSession,  # Тип сессии - асинхронная
    expire_on_commit=False  # Объекты не сбрасываются после сохранения (коммита)
)


# 6. Создаём функцию для получения сессии
# Эта функция будет использоваться в обработчиках бота и API
async def get_db() -> AsyncSession:
    """
    Функция-генератор для получения сессии БД.

    Использование:
    async with get_db() as session:
        # Здесь работаем с БД через session

    Важно: сессия автоматически закрывается после выхода из блока with
    """
    async with AsyncSessionLocal() as session:
        try:
            # Отдаём сессию тому, кто её запросил
            yield session
        finally:
            # Всегда закрываем сессию, даже если произошла ошибка
            await session.close()


# 7. Функция для создания всех таблиц в БД (будет использоваться при запуске)
async def create_tables():
    """
    Создаёт все таблицы в базе данных на основе наших моделей.
    Вызывается один раз при первом запуске приложения.
    """
    async with engine.begin() as conn:
        # Создаём все таблицы, определённые в моделях, которые наследуются от Base
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Все таблицы успешно созданы!")


# 8. Функция для удаления всех таблиц (только для тестов и разработки!)
async def drop_tables():
    """
    УДАЛЯЕТ ВСЕ ТАБЛИЦЫ из базы данных.
    Использовать только для тестов или полного сброса!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("⚠️ Все таблицы удалены!")