import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from services.user_service import UserService
from models.user import User, UserRole


@pytest.fixture
def mock_user_repository():
    """Фикстура: создаем мок репозитория пользователей"""
    return AsyncMock()


@pytest.fixture
def user_service(mock_user_repository):
    """Фикстура для сервиса с мокнутым репозиторием"""
    return UserService(mock_user_repository)


@pytest.fixture
def sample_user_data():
    """Фикстура: тестовые данные пользователя"""
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "test_user",
        "full_name": "Test User",
        "role": UserRole.PARTICIPANT,
        "timezone": "UTC+3"
    }


class TestGetByTgId:
    # Тест для получения тг айди
    @pytest.mark.asyncio
    async def test_get_by_tg_id_user_exists(self, user_service, mock_user_repository, sample_user_data):
        # Создаем мок пользователя
        mock_user = Mock(spec=User)
        mock_user.id = sample_user_data["id"]
        mock_user.telegram_id = sample_user_data["telegram_id"]

        mock_user_repository.get_by_telegram_id.return_value = mock_user

        result = await user_service.get_by_tg_id(sample_user_data["telegram_id"])

        assert result is not None
        assert result.telegram_id == sample_user_data["telegram_id"]

        mock_user_repository.get_by_telegram_id.assert_called_once_with(sample_user_data["telegram_id"])

    # Тест для не найденного айди
    @pytest.mark.asyncio
    async def test_get_by_tg_id_user_not_found(self, user_service, mock_user_repository):
        mock_user_repository.get_by_telegram_id.return_value = None

        result = await user_service.get_by_tg_id(999999999)

        assert result is None
        mock_user_repository.get_by_telegram_id.assert_called_once_with(999999999)


class TestCreateUser:
    # Тест для успешного создания пользователя
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repository):
        # Используем патч чтобы не создавать реальный объект
        with patch('services.user_service.User') as MockUser:
            # мок класса User
            mock_user_instance = Mock()
            mock_user_instance.id = 1
            mock_user_instance.telegram_id = 123456789
            MockUser.return_value = mock_user_instance

            # мок репозитория
            mock_user_repository.create.return_value = mock_user_instance

            result = await user_service.create_user(
                tg_id=123456789,
                username="test_user",
                full_name="Test User",
                role=UserRole.PARTICIPANT.value,  # .value для строки
                tz="UTC+3"
            )


            assert result == mock_user_instance

            # Проверяем что User был создан с правильными параметрами
            MockUser.assert_called_once_with(
                telegram_id=123456789,
                username="test_user",
                full_name="Test User",
                role=UserRole.PARTICIPANT.value,
                timezone="UTC+3"
            )

            # Проверяем что репозиторий был вызван с нашим объектом
            mock_user_repository.create.assert_called_once_with(mock_user_instance)

    # Тест для создания пользователя без username
    @pytest.mark.asyncio
    async def test_create_user_without_username(self, user_service, mock_user_repository):
        with patch('services.user_service.User') as MockUser:
            mock_user_instance = Mock()
            MockUser.return_value = mock_user_instance
            mock_user_repository.create.return_value = mock_user_instance

            # Создаем пользователя без username
            await user_service.create_user(
                tg_id=123456790,
                username=None,
                full_name="User Without Username",
                role=UserRole.PARTICIPANT.value,
                tz="UTC+3"
            )

            # Проверяем что username передается как None
            MockUser.assert_called_once_with(
                telegram_id=123456790,
                username=None,
                full_name="User Without Username",
                role=UserRole.PARTICIPANT.value,
                timezone="UTC+3"
            )


class TestGetAll:
    # Тест для получения всех пользователей когда они есть
    @pytest.mark.asyncio
    async def test_get_all_with_users(self, user_service, mock_user_repository):
        # Создаем моков пользователей
        user1 = Mock(id=1, full_name="User 1")
        user2 = Mock(id=2, full_name="User 2")
        user3 = Mock(id=3, full_name="User 3")

        mock_user_repository.get_all.return_value = [user1, user2, user3]

        result = await user_service.get_all()

        assert len(result) == 3
        assert result[0].id == 1
        assert result[1].id == 2
        assert result[2].id == 3

        mock_user_repository.get_all.assert_called_once()

    # Тест для получения всех пользователей когда их нет
    @pytest.mark.asyncio
    async def test_get_all_empty(self, user_service, mock_user_repository):
        # Настраиваем возврат пустого списка
        mock_user_repository.get_all.return_value = []

        result = await user_service.get_all()

        assert result == []
        assert len(result) == 0

        # Проверяем что метод репозитория был вызван
        mock_user_repository.get_all.assert_called_once()


class TestGetAllParticipants:
    # Тест для получения всех участников когда они есть
    @pytest.mark.asyncio
    async def test_get_all_participants_exists(self, user_service, mock_user_repository):
        # Создаем моков участников с правильной ролью
        participant1 = Mock(role=UserRole.PARTICIPANT, full_name="Participant 1")
        participant2 = Mock(role=UserRole.PARTICIPANT, full_name="Participant 2")

        mock_user_repository.get_all_participants.return_value = [participant1, participant2]

        result = await user_service.get_all_participants()


        assert len(result) == 2
        # Проверяем что все имеют роль PARTICIPANT
        assert all(user.role == UserRole.PARTICIPANT for user in result)

        mock_user_repository.get_all_participants.assert_called_once()

    # Тест для получения всех участников когда их нет
    @pytest.mark.asyncio
    async def test_get_all_participants_empty(self, user_service, mock_user_repository):
        # Настраиваем возврат пустого списка
        mock_user_repository.get_all_participants.return_value = []

        result = await user_service.get_all_participants()

        assert result == []

        mock_user_repository.get_all_participants.assert_called_once()


class TestDeleteUser:
    # Тест для успешного удаления пользователя
    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_user_repository):
        # Создаем мок пользователя который будет найден
        user_mock = Mock()
        user_mock.id = 1
        user_mock.telegram_id = 123456789

        # Настраиваем мок репозитория
        mock_user_repository.get_by_telegram_id.return_value = user_mock

        await user_service.delete_user(123456789)

        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)
        mock_user_repository.delete_hard.assert_called_once_with(1)

    # Тест для попытки удалить несуществующего пользователя
    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service, mock_user_repository):
        # Настраиваем мок чтобы пользователь не был найден
        mock_user_repository.get_by_telegram_id.return_value = None

        await user_service.delete_user(999999999)

        mock_user_repository.get_by_telegram_id.assert_called_once_with(999999999)
        mock_user_repository.delete_hard.assert_not_called()


class TestUpdateUserByTgId:
    # Тест для успешного обновления пользователя
    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_user_repository):
        # Создаем мок пользователя
        user_mock = Mock()
        user_mock.id = 1
        user_mock.telegram_id = 123456789

        mock_user_repository.get_by_telegram_id.return_value = user_mock

        await user_service.update_user_by_tg_id(
            tg_id=123456789,
            full_name="Updated Name",
            timezone="UTC+5"
        )

        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)

        mock_user_repository.update.assert_called_once_with(
            1,  # ID пользователя
            full_name="Updated Name",
            timezone="UTC+5"
        )

    # Тест для попытки обновить несуществующего пользователя
    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service, mock_user_repository):
        # Настраиваем мок чтобы пользователь не был найден
        mock_user_repository.get_by_telegram_id.return_value = None

        await user_service.update_user_by_tg_id(
            tg_id=999999999,
            full_name="New Name"
        )

        mock_user_repository.get_by_telegram_id.assert_called_once_with(999999999)

        mock_user_repository.update.assert_not_called()

    # Тест для обновления только одного поля
    @pytest.mark.asyncio
    async def test_update_user_partial_fields(self, user_service, mock_user_repository):
        # Создаем мок пользователя
        user_mock = Mock()
        user_mock.id = 1
        user_mock.telegram_id = 123456789

        mock_user_repository.get_by_telegram_id.return_value = user_mock

        await user_service.update_user_by_tg_id(
            tg_id=123456789,
            timezone="UTC+8"
        )

        mock_user_repository.update.assert_called_once_with(
            1,
            timezone="UTC+8"
        )


# Дополнительные интеграционные тесты
class TestUserServiceIntegration:
    # Тест для проверки цепочки действий
    @pytest.mark.asyncio
    async def test_create_and_get_user_flow(self, mock_user_repository):
        # Создаем сервис
        service = UserService(mock_user_repository)

        # Используем патч для создания пользователя
        with patch('services.user_service.User') as MockUser:
            # Создаем мок пользователя
            created_user = Mock()
            created_user.id = 1
            created_user.telegram_id = 123456789

            # Настраиваем моки
            MockUser.return_value = created_user
            mock_user_repository.create.return_value = created_user

            await service.create_user(
                tg_id=123456789,
                username="test",
                full_name="Test User",
                role=UserRole.PARTICIPANT.value,
                tz="UTC+3"
            )

            # Сбрасываем моки для следующего вызова
            mock_user_repository.reset_mock()

            mock_user_repository.get_by_telegram_id.return_value = created_user
            retrieved_user = await service.get_by_tg_id(123456789)

            # Проверяем что пользователь тот же
            assert retrieved_user == created_user
            assert retrieved_user.telegram_id == 123456789

