import pytest
import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import bot.services.notifications as notif


# ---------- FAKES ----------
class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, user_id, text, parse_mode=None):
        self.sent.append((user_id, text))


class FakeUser:
    def __init__(self, telegram_id="1", role="participant", timezone="UTC+3"):
        self.telegram_id = telegram_id
        self.role = role
        self.timezone = timezone


@pytest.fixture(autouse=True)
def clear_storage():
    notif.notifications_storage["sent_reminders"].clear()
    yield
    notif.notifications_storage["sent_reminders"].clear()


# ---------- BASIC ----------
def test_get_default_notification_settings():
    p = notif.get_default_notification_settings("participant")
    o = notif.get_default_notification_settings("organizer")

    assert p["enabled"] is True
    assert p["new_event_enabled"] is True
    assert o["new_event_enabled"] is False


@pytest.mark.asyncio
async def test_send_notification_disabled(monkeypatch):
    bot = FakeBot()

    async def fake_settings(_):
        return {"enabled": False}

    monkeypatch.setattr(
        notif,
        "NotificationService",
        lambda: SimpleNamespace(get_or_create_settings=fake_settings),
    )

    res = await notif.send_notification(bot, "1", "T", "M")
    assert res is False
    assert bot.sent == []


@pytest.mark.asyncio
async def test_send_notification_success(monkeypatch):
    bot = FakeBot()

    async def fake_settings(_):
        return {"enabled": True}

    monkeypatch.setattr(
        notif,
        "NotificationService",
        lambda: SimpleNamespace(get_or_create_settings=fake_settings),
    )

    res = await notif.send_notification(bot, "1", "Hello", "World")
    assert res is True
    assert len(bot.sent) == 1


# ---------- REMINDERS ----------
@pytest.mark.asyncio
async def test_check_and_send_reminders(monkeypatch):
    bot = FakeBot()
    user = FakeUser()

    async def fake_users():
        return [user]

    async def fake_events(role, tz):
        return [{
            "id": "e1",
            "title": "Meet",
            "start_time": datetime.utcnow() + timedelta(minutes=5),
            "creator_timezone": "UTC+0"
        }]

    async def fake_settings(_):
        return {"enabled": True, "reminder_minutes": [5]}

    monkeypatch.setattr(notif, "UserService", lambda: SimpleNamespace(get_all=fake_users))
    monkeypatch.setattr(notif, "ScheduleService", lambda: SimpleNamespace(get_events_for_role=fake_events))
    monkeypatch.setattr(notif, "NotificationService", lambda: SimpleNamespace(get_or_create_settings=fake_settings))
    monkeypatch.setitem(notif.TIMEZONE_OFFSETS, "UTC+0", 0)

    await notif.check_and_send_reminders(bot)
    assert len(bot.sent) == 1


# ---------- EVENTS ----------
@pytest.mark.asyncio
async def test_notify_new_event(monkeypatch):
    user = FakeUser()

    async def fake_users():
        return [user]

    called = []

    async def fake_send(*args, **kwargs):
        called.append(kwargs["user_role"])
        return True

    monkeypatch.setattr(notif, "UserService", lambda: SimpleNamespace(get_all=fake_users))
    monkeypatch.setattr(notif, "send_notification", fake_send)
    monkeypatch.setattr(
        notif,
        "schedule_service",
        SimpleNamespace(_convert_time_for_user=lambda dt, *_: dt)
    )

    await notif.notify_new_event(FakeBot(), {
        "title": "Event",
        "start_time": datetime.utcnow(),
        "visibility": ["all"]
    })

    assert called == ["participant"]


@pytest.mark.asyncio
async def test_notify_event_updated(monkeypatch):
    user = FakeUser()

    async def fake_users():
        return [user]

    monkeypatch.setattr(notif, "UserService", lambda: SimpleNamespace(get_all=fake_users))
    monkeypatch.setattr(notif, "send_notification", lambda *a, **k: asyncio.sleep(0))

    await notif.notify_event_updated(
        FakeBot(),
        {
            "title": "Upd",
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow() + timedelta(hours=1),
            "visibility": ["participant"]
        },
        {"title": True}
    )


@pytest.mark.asyncio
async def test_notify_event_cancelled(monkeypatch):
    user = FakeUser()

    async def fake_users():
        return [user]

    monkeypatch.setattr(notif, "UserService", lambda: SimpleNamespace(get_all=fake_users))
    monkeypatch.setattr(notif, "send_notification", lambda *a, **k: asyncio.sleep(0))

    await notif.notify_event_cancelled(
        FakeBot(),
        {
            "title": "Cancelled",
            "start_time": datetime.utcnow(),
            "visibility": ["all"]
        }
    )
