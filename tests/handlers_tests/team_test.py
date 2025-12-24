# tests/test_team_handlers.py
import asyncio
import types
from types import SimpleNamespace
import pytest

# импортируем тестируемый модуль
from bot.handlers import team as team_module

# ---- Вспомогательные заглушки (используются во многих тестах) ----
class DummyMessage:
    def __init__(self, user_id=1, text=""):
        self.from_user = SimpleNamespace(id=user_id)
        self.text = text
        self.edited_text = None
        self.answer_calls = []
    async def edit_text(self, text, reply_markup=None, parse_mode=None):
        self.edited_text = (text, reply_markup, parse_mode)
        return None
    async def answer(self, text, reply_markup=None, parse_mode=None, show_alert=False):
        # сохраняем все аргументы, чтобы можно было проверять сообщения и reply_markup
        self.answer_calls.append({
            "text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
            "show_alert": show_alert
        })
        return None

class DummyCallback:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = DummyMessage(user_id=user_id)
        self.answer_calls = []
    async def answer(self, text=None, show_alert=False):
        self.answer_calls.append({"text": text, "show_alert": show_alert})
        return None

class DummyState:
    def __init__(self):
        self.state_set = None
        self.data = {}
        self.cleared = False
    async def set_state(self, st):
        self.state_set = st
    async def clear(self):
        self.cleared = True
    async def update_data(self, **kwargs):
        self.data.update(kwargs)
    async def get_data(self):
        return dict(self.data)

# ---- Тесты ----

def test_back_keyboards_and_menu_builder_basic():
    # простая проверка, что функции-клавиатуры возвращают объект с атрибутом inline_keyboard
    kb1 = team_module.back_to_team_menu_keyboard()
    kb2 = team_module.back_to_main_menu_keyboard()
    assert hasattr(kb1, "inline_keyboard")
    assert hasattr(kb2, "inline_keyboard")

    # get_team_main_menu: без команды
    mk_no_team = team_module.get_team_main_menu(is_captain=False, has_team=False)
    assert hasattr(mk_no_team, "inline_keyboard")
    # с командой и капитаном
    mk_captain = team_module.get_team_main_menu(is_captain=True, has_team=True)
    assert hasattr(mk_captain, "inline_keyboard")
    # с командой, но не капитан
    mk_member = team_module.get_team_main_menu(is_captain=False, has_team=True)
    assert hasattr(mk_member, "inline_keyboard")

@pytest.mark.asyncio
async def test_team_search_main_user_not_registered(monkeypatch):
    # имитируем незарегистрированного пользователя
    async def fake_get_by_tg_id(_):
        return None
    monkeypatch.setattr(team_module, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get_by_tg_id))

    callback = DummyCallback(data="participant_team_search", user_id=42)
    await team_module.team_search_main(callback)
    # ожидаем, что callback.answer был вызван с текстом об регистрации
    assert callback.answer_calls
    assert "зарегистрируйтесь" in (callback.answer_calls[0]["text"] or "")


@pytest.mark.asyncio
async def test_team_member_add_process_name_user_not_found(monkeypatch):
    # UserService.get_by_tg_id -> some user, get_by_tg_username -> None
    async def fake_get_by_tg_id(_):
        return SimpleNamespace(id=1, team_id=10)
    async def fake_get_by_tg_username(name):
        return None

    monkeypatch.setattr(team_module, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get_by_tg_id, get_by_tg_username=fake_get_by_tg_username))
    # TeamService methods не нужны в этом сценарии
    message = DummyMessage(user_id=1, text="not_exists")
    state = DummyState()

    await team_module.team_member_add_process_name(message, state)
    # ожидаем сообщение о том, что пользователь не найден
    assert message.answer_calls
    assert "не найден" in message.answer_calls[0]["text"]

@pytest.mark.asyncio
async def test_team_member_add_process_name_already_in_team(monkeypatch):
    # UserService возвращает и user_to_add
    async def fake_get_by_tg_id(_):
        return SimpleNamespace(id=1, team_id=10)
    async def fake_get_by_tg_username(name):
        return SimpleNamespace(id=5, username=name)

    async def fake_is_user_in_team(uid):
        return True

    async def fake_join_team(uid, team_id):
        return (False, "should not be called")

    monkeypatch.setattr(team_module, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get_by_tg_id, get_by_tg_username=fake_get_by_tg_username))
    # TeamService used via TeamService().is_user_in_team and .join_team
    monkeypatch.setattr(team_module, "TeamService", lambda: SimpleNamespace(is_user_in_team=fake_is_user_in_team, join_team=fake_join_team))

    message = DummyMessage(user_id=1, text="already")
    state = DummyState()
    await team_module.team_member_add_process_name(message, state)
    assert message.answer_calls
    assert "уже состоит в команде" in message.answer_calls[0]["text"]

@pytest.mark.asyncio
async def test_team_member_add_process_name_success(monkeypatch):
    async def fake_get_by_tg_id(_):
        return SimpleNamespace(id=1, team_id=10)
    async def fake_get_by_tg_username(name):
        return SimpleNamespace(id=5, username=name)

    async def fake_is_user_in_team(uid):
        return False

    async def fake_join_team(uid, team_id):
        return (True, "ok")

    monkeypatch.setattr(team_module, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get_by_tg_id, get_by_tg_username=fake_get_by_tg_username))
    monkeypatch.setattr(team_module, "TeamService", lambda: SimpleNamespace(is_user_in_team=fake_is_user_in_team, join_team=fake_join_team))

    message = DummyMessage(user_id=1, text="newuser")
    state = DummyState()
    await team_module.team_member_add_process_name(message, state)
    assert message.answer_calls
    assert "успешно добавлен" in message.answer_calls[0]["text"]

@pytest.mark.asyncio
async def test_team_member_delete_process_name_not_found(monkeypatch):
    async def fake_get_by_tg_id(_):
        return SimpleNamespace(id=1, team_id=10)
    async def fake_get_by_tg_username(name):
        return None

    monkeypatch.setattr(team_module, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get_by_tg_id, get_by_tg_username=fake_get_by_tg_username))
    message = DummyMessage(user_id=1, text="nope")
    state = DummyState()
    await team_module.team_member_delete_process_name(message, state)
    assert message.answer_calls
    assert "не найден" in message.answer_calls[0]["text"]

@pytest.mark.asyncio
async def test_team_create_user_not_registered(monkeypatch):
    # UserService.get_by_tg_id -> None
    async def fake_get_by_tg_id(_):
        return None
    monkeypatch.setattr(team_module, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get_by_tg_id))

    callback = DummyCallback(data="team_create", user_id=99)
    state = DummyState()
    # Вызов обработчика
    await team_module.team_create(callback, state)
    # Ожидаем, что callback.answer с текстом про регистрацию был вызван
    assert callback.answer_calls
    assert "зарегистрируйтесь" in (callback.answer_calls[0]["text"] or "")

@pytest.mark.asyncio
async def test_process_team_name_too_long(monkeypatch):
    async def fake_get_by_tg_id(_):
        return SimpleNamespace(id=3)
    # замена UserService
    monkeypatch.setattr(team_module, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get_by_tg_id))
    # TeamService не будет вызываться, потому что длина > 100
    message = DummyMessage(user_id=3, text="x" * 101)
    state = DummyState()
    await team_module.process_team_name(message, state)
    assert message.answer_calls
    # Проверяем, что в ответе есть подсказка о слишком длинном названии
    assert "слишком длинное" in message.answer_calls[0]["text"]

@pytest.mark.asyncio
async def test_process_team_name_create_success(monkeypatch):
    async def fake_get_by_tg_id(_):
        return SimpleNamespace(id=7)
    # TeamService.create_team -> (True, team, message_text)
    async def fake_create_team(user_id, name):
        return (True, SimpleNamespace(id=1, name=name), "created")
    monkeypatch.setattr(team_module, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get_by_tg_id))
    monkeypatch.setattr(team_module, "TeamService", lambda: SimpleNamespace(create_team=fake_create_team))

    message = DummyMessage(user_id=7, text="MyTeam")
    state = DummyState()
    await team_module.process_team_name(message, state)
    # Ожидаем как минимум одно сообщение-ответ о создании
    assert message.answer_calls
    # Первое сообщение должно содержать "Команда создана" или "✅"
    texts = [c["text"] for c in message.answer_calls if c["text"]]
    assert any("Команда создана" in t or "✅" in t for t in texts)

