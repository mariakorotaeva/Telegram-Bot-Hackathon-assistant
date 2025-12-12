# check_tables.py
import asyncio
from sqlalchemy import text
from config.database import engine


async def check_tables():
    print("🔍 Проверяем созданные таблицы в PostgreSQL...")

    async with engine.connect() as conn:
        # Проверяем таблицу users
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """))

        print("\n📊 Таблица 'users':")
        for row in result:
            print(f"  • {row[0]:20} {row[1]:20} {'NULL' if row[2] == 'YES' else 'NOT NULL'}")

        # Проверяем таблицу teams
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'teams'
            ORDER BY ordinal_position;
        """))

        print("\n📊 Таблица 'teams':")
        for row in result:
            print(f"  • {row[0]:20} {row[1]:20} {'NULL' if row[2] == 'YES' else 'NOT NULL'}")

        # Проверяем таблицу team_applications
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'team_applications'
            ORDER BY ordinal_position;
        """))

        print("\n📊 Таблица 'team_applications':")
        for row in result:
            print(f"  • {row[0]:20} {row[1]:20} {'NULL' if row[2] == 'YES' else 'NOT NULL'}")


if __name__ == "__main__":
    asyncio.run(check_tables())