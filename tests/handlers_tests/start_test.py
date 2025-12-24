import pytest
import asyncio
from types import SimpleNamespace

import bot.handlers.start as start_mod


# =========================
# FAKES
# =========================
class FakeMessage:
    def __init__(self, text="/start", user_id=1, username="user"):
        self.text = text
        self.from_user = SimpleNamespace(id=user_id, username=username)
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class FakeCallback:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = SimpleNamespace(edit_text=self._edit_text)
        self.answers = []

    async def _edit_text(self, text, **kwargs):
        self.answers.append(text)

    async def answer(self, text=None, **kwargs):
        if text:
            self.answers.append(text)


class FakeFSM:
    def __init__(self):
        self.state = None
        self.data = {}

    async def set_state(self, state):
        self.state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return self.data

    async def clear(self):
        self.state = None
        self.data = {}


class FakeUser:
    def __init__(self, role="participant", full_name="Test User", timezone="UTC+3", username="u"):
        self.role = role
        self.full_name = full_name
        self.timezone = timezone
        self.username = username
        self.id = 1


# =========================
# validate_name
# =========================
def test_validate_name_ok():
    ok, err = start_mod.validate_name("Иван Иванов")
    assert ok is True
    assert err is None


def test_validate_name_invalid():
    ok, err = start_mod.validate_name("12")
    assert ok is False


# =========================
# /start
# =========================
@pytest.mark.asyncio
async def test_cmd_start_existing_user(monkeypatch):
    async def fake_get(_):
        return FakeUser()

    monkeypatch.setattr(start_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))

    msg = FakeMessage()
    fsm = FakeFSM()

    await start_mod.cmd_start_handler(msg, fsm)

    assert "Ты уже зарегистрирован" in msg.answers[0]


@pytest.mark.asyncio
async def test_cmd_start_new_user(monkeypatch):
    async def fake_get(_):
        return None

    monkeypatch.setattr(start_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))

    msg = FakeMessage()
    fsm = FakeFSM()

    await start_mod.cmd_start_handler(msg, fsm)

    assert "введи свое" in msg.answers[0]
    assert fsm.state == start_mod.RegistrationStates.waiting_for_name


# =========================
# process_name
# =========================
@pytest.mark.asyncio
async def test_process_name_invalid():
    msg = FakeMessage(text="12")
    fsm = FakeFSM()

    await start_mod.process_name(msg, fsm)

    assert "❌" in msg.answers[0]


@pytest.mark.asyncio
async def test_process_name_valid():
    msg = FakeMessage(text="Иван Иванов")
    fsm = FakeFSM()

    await start_mod.process_name(msg, fsm)

    assert fsm.state == start_mod.RegistrationStates.waiting_for_role
    assert "Иван Иванов" in msg.answers[0]


# =========================
# process_role
# =========================
@pytest.mark.asyncio
async def test_process_role_invalid():
    cb = FakeCallback("role_invalid")
    fsm = FakeFSM()

    await start_mod.process_role(cb, fsm)

    assert any("❌" in a for a in cb.answers)


@pytest.mark.asyncio
async def test_process_role_valid():
    cb = FakeCallback("role_participant")
    fsm = FakeFSM()

    await start_mod.process_role(cb, fsm)

    assert fsm.state == start_mod.RegistrationStates.waiting_for_timezone


# =========================
# process_timezone
# =========================
@pytest.mark.asyncio
async def test_process_timezone_missing_data():
    cb = FakeCallback("tz_UTC+3")
    fsm = FakeFSM()

    await start_mod.process_timezone(cb, fsm)

    assert "Регистрация не удалась" in cb.answers[0]

@pytest.mark.asyncio
async def test_show_all_users_not_registered(monkeypatch):
    async def fake_get(_):
        return None

    monkeypatch.setattr(start_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))

    msg = FakeMessage(text="/users")

    await start_mod.show_all_users(msg)

    assert "Сначала зарегистрируйся" in msg.answers[0]


@pytest.mark.asyncio
async def test_show_all_users_not_organizer(monkeypatch):
    async def fake_get(_):
        return FakeUser(role="participant")

    monkeypatch.setattr(start_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))

    msg = FakeMessage(text="/users")

    await start_mod.show_all_users(msg)

    assert "Доступ запрещен" in msg.answers[0]


# =========================
# /reset
# =========================
@pytest.mark.asyncio
async def test_reset_registered(monkeypatch):
    async def fake_get(_):
        return FakeUser()

    async def fake_delete(_):
        return None

    monkeypatch.setattr(
        start_mod,
        "UserService",
        lambda: SimpleNamespace(get_by_tg_id=fake_get, delete_user=fake_delete),
    )

    msg = FakeMessage(text="/reset")
    fsm = FakeFSM()

    await start_mod.reset_registration(msg, fsm)

    assert "Регистрация сброшена" in msg.answers[0]


# =========================
# /help
# =========================
@pytest.mark.asyncio
async def test_help_for_participant(monkeypatch):
    async def fake_get(_):
        return FakeUser(role="participant")

    monkeypatch.setattr(start_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))

    msg = FakeMessage(text="/help")

    await start_mod.show_help(msg)

    assert "/users" not in msg.answers[0]


@pytest.mark.asyncio
async def test_help_for_organizer(monkeypatch):
    async def fake_get(_):
        return FakeUser(role="organizer")

    monkeypatch.setattr(start_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))

    msg = FakeMessage(text="/help")

    await start_mod.show_help(msg)

    assert "/users" in msg.answers[0]
