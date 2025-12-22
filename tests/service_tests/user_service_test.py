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
    # Статические данные для тестов
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "test_user",
        "full_name": "Test User",
        "role": UserRole.PARTICIPANT,
        "timezone": "UTC+3"
    }


class TestGetByTgId:
    """Тестируем метод получения пользователя по telegram ID"""

    @pytest.mark.asyncio
    async def test_get_by_tg_id_user_exists(self, user_service, mock_user_repository, sample_user_data):
        # Создаем мок пользователя
        mock_user = Mock(spec=User)
        mock_user.id = sample_user_data["id"]
        mock_user.telegram_id = sample_user_data["telegram_id"]

        # Настраиваем мок репозитория
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        # ACT: Действие
        result = await user_service.get_by_tg_id(sample_user_data["telegram_id"])

        # ASSERT: Проверка
        assert result is not None
        assert result.telegram_id == sample_user_data["telegram_id"]
        # Проверяем, что метод репозитория вызван с правильным аргументом
        mock_user_repository.get_by_telegram_id.assert_called_once_with(sample_user_data["telegram_id"])

    @pytest.mark.asyncio
    async def test_get_by_tg_id_user_not_found(self, user_service, mock_user_repository):
        """Тест 2: Пользователь не найден"""
        # ARRANGE: Настраиваем мок, чтобы вернул None
        mock_user_repository.get_by_telegram_id.return_value = None

        # ACT: Пытаемся получить несуществующего пользователя
        result = await user_service.get_by_tg_id(999999999)

        # ASSERT: Должен вернуться None
        assert result is None
        mock_user_repository.get_by_telegram_id.assert_called_once_with(999999999)

    @pytest.mark.asyncio
    async def test_get_by_tg_id_with_negative_id(self, user_service, mock_user_repository):
        """Тест 3: Передаем отрицательный ID (если такое возможно в логике)"""
        # ARRANGE: Мок возвращает None для отрицательного ID
        mock_user_repository.get_by_telegram_id.return_value = None

        # ACT: Вызываем с отрицательным ID
        result = await user_service.get_by_tg_id(-123)

        # ASSERT: Проверяем корректность вызова
        assert result is None
        mock_user_repository.get_by_telegram_id.assert_called_once_with(-123)