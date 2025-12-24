import pytest
from unittest.mock import AsyncMock, Mock, patch
from services.notification_service import NotificationService, NotificationType


@pytest.fixture
def mock_notification_repository():
    return AsyncMock()


@pytest.fixture
def notification_service(mock_notification_repository):
    with patch('services.notification_service.NotificationSettingsRepository',
               return_value=mock_notification_repository):
        return NotificationService()


class TestGetOrCreateSettings:
    @pytest.mark.asyncio
    async def test_get_or_create_settings_success(self, notification_service, mock_notification_repository):
        mock_settings = Mock()
        mock_notification_repository.get_or_create_settings.return_value = mock_settings

        result = await notification_service.get_or_create_settings(123)

        assert result == mock_settings
        mock_notification_repository.get_or_create_settings.assert_called_once_with(123)


class TestToggleEnabled:
    @pytest.mark.asyncio
    async def test_toggle_enabled_success(self, notification_service, mock_notification_repository):
        mock_settings = Mock()
        mock_notification_repository.toggle_enabled.return_value = mock_settings

        result = await notification_service.toggle_enabled(123)

        assert result == mock_settings
        mock_notification_repository.toggle_enabled.assert_called_once_with(123)


class TestUpdateReminderTimes:
    @pytest.mark.asyncio
    async def test_update_reminder_times_success(self, notification_service, mock_notification_repository):
        mock_settings = Mock()
        reminder_minutes = [15, 30, 60]
        mock_notification_repository.update_reminder_times.return_value = mock_settings

        result = await notification_service.update_reminder_times(123, reminder_minutes)

        assert result == mock_settings
        mock_notification_repository.update_reminder_times.assert_called_once_with(123, reminder_minutes)


class TestToggleNewEvents:
    @pytest.mark.asyncio
    async def test_toggle_new_events_success(self, notification_service, mock_notification_repository):
        mock_settings = Mock()
        mock_notification_repository.toggle_new_events.return_value = mock_settings

        result = await notification_service.toggle_new_events(123)

        assert result == mock_settings
        mock_notification_repository.toggle_new_events.assert_called_once_with(123)


class TestToggleEventUpdates:
    @pytest.mark.asyncio
    async def test_toggle_event_updates_success(self, notification_service, mock_notification_repository):
        mock_settings = Mock()
        mock_notification_repository.toggle_event_updates.return_value = mock_settings

        result = await notification_service.toggle_event_updates(123)

        assert result == mock_settings
        mock_notification_repository.toggle_event_updates.assert_called_once_with(123)


class TestToggleEventCancelled:
    @pytest.mark.asyncio
    async def test_toggle_event_cancelled_success(self, notification_service, mock_notification_repository):
        mock_settings = Mock()
        mock_notification_repository.toggle_event_cancelled.return_value = mock_settings

        result = await notification_service.toggle_event_cancelled(123)

        assert result == mock_settings
        mock_notification_repository.toggle_event_cancelled.assert_called_once_with(123)


class TestShouldSendNotification:
    @pytest.mark.asyncio
    async def test_should_send_notification_true(self, notification_service, mock_notification_repository):
        mock_settings = Mock()
        mock_settings.is_enabled_for_type.return_value = True
        mock_notification_repository.get_or_create_settings.return_value = mock_settings

        result = await notification_service.should_send_notification(123, NotificationType.NEW_EVENT)

        assert result is True
        mock_notification_repository.get_or_create_settings.assert_called_once_with(123)
        mock_settings.is_enabled_for_type.assert_called_once_with(NotificationType.NEW_EVENT)

    @pytest.mark.asyncio
    async def test_should_send_notification_false(self, notification_service, mock_notification_repository):
        mock_settings = Mock()
        mock_settings.is_enabled_for_type.return_value = False
        mock_notification_repository.get_or_create_settings.return_value = mock_settings

        result = await notification_service.should_send_notification(123, NotificationType.NEW_EVENT)

        assert result is False


class TestAddSentReminder:
    def test_add_sent_reminder_new_user(self, notification_service):
        notification_service.add_sent_reminder(123, 456, 30)

        assert 123 in notification_service.sent_reminders
        assert "456:30" in notification_service.sent_reminders[123]

    def test_add_sent_reminder_existing_user(self, notification_service):
        notification_service.sent_reminders[123] = {"456:15"}
        notification_service.add_sent_reminder(123, 456, 30)

        assert "456:15" in notification_service.sent_reminders[123]
        assert "456:30" in notification_service.sent_reminders[123]


class TestIsReminderSent:
    def test_is_reminder_sent_true(self, notification_service):
        notification_service.sent_reminders[123] = {"456:30"}

        result = notification_service.is_reminder_sent(123, 456, 30)

        assert result is True

    def test_is_reminder_sent_false_no_user(self, notification_service):
        result = notification_service.is_reminder_sent(999, 456, 30)

        assert result is False

    def test_is_reminder_sent_false_no_reminder(self, notification_service):
        notification_service.sent_reminders[123] = {"456:15"}

        result = notification_service.is_reminder_sent(123, 456, 30)

        assert result is False


class TestGetUsersForNotification:
    @pytest.mark.asyncio
    async def test_get_users_for_notification_filtered(self, notification_service):
        user1 = Mock(id=123)
        user2 = Mock(id=456)
        user3 = Mock(id=789)

        with patch.object(notification_service, 'should_send_notification') as mock_should_send:
            mock_should_send.side_effect = lambda user_id, notification_type: user_id in [123, 789]

            result = await notification_service.get_users_for_notification(
                notification_type=NotificationType.NEW_EVENT,
                users=[user1, user2, user3]
            )

            assert len(result) == 2
            assert result[0].id == 123
            assert result[1].id == 789

    @pytest.mark.asyncio
    async def test_get_users_for_notification_empty(self, notification_service):
        with patch.object(notification_service, 'should_send_notification', return_value=False):
            result = await notification_service.get_users_for_notification(
                notification_type=NotificationType.NEW_EVENT,
                users=[Mock(id=123), Mock(id=456)]
            )

            assert result == []