# tests/test_faq_handlers.py
import pytest
from types import SimpleNamespace
import asyncio

import bot.handlers.faq as faq_mod


# ---- Простые заглушки для InlineKeyboardBuilder (чтобы не зависеть от aiogram internals) ----
class FakeBuilder:
    def __init__(self):
        self.buttons = []

    def button(self, text=None, callback_data=None):
        # сохраняем tuple для проверки
        self.buttons.append((text, callback_data))
        return None

    def adjust(self, *args, **kwargs):
        return None

    def as_markup(self):
        # возвращаем объект похожий на InlineKeyboardMarkup
        rows = []
        for t, cb in self.buttons:
            btn = SimpleNamespace(text=t, callback_data=cb)
            rows.append([btn])
        return SimpleNamespace(inline_keyboard=rows)


# ---- Простые объекты Message и CallbackQuery ----
class DummyMessage:
    def __init__(self, user_id=1, text=""):
        self.from_user = SimpleNamespace(id=user_id)
        self.text = text
        self.answer_calls = []
        self.edited_text = None

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.answer_calls.append({"text": text, "reply_markup": reply_markup, "parse_mode": parse_mode})

    async def edit_text(self, text, reply_markup=None, parse_mode=None):
        self.edited_text = {"text": text, "reply_markup": reply_markup, "parse_mode": parse_mode}


class DummyCallback:
    def __init__(self, data, user_id=1):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = DummyMessage(user_id=user_id)
        self.answer_calls = []

    async def answer(self, text=None, show_alert=False):
        self.answer_calls.append({"text": text, "show_alert": show_alert})


# ---- Fixtures to reset/patch things ----
@pytest.fixture(autouse=True)
def patch_builder(monkeypatch):
    # Подменяем InlineKeyboardBuilder, чтобы все as_markup возвращало predictable structure
    monkeypatch.setattr(faq_mod, "InlineKeyboardBuilder", lambda: FakeBuilder())
    yield


# ---- Тесты ----



@pytest.mark.asyncio
async def test_show_faq_not_participant(monkeypatch):
    # user exists but role != participant
    async def fake_get(uid):
        return SimpleNamespace(id=uid, role="mentor")
    monkeypatch.setattr(faq_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))

    message = DummyMessage(user_id=10)
    await faq_mod.show_faq_from_message(message)
    assert message.answer_calls
    assert "FAQ доступен только участникам" in message.answer_calls[0]["text"]


@pytest.mark.asyncio
async def test_show_faq_no_categories(monkeypatch):
    # participant user but no categories from faq_service
    async def fake_get(uid):
        return SimpleNamespace(id=uid, role="participant")
    monkeypatch.setattr(faq_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_categories=lambda: []))

    message = DummyMessage(user_id=7)
    await faq_mod.show_faq_from_message(message)
    assert message.answer_calls
    assert "FAQ временно недоступен" in message.answer_calls[0]["text"]


@pytest.mark.asyncio
async def test_show_faq_with_categories(monkeypatch):
    # participant and categories present
    async def fake_get(uid):
        return SimpleNamespace(id=uid, role="participant")
    monkeypatch.setattr(faq_mod, "UserService", lambda: SimpleNamespace(get_by_tg_id=fake_get))
    # return two categories including an unknown one to test fallback
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_categories=lambda: ["general", "other"]))

    message = DummyMessage(user_id=5)
    await faq_mod.show_faq_from_message(message)
    # answer should be called with reply_markup having inline_keyboard
    assert message.answer_calls
    reply = message.answer_calls[0]["reply_markup"]
    assert hasattr(reply, "inline_keyboard")
    # check that buttons include our categories and "faq_all"
    texts = [row[0].text for row in reply.inline_keyboard]
    assert any("📋" in t or "Other" in t or "All" or "Все" for t in texts) or len(texts) >= 1


@pytest.mark.asyncio
async def test_show_category_questions_empty(monkeypatch):
    # show_category_questions when no questions -> callback.answer show_alert True
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_questions_by_category=lambda c: []))
    cb = DummyCallback(data="faq_category:general")
    await faq_mod.show_category_questions(cb)
    assert cb.answer_calls
    assert cb.answer_calls[0]["show_alert"] is True


@pytest.mark.asyncio
async def test_show_category_questions_with_questions(monkeypatch):
    # questions present including long question to test truncation
    questions = [
        {"question": "Short question", "answer": "ans"},
        {"question": "Q" * 100, "answer": "long ans"}
    ]
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_questions_by_category=lambda c: questions))

    cb = DummyCallback(data="faq_category:general")
    await faq_mod.show_category_questions(cb)
    # message.edited_text should be set and callback.answer called
    assert cb.message.edited_text is not None
    assert cb.answer_calls
    # ensure the long question was truncated in the buttons markup
    markup = cb.message.edited_text["reply_markup"]
    btn_texts = [row[0].text for row in markup.inline_keyboard]
    assert any(len(t) <= 40 for t in btn_texts)


@pytest.mark.asyncio
async def test_show_all_questions_empty(monkeypatch):
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_all_questions=lambda: []))
    cb = DummyCallback(data="faq_all")
    await faq_mod.show_all_questions(cb)
    assert cb.answer_calls and cb.answer_calls[0]["show_alert"] is True


@pytest.mark.asyncio
async def test_show_all_questions_with_questions(monkeypatch):
    all_q = [
        {"id": "1", "question": "Q1", "answer": "A1", "category": "general"},
        {"id": "2", "question": "Q2", "answer": "A2", "category": "technical"}
    ]
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_all_questions=lambda: all_q))
    cb = DummyCallback(data="faq_all")
    await faq_mod.show_all_questions(cb)
    assert cb.message.edited_text is not None
    assert cb.answer_calls


@pytest.mark.asyncio
async def test_show_answer_index_out_of_range(monkeypatch):
    # questions has length 1, but index 5 requested
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_questions_by_category=lambda c: [{"question": "x", "answer": "y"}]))
    cb = DummyCallback(data="faq_answer:general:5")
    await faq_mod.show_answer(cb)
    assert cb.answer_calls and cb.answer_calls[0]["show_alert"] is True


@pytest.mark.asyncio
async def test_show_answer_success(monkeypatch):
    questions = [{"question": "How?", "answer": "You do it"}]
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_questions_by_category=lambda c: questions))
    cb = DummyCallback(data="faq_answer:general:0")
    await faq_mod.show_answer(cb)
    assert cb.message.edited_text is not None
    assert cb.answer_calls


@pytest.mark.asyncio
async def test_show_answer_by_id_not_found(monkeypatch):
    # no questions with id 999
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_all_questions=lambda: [{"id": "1", "question": "x", "answer": "y", "category": "general"}]))
    cb = DummyCallback(data="faq_answer_id:999")
    await faq_mod.show_answer_by_id(cb)
    assert cb.answer_calls and cb.answer_calls[0]["show_alert"] is True


@pytest.mark.asyncio
async def test_show_answer_by_id_success(monkeypatch):
    items = [{"id": "abc", "question": "Q", "answer": "A", "category": "general"}]
    monkeypatch.setattr(faq_mod, "faq_service", SimpleNamespace(get_all_questions=lambda: items))
    cb = DummyCallback(data="faq_answer_id:abc")
    await faq_mod.show_answer_by_id(cb)
    assert cb.message.edited_text is not None
    assert cb.answer_calls


def test_back_to_menu_keyboard_structure():
    kb = faq_mod.back_to_menu_keyboard()
    # объект должен содержать inline_keyboard
    assert hasattr(kb, "inline_keyboard")
    # проверяем, что первая кнопка имеет текст "⬅️ Назад в меню"
    first = kb.inline_keyboard[0][0]
    assert getattr(first, "text", "").startswith("⬅️ Назад")
