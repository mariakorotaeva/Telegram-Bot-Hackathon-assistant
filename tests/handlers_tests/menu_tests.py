import sys
from unittest.mock import AsyncMock, MagicMock, patch
from models.user import User, UserRole, ParticipantStatus
import pytest


mock_user_model = MagicMock()
mock_user_model.User = MagicMock()

sys.modules['models.user'] = mock_user_model

from bot.handlers.menu import router, _show_menu
from aiogram.types import Message, CallbackQuery


class TestMenuHandlers:
    """Тесты для обработчиков меню"""

    @pytest.fixture
    def mock_message(self):
        message = AsyncMock(spec=Message)
        message.from_user = MagicMock()
        message.from_user.id = 123456
        message.answer = AsyncMock()
        return message

    @pytest.fixture
    def mock_callback(self):
        callback = AsyncMock(spec=CallbackQuery)
        callback.from_user = MagicMock()
        callback.from_user.id = 123456
        callback.message = AsyncMock()
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        return callback

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.id = 1
        user.telegram_id = 123456
        user.role = "participant"
        user.full_name = "Test User"
        return user

    @pytest.mark.asyncio
    @patch('bot.handlers.menu.UserService')
    async def test_show_menu_command_no_user(self, MockUserService, mock_message):
        mock_service = MockUserService.return_value
        mock_service.get_by_tg_id = AsyncMock(return_value=None)

        from bot.handlers.menu import show_menu_command
        await show_menu_command(mock_message)

        mock_message.answer.assert_called_once_with(
            "❌ Сначала зарегистрируйтесь с помощью /start",
            show_alert=True
        )

    @pytest.mark.asyncio
    @patch('bot.handlers.menu.UserService')
    async def test_show_faq_no_user(self, MockUserService, mock_callback):
        mock_service = MockUserService.return_value
        mock_service.get_by_tg_id = AsyncMock(return_value=None)

        from bot.handlers.menu import show_faq
        await show_faq(mock_callback)

        mock_callback.answer.assert_called_once_with(
            "❌ Сначала зарегистрируйтесь с помощью /start",
            show_alert=True
        )

    @pytest.mark.asyncio
    @patch('bot.handlers.menu.UserService')
    async def test_back_to_menu_no_user(self, MockUserService, mock_callback):
        mock_service = MockUserService.return_value
        mock_service.get_by_tg_id = AsyncMock(return_value=None)

        from bot.handlers.menu import back_to_menu
        await back_to_menu(mock_callback)

        mock_callback.answer.assert_called_once_with(
            "❌ Сначала зарегистрируйтесь с помощью /start",
            show_alert=True
        )

    @pytest.mark.asyncio
    @patch('bot.handlers.menu.parse_users_to_sheet')
    @patch('bot.handlers.menu.UserService')
    async def test_admin_parse_users_organizer_success(self, MockUserService, mock_parse, mock_callback, mock_user):
        mock_user.role = "organizer"
        mock_service = MockUserService.return_value
        mock_service.get_by_tg_id = AsyncMock(return_value=mock_user)
        mock_parse.return_value = "https://example.com/sheet"

        from bot.handlers.menu import admin_parse_users
        await admin_parse_users(mock_callback)

        mock_service.get_by_tg_id.assert_called_once_with(123456)
        mock_parse.assert_called_once()
        mock_callback.message.edit_text.assert_called_once()

    @pytest.mark.asyncio
    @patch('bot.handlers.menu.UserService')
    async def test_admin_parse_users_not_organizer(self, MockUserService, mock_callback, mock_user):
        mock_user.role = "participant"
        mock_service = MockUserService.return_value
        mock_service.get_by_tg_id = AsyncMock(return_value=mock_user)

        from bot.handlers.menu import admin_parse_users
        await admin_parse_users(mock_callback)

        mock_callback.answer.assert_called_once_with(
            "❌ Команда доступна только организаторам",
            show_alert=True
        )

