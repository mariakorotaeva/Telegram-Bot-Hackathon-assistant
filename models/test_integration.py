# test_postgres_models.py
"""
Тест для PostgreSQL - проверяем создание всех таблиц.
"""

import asyncio
from sqlalchemy import text

from config.database import create_tables, engine
from models.user import User, UserRole, ParticipantStatus
from models.team import Team


async def test_all_models():
    try:
        await create_tables()
        print("Все таблицы созданы")

        print("\n Cозданные таблицы:")
        async with engine.connect() as conn:
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
                print("Нет таблиц")

        print("\nВсе модели готовы к использованию!")

    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_all_models())