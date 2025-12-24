
import asyncio
import importlib
from types import SimpleNamespace
import pytest

pytest_plugins = ()

form = importlib.import_module("bot.handlers.form")

# мок сообщений
class MockMessage:
    def __init__(self):
        self.last_edited_text = None
        self.last_answer_text = None
        self.reply_markup = None
        self.from_user = SimpleNamespace(id=12345)

    async def edit_text(self, text, reply_markup=None, parse_mode=None):
        self.last_edited_text = text
        self.reply_markup = reply_markup

    async def answer(self, text=None, reply_markup=None):
        self.last_answer_text = text
        self.reply_markup = reply_markup

class FakeCallbackQuery:
    def __init__(self):
        self.message = MockMessage()
        self.from_user = SimpleNamespace(id=12345)
        self.answered = False
        self.answer_args = None

    async def answer(self, *args, **kwargs):
        # Сохраняем аргументы для проверок
        self.answered = True
        self.answer_args = (args, kwargs)

class FakeFSMContext:
    def __init__(self):
        self.state_set = None
        self._data = {}
        self.cleared = False

    async def set_state(self, state):
        self.state_set = state

    async def get_data(self):
        return self._data

    async def clear(self):
        self.cleared = True

# Простые фейковые сервисы
class FakeUser:
    def __init__(self, id=1, profile_text=None, username=None, full_name="Имя Фамилия", profile_active=False):
        self.id = id
        self.profile_text = profile_text
        self.username = username
        self.full_name = full_name
        self.profile_active = profile_active

class FakeUserService:
    def __init__(self):
        self.users = {}
        self.updated_profile = None
        self.active_calls = []
        self.random_profiles = []

    async def get_by_tg_id(self, tg_id):
        return self.users.get(tg_id)

    async def get_random_active_profiles(self, limit=5, exclude_user_id=None):
        # возвращаем заранее подготовленный список
        return self.random_profiles

    async def set_profile_active(self, user_id, active):
        self.active_calls.append((user_id, active))
        return True

    async def update_user_profile(self, user_id, text):
        self.updated_profile = (user_id, text)
        return True

class FakeTeamService:
    def __init__(self, in_team=False):
        self.in_team = in_team

    async def is_user_in_team(self, user_id):
        return self.in_team

# Фикстуры
@pytest.fixture
def fake_user_service():
    return FakeUserService()

@pytest.fixture
def fake_team_service():
    return FakeTeamService(in_team=False)

@pytest.fixture
def patch_services(monkeypatch, fake_user_service, fake_team_service):
    # Заменим классы в модуле на фабрики, возвращающие наши фейковые инстансы
    monkeypatch.setattr(form, 'UserService', lambda *args, **kwargs: fake_user_service)
    monkeypatch.setattr(form, 'TeamService', lambda *args, **kwargs: fake_team_service)
    return fake_user_service, fake_team_service


@pytest.mark.asyncio
async def test_my_profile_with_team(patch_services):
    fake_user_service, fake_team_service = patch_services

    user = FakeUser(id=1, profile_text="Привет, я", username="me", full_name="Me")
    fake_user_service.users[12345] = user
    fake_team_service.in_team = True

    callback = FakeCallbackQuery()

    await form.my_profile(callback)

    text = callback.message.last_edited_text
    assert text is not None
    assert "вы состоите в команде" in text or "Неактивна (вы состоите в команде)" in text

@pytest.mark.asyncio
async def test_toggle_profile_active_blocked_if_in_team(patch_services):
    fake_user_service, fake_team_service = patch_services
    user = FakeUser(id=1, profile_text="x")
    fake_user_service.users[12345] = user
    fake_team_service.in_team = True

    callback = FakeCallbackQuery()

    await form.toggle_profile_active(callback)


    assert callback.answered
    args, kwargs = callback.answer_args
    assert kwargs.get('show_alert') is True

@pytest.mark.asyncio
async def test_edit_profile_start_sets_state(patch_services):
    fake_user_service, _ = patch_services
    user = FakeUser(id=1, profile_text="Старый текст")
    fake_user_service.users[12345] = user

    callback = FakeCallbackQuery()
    fake_state = FakeFSMContext()

    await form.edit_profile_start(callback, fake_state)

    assert fake_state.state_set == form.FormCreationState.waiting_for_text
    assert callback.message.last_edited_text is not None
    assert "Редактирование анкеты" in callback.message.last_edited_text or "Создание анкеты" in callback.message.last_edited_text

@pytest.mark.asyncio
async def test_process_profile_text_success(patch_services):
    fake_user_service, _ = patch_services
    user = FakeUser(id=1, profile_text=None)
    fake_user_service.users[12345] = user

    class IncomingMessage(MockMessage):
        def __init__(self):
            super().__init__()
            self.text = "Это мой новый профиль"
            self.from_user = SimpleNamespace(id=12345)

    incoming = IncomingMessage()
    fake_state = FakeFSMContext()

    await form.process_profile_text(incoming, fake_state)

    assert fake_user_service.updated_profile == (user.id, "Это мой новый профиль")
    assert incoming.last_answer_text is not None
    assert "Анкета сохранена" in incoming.last_answer_text
    assert fake_state.cleared is True
    assert fake_user_service.active_calls[-1] == (user.id, False)
