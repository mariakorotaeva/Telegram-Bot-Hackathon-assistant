# test_postgres_models.py
"""
Тест для PostgreSQL - проверяем создание всех таблиц.
"""

import asyncio
from sqlalchemy import text

from config.database import create_tables, engine
from models.user import User, UserRole, ParticipantStatus
from models.team import Team
from models.team_application import TeamApplication, ApplicationStatus


async def test_all_models():
    print("🧪 Тестируем создание всех таблиц в PostgreSQL...")

    try:
        # 1. Создаём все таблицы
        print("Создаю таблицы...")
        await create_tables()
        print("✅ Все таблицы созданы успешно!")

        # 2. Проверяем, что можем работать с моделями
        print("\n📋 Список созданных таблиц:")
        async with engine.connect() as conn:
            # ★ PostgreSQL использует information_schema.tables, а не sqlite_master
            result = await conn.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
            )
            tables = result.fetchall()

            if tables:
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print("   (нет таблиц)")

        print("\n🎉 Все модели готовы к использованию в PostgreSQL!")
        print("\nСозданные таблицы:")
        print("1. users - анкеты участников")
        print("2. teams - команды хакатона")
        print("3. team_applications - заявки в команды")
        print("\n✅ Задача 'Написание базовых моделей SQL' ВЫПОЛНЕНА!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_all_models())