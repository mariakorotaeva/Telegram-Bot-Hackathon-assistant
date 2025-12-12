# final_test.py
import asyncio
from sqlalchemy import select
from config.database import AsyncSessionLocal
from models.user import User, UserRole
from models.team import Team
from models.team_application import TeamApplication, ApplicationStatus


async def test_all():
    print("🧪 Финальный тест всех компонентов БД...")

    async with AsyncSessionLocal() as session:
        try:
            # 1. Создаём пользователя
            user = User(
                telegram_id=1001,
                full_name="Тест Участник",
                role=UserRole.PARTICIPANT,
                desired_role="Backend Developer"
            )
            session.add(user)
            await session.flush()
            print("✅ Пользователь создан")

            # 2. Создаём команду
            team = Team(
                name="Тестовая Команда",
                captain_id=user.id,
                max_members=3
            )
            session.add(team)
            await session.flush()
            print("✅ Команда создана")

            # 3. Создаём заявку
            application = TeamApplication(
                user_id=user.id,
                team_id=team.id,
                message="Хочу присоединиться!"
            )
            session.add(application)
            await session.flush()
            print("✅ Заявка создана")

            # 4. Читаем данные обратно
            # Проверяем пользователя
            stmt = select(User).where(User.telegram_id == 1001)
            result = await session.execute(stmt)
            found_user = result.scalar_one()
            print(f"✅ Найден пользователь: {found_user.full_name}")

            # Проверяем команду
            stmt = select(Team).where(Team.captain_id == user.id)
            result = await session.execute(stmt)
            found_team = result.scalar_one()
            print(f"✅ Найдена команда: {found_team.name}")

            # Проверяем заявку
            stmt = select(TeamApplication).where(TeamApplication.user_id == user.id)
            result = await session.execute(stmt)
            found_app = result.scalar_one()
            print(f"✅ Найдена заявка со статусом: {found_app.status.value}")

            print("\n" + "=" * 50)
            print("🎉 ВСЁ РАБОТАЕТ ИДЕАЛЬНО!")
            print("\nБаза данных готова к использованию.")

            # 5. Очищаем тестовые данные
            await session.delete(application)
            await session.delete(team)
            await session.delete(user)
            await session.commit()
            print("🧹 Тестовые данные очищены")

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()


if __name__ == "__main__":
    asyncio.run(test_all())