import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
from services.schedule_service import ScheduleService
from models.schedule import Event, EventChangeType
from models.user import UserRole


@pytest.fixture
def mock_schedule_repository():
    return AsyncMock()


@pytest.fixture
def mock_user_repository():
    return AsyncMock()


@pytest.fixture
def schedule_service(mock_schedule_repository, mock_user_repository):
    with patch('services.schedule_service.UserService') as MockUserService:
        mock_user_service = MockUserService.return_value
        mock_user_service.get_all.return_value = []

        return ScheduleService(mock_schedule_repository, mock_user_repository)


@pytest.fixture
def sample_event_data():
    return {
        "id": 1,
        "title": "Test Event",
        "description": "Test Description",
        "start_time": datetime.now(),
        "end_time": datetime.now() + timedelta(hours=2),
        "visibility": ["all"],
        "location": "Test Location",
        "created_by": "123",
        "creator_timezone": "UTC+3"
    }


class TestAddEvent:
    # Тест для успешного добавления события
    @pytest.mark.asyncio
    async def test_add_event_success(self, schedule_service, mock_schedule_repository, mock_user_repository):
        mock_event = Mock()
        mock_event.id = 1
        mock_event.to_dict.return_value = {"id": 1, "title": "Test Event"}
        mock_schedule_repository.create_event.return_value = mock_event

        mock_user = Mock()
        mock_user.id = 1
        mock_user_repository.get_by_telegram_id.return_value = mock_user

        result = await schedule_service.add_event(
            title="Test Event",
            description="Test Description",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=2),
            visibility=["all"],
            location="Test Location",
            created_by="123",
            creator_timezone="UTC+3"
        )

        assert result["id"] == 1
        assert result["title"] == "Test Event"
        mock_schedule_repository.create_event.assert_called_once()
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123)

    # Тест для добавления события без created_by
    @pytest.mark.asyncio
    async def test_add_event_no_creator(self, schedule_service, mock_schedule_repository):
        mock_event = Mock()
        mock_event.id = 1
        mock_event.to_dict.return_value = {"id": 1}
        mock_schedule_repository.create_event.return_value = mock_event

        result = await schedule_service.add_event(
            title="Test Event",
            description="Test Description",
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(hours=2),
            visibility=["all"],
            location="",
            created_by="",
            creator_timezone="UTC+3"
        )

        assert result["id"] == 1
        mock_schedule_repository.create_event.assert_called_once()


class TestGetEventsForRole:
    # Тест для получения событий для роли
    @pytest.mark.asyncio
    async def test_get_events_for_role_success(self, schedule_service, mock_schedule_repository):
        mock_event = Mock()
        mock_event.start_time = datetime.now()
        mock_event.end_time = datetime.now() + timedelta(hours=2)
        mock_event.creator_timezone = "UTC+3"
        mock_event.to_dict.return_value = {"title": "Test Event"}

        mock_schedule_repository.get_events_for_role.return_value = [mock_event]

        result = await schedule_service.get_events_for_role(
            role="participant",
            user_timezone="UTC+3",
            include_all=True
        )

        assert len(result) == 1
        assert result[0]["title"] == "Test Event"
        mock_schedule_repository.get_events_for_role.assert_called_once_with("participant", "UTC+3", True)


class TestGetEventById:
    # Тест для получения события по ID
    @pytest.mark.asyncio
    async def test_get_event_by_id_success(self, schedule_service, mock_schedule_repository):
        mock_event = Mock()
        mock_event.to_dict.return_value = {"id": 1, "title": "Test Event"}
        mock_schedule_repository.get_event_by_id.return_value = mock_event

        result = await schedule_service.get_event_by_id(1)

        assert result["id"] == 1
        assert result["title"] == "Test Event"
        mock_schedule_repository.get_event_by_id.assert_called_once_with(1)

    # Тест для получения несуществующего события
    @pytest.mark.asyncio
    async def test_get_event_by_id_not_found(self, schedule_service, mock_schedule_repository):
        mock_schedule_repository.get_event_by_id.return_value = None

        result = await schedule_service.get_event_by_id(999)

        assert result is None
        mock_schedule_repository.get_event_by_id.assert_called_once_with(999)


class TestUpdateEvent:
    # Тест для успешного обновления события
    @pytest.mark.asyncio
    async def test_update_event_success(self, schedule_service, mock_schedule_repository):
        mock_schedule_repository.update_event.return_value = True

        mock_event = Mock()
        mock_schedule_repository.get_event_by_id.return_value = mock_event

        result = await schedule_service.update_event(
            event_id=1,
            title="Updated Title",
            description="Updated Description"
        )

        assert result is True
        mock_schedule_repository.update_event.assert_called_once_with(1, title="Updated Title",
                                                                      description="Updated Description")
        mock_schedule_repository.get_event_by_id.assert_called_once_with(1)

    # Тест для обновления несуществующего события
    @pytest.mark.asyncio
    async def test_update_event_not_found(self, schedule_service, mock_schedule_repository):
        mock_schedule_repository.update_event.return_value = False

        result = await schedule_service.update_event(
            event_id=999,
            title="Updated Title"
        )

        assert result is False
        mock_schedule_repository.update_event.assert_called_once_with(999, title="Updated Title")


class TestDeleteEvent:
    # Тест для успешного удаления события
    @pytest.mark.asyncio
    async def test_delete_event_success(self, schedule_service, mock_schedule_repository):
        mock_event = Mock()
        mock_event.to_dict.return_value = {"id": 1, "title": "Test Event"}
        mock_schedule_repository.get_event_by_id.return_value = mock_event
        mock_schedule_repository.delete_event_hard.return_value = None

        result = await schedule_service.delete_event(1)

        assert result is True
        mock_schedule_repository.get_event_by_id.assert_called_once_with(1)
        mock_schedule_repository.create_event_log.assert_called_once()

    # Тест для удаления несуществующего события
    @pytest.mark.asyncio
    async def test_delete_event_not_found(self, schedule_service, mock_schedule_repository):
        mock_schedule_repository.get_event_by_id.return_value = None

        result = await schedule_service.delete_event(999)

        assert result is False
        mock_schedule_repository.get_event_by_id.assert_called_once_with(999)


class TestGetAllEvents:
    # Тест для получения всех событий
    @pytest.mark.asyncio
    async def test_get_all_events_success(self, schedule_service, mock_schedule_repository):
        mock_event1 = Mock()
        mock_event1.to_dict.return_value = {"id": 1, "title": "Event 1"}

        mock_event2 = Mock()
        mock_event2.to_dict.return_value = {"id": 2, "title": "Event 2"}

        mock_schedule_repository.get_all_events.return_value = [mock_event1, mock_event2]

        result = await schedule_service.get_all_events()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        mock_schedule_repository.get_all_events.assert_called_once()

    # Тест для получения пустого списка событий
    @pytest.mark.asyncio
    async def test_get_all_events_empty(self, schedule_service, mock_schedule_repository):
        mock_schedule_repository.get_all_events.return_value = []

        result = await schedule_service.get_all_events()

        assert result == []
        mock_schedule_repository.get_all_events.assert_called_once()


class TestFormatEventForDisplay:
    # Тест для форматирования события для отображения
    def test_format_event_for_display(self, schedule_service):
        event_data = {
            "title": "Test Event",
            "start_time": datetime(2024, 1, 15, 10, 0, 0),
            "end_time": datetime(2024, 1, 15, 12, 0, 0),
            "location": "Test Location",
            "description": "Test Description",
            "visibility": ["all"],
            "creator_timezone": "UTC+3"
        }

        result = schedule_service.format_event_for_display(event_data, "UTC+3")

        assert "Test Event" in result
        assert "10:00" in result
        assert "12:00" in result
        assert "Test Location" in result
        assert "Test Description" in result

    # Тест для форматирования события без некоторых полей
    def test_format_event_for_display_minimal(self, schedule_service):
        event_data = {
            "title": "Test Event",
            "start_time": datetime(2024, 1, 15, 10, 0, 0),
            "end_time": datetime(2024, 1, 15, 12, 0, 0),
            "visibility": ["participant", "mentor"]
        }

        result = schedule_service.format_event_for_display(event_data, "UTC+3")

        assert "Test Event" in result
        assert "👤" in result
        assert "🧠" in result


class TestAddEventWithNotification:
    # Тест для добавления события с уведомлением
    @pytest.mark.asyncio
    async def test_add_event_with_notification(self, schedule_service, mock_schedule_repository):
        with patch.object(schedule_service, '_notify_new_event') as mock_notify:
            mock_event = Mock()
            mock_event.id = 1
            mock_event.to_dict.return_value = {"id": 1, "title": "Test Event"}
            mock_schedule_repository.create_event.return_value = mock_event
            mock_schedule_repository.get_event_by_id.return_value = mock_event

            mock_user_repository = Mock()
            mock_user_repository.get_by_telegram_id.return_value = Mock()

            result = await schedule_service.add_event_with_notification(
                title="Test Event",
                description="Test Description",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=2),
                visibility=["all"],
                location="Test Location",
                created_by="123",
                creator_timezone="UTC+3",
                bot=None
            )

            assert result["id"] == 1
            assert result["title"] == "Test Event"
            mock_notify.assert_not_called()


class TestUpdateEventWithNotification:
    # Тест для обновления события с уведомлением
    @pytest.mark.asyncio
    async def test_update_event_with_notification(self, schedule_service, mock_schedule_repository):
        with patch.object(schedule_service, '_notify_event_updated') as mock_notify:
            mock_schedule_repository.update_event.return_value = True

            mock_old_event = Mock()
            mock_old_event.title = "Old Title"
            mock_schedule_repository.get_event_by_id.return_value = mock_old_event

            result = await schedule_service.update_event_with_notification(
                event_id=1,
                title="New Title",
                bot=None
            )

            assert result is True
            mock_schedule_repository.update_event.assert_called_once_with(1, title="New Title")
            mock_notify.assert_not_called()


class TestDeleteEventWithNotification:
    # Тест для удаления события с уведомлением
    @pytest.mark.asyncio
    async def test_delete_event_with_notification(self, schedule_service, mock_schedule_repository):
        with patch.object(schedule_service, '_notify_event_cancelled') as mock_notify:
            mock_event = Mock()
            mock_event.to_dict.return_value = {"id": 1, "title": "Test Event"}
            mock_schedule_repository.get_event_by_id.return_value = mock_event
            mock_schedule_repository.delete_event_hard.return_value = None

            result = await schedule_service.delete_event_with_notification(
                event_id=1,
                bot=None
            )

            assert result is True
            mock_notify.assert_not_called()


class TestGetUpcomingEventsForRole:
    # Тест для получения ближайших событий для роли
    @pytest.mark.asyncio
    async def test_get_upcoming_events_for_role(self, schedule_service, mock_schedule_repository):
        mock_event = Mock()
        mock_event.start_time = datetime.now() + timedelta(hours=1)
        mock_event.end_time = datetime.now() + timedelta(hours=3)
        mock_event.creator_timezone = "UTC+3"
        mock_event.to_dict.return_value = {"title": "Upcoming Event"}

        mock_schedule_repository.get_upcoming_events.return_value = [mock_event]

        result = await schedule_service.get_upcoming_events_for_role(
            role="participant",
            hours_ahead=24,
            user_timezone="UTC+3"
        )

        assert len(result) == 1
        assert result[0]["title"] == "Upcoming Event"
        mock_schedule_repository.get_upcoming_events.assert_called_once_with(24, "participant")


class TestConvertTimeForUser:
    # Тест для конвертации времени
    def test_convert_time_for_user_same_timezone(self, schedule_service):
        event_time = datetime(2024, 1, 15, 10, 0, 0)
        result = schedule_service._convert_time_for_user(
            event_time=event_time,
            event_timezone="UTC+3",
            user_timezone="UTC+3"
        )

        assert result == event_time

    # Тест для конвертации времени в другой часовой пояс
    def test_convert_time_for_user_different_timezone(self, schedule_service):
        event_time = datetime(2024, 1, 15, 10, 0, 0)
        result = schedule_service._convert_time_for_user(
            event_time=event_time,
            event_timezone="UTC+3",
            user_timezone="UTC+5"
        )

        assert result == event_time + timedelta(hours=2)


