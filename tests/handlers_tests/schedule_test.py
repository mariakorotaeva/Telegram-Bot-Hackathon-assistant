import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from unittest.mock import AsyncMock, Mock, patch
from aiogram.types import CallbackQuery, User, Message
from bot.handlers.schedule import router, show_schedule, start_add_event, ScheduleStates
from datetime import datetime


class TestScheduleSimpleHandlers:

    @pytest.fixture
    def mock_callback(self):
        callback = AsyncMock(spec=CallbackQuery)
        callback.from_user = Mock(id=123)
        callback.message = AsyncMock()
        callback.answer = AsyncMock()
        return callback

    @pytest.mark.asyncio
    async def test_show_schedule_user_not_found(self, mock_callback):
        """Тест: пользователь не найден"""
        with patch('bot.handlers.schedule.UserService') as MockUserService:
            mock_service = MockUserService.return_value
            mock_service.get_by_tg_id = AsyncMock(return_value=None)

            await show_schedule(mock_callback)

            mock_callback.answer.assert_called_once_with(
                "❌ Сначала зарегистрируйтесь с помощью /start",
                show_alert=True
            )

    @pytest.mark.asyncio
    async def test_show_schedule_no_events(self, mock_callback):
        """Тест: нет событий в расписании"""
        with patch('bot.handlers.schedule.UserService') as MockUserService, \
                patch('bot.handlers.schedule.ScheduleService') as MockScheduleService:
            # Мокаем пользователя
            mock_user = Mock(role="participant", timezone="UTC")
            MockUserService.return_value.get_by_tg_id = AsyncMock(return_value=mock_user)

            # Мокаем отсутствие событий
            MockScheduleService.return_value.get_events_for_role = AsyncMock(return_value=[])

            await show_schedule(mock_callback)

            mock_callback.message.edit_text.assert_called_once()
            args = mock_callback.message.edit_text.call_args
            assert "На данный момент событий нет" in args[0][0]

    @pytest.mark.asyncio
    async def test_show_schedule_with_events(self, mock_callback):
        with patch('bot.handlers.schedule.UserService') as MockUserService, \
                patch('bot.handlers.schedule.ScheduleService') as MockScheduleService:
            # Мокаем пользователя
            mock_user = Mock(role="participant", timezone="UTC")
            MockUserService.return_value.get_by_tg_id = AsyncMock(return_value=mock_user)

            # Мокаем события
            from datetime import datetime, timedelta
            mock_event = {
                "id": 1,
                "title": "Тестовое событие",
                "start_time_local": datetime.now() + timedelta(hours=1),
                "end_time_local": datetime.now() + timedelta(hours=2),
                "location": "Тестовая локация"
            }
            MockScheduleService.return_value.get_events_for_role = AsyncMock(return_value=[mock_event])

            await show_schedule(mock_callback)

            mock_callback.message.edit_text.assert_called_once()
            args = mock_callback.message.edit_text.call_args
            assert "Тестовое событие" in args[0][0]
            assert "Тестовая локация" in args[0][0]


    class TestScheduleFSMHandlers:

        @pytest.fixture
        def mock_state(self):
            state = AsyncMock(spec=FSMContext)
            state.clear = AsyncMock()
            state.set_state = AsyncMock()
            state.update_data = AsyncMock()
            state.get_data = AsyncMock(return_value={})
            return state

        @pytest.mark.asyncio
        async def test_start_add_event(self, mock_callback, mock_state):
            """Тест: начало добавления события"""
            await start_add_event(mock_callback, mock_state)

            mock_state.clear.assert_called_once()
            mock_state.set_state.assert_called_once_with(ScheduleStates.waiting_for_title)
            mock_state.update_data.assert_called_once_with(visibility=[])

            mock_callback.message.edit_text.assert_called_once()
            args = mock_callback.message.edit_text.call_args
            assert "Добавление нового события" in args[0][0]


class TestScheduleIntegration:

    @pytest.mark.asyncio
    async def test_process_event_title_success(self):
        """Тест: успешная обработка названия события"""
        from aiogram.types import Message
        from bot.handlers.schedule import process_event_title

        message = AsyncMock(spec=Message)
        message.text = "Тестовое событие"
        message.answer = AsyncMock()

        state = AsyncMock()
        state.update_data = AsyncMock()
        state.set_state = AsyncMock()

        await process_event_title(message, state)

        state.update_data.assert_called_once_with(title="Тестовое событие")
        state.set_state.assert_called_once()

        message.answer.assert_called_once()
        assert "описание" in message.answer.call_args[0][0].lower()