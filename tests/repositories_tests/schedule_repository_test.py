# tests/test_schedule_repository.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine.result import ScalarResult
from datetime import datetime, timedelta

from repositories.schedule_repository import ScheduleRepository
from models.schedule import Event, EventLog, EventNotification, EventChangeType
from models.user import User, UserRole


class TestScheduleRepository:
    """Тесты для ScheduleRepository"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_event(self):
        event = MagicMock(spec=Event)
        event.id = 1
        event.title = "Test Event"
        event.description = "Test Description"
        event.start_time = datetime.utcnow() + timedelta(hours=1)
        event.end_time = datetime.utcnow() + timedelta(hours=2)
        event.location = "Test Location"
        event.visibility = ["all"]
        event.is_active = True
        event.created_by = 1
        return event

    @pytest.fixture
    def mock_event_log(self):
        log = MagicMock(spec=EventLog)
        log.id = 1
        log.event_id = 1
        log.changed_by = 1
        log.change_type = EventChangeType.CREATED
        log.old_values = {}
        log.new_values = {}
        log.changed_at = datetime.utcnow()
        return log

    @pytest.fixture
    def mock_notification(self):
        notification = MagicMock(spec=EventNotification)
        notification.id = 1
        notification.user_id = 1
        notification.event_id = 1
        notification.notification_type = "reminder"
        notification.sent_at = datetime.utcnow()
        notification.read_at = None
        return notification

    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = 1
        user.is_active = True
        user.role = UserRole.PARTICIPANT
        return user

    @pytest.fixture
    def repo(self):
        return ScheduleRepository()

    @pytest.mark.asyncio
    async def test_delete_event_soft_success(self, repo, mock_session):
        with patch.object(repo, 'update_event', AsyncMock(return_value=True)):
            result = await repo.delete_event_soft(1)

            assert result is True
            repo.update_event.assert_called_once_with(1, is_active=False)

    @pytest.mark.asyncio
    async def test_has_notification_true(self, repo, mock_session, mock_notification):
        with patch('repositories.schedule_repository.get_db', return_value=mock_session):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=mock_notification)
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await repo.has_notification(1, 1, "reminder")

            assert result is True

    @pytest.mark.asyncio
    async def test_is_visible_for_role_all_visibility(self, repo, mock_event):
        mock_event.visibility = ["all"]
        result = repo._is_visible_for_role(mock_event, UserRole.PARTICIPANT)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_visible_for_role_specific_role_match(self, repo, mock_event):
        mock_event.visibility = [UserRole.PARTICIPANT]
        result = repo._is_visible_for_role(mock_event, UserRole.PARTICIPANT)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_visible_for_role_specific_role_no_match(self, repo, mock_event):
        mock_event.visibility = [UserRole.MENTOR]
        result = repo._is_visible_for_role(mock_event, UserRole.PARTICIPANT)
        assert result is False