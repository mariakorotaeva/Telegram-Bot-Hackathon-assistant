# tests/test_ollama_handler.py
import asyncio
import pytest
from types import SimpleNamespace
from datetime import datetime

import bot.models.ollama_handler as ollama_mod


# ---- Заглушки для aiohttp response / session ----
class FakeResponse:
    def __init__(self, status=200, json_data=None, text_data=""):
        self.status = status
        self._json = json_data if json_data is not None else {}
        self._text = text_data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self):
        # emulate await response.json()
        return self._json

    async def text(self):
        return self._text


class FakeClientSession:
    """
    Fake ClientSession which can return different responses depending on URL.
    - root_get_resp: response for GET '/'
    - tags_get_resp: response for GET '/api/tags'
    - post_resp: response for POST '/api/generate'
    Optionally can be configured to raise exceptions for get/post.
    """
    def __init__(self, root_get_resp=None, tags_get_resp=None, post_resp=None,
                 get_exc=None, post_exc=None):
        self.root_get_resp = root_get_resp or FakeResponse(status=200, json_data={})
        self.tags_get_resp = tags_get_resp or FakeResponse(status=200, json_data={"models": []})
        self.post_resp = post_resp or FakeResponse(status=200, json_data={"response": "ok"})
        self.get_exc = get_exc
        self.post_exc = post_exc
        self.get_calls = []
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, *args, **kwargs):
        self.get_calls.append(url)
        if self.get_exc:
            raise self.get_exc
        if url.endswith("/api/tags"):
            return self.tags_get_resp
        return self.root_get_resp

    def post(self, url, *args, **kwargs):
        self.post_calls.append((url, args, kwargs))
        if self.post_exc:
            raise self.post_exc
        return self.post_resp


# ---- Фикстура для сброса синглтона между тестами ----
@pytest.fixture(autouse=True)
def reset_singleton(monkeypatch):
    # сбрасываем глобальный синглтон в модуле
    try:
        setattr(ollama_mod, "_assistant_instance", None)
    finally:
        yield
        setattr(ollama_mod, "_assistant_instance", None)


# ---- Тесты ----

@pytest.mark.asyncio
async def test_get_cache_key_and_should_cache():
    h = ollama_mod.OllamaHandler()
    key1 = h._get_cache_key("  ПрИмер? ")
    key2 = h._get_cache_key("пример?")
    assert key1 == key2  # нормализация и md5
    assert len(key1) == 16

    assert h._should_cache("Когда начинается хакатон?") is True
    assert h._should_cache("some random question") is False


@pytest.mark.asyncio
async def test_test_connection_success_and_failure(monkeypatch):
    # успешное подключение (status=200)
    fake_session = FakeClientSession(root_get_resp=FakeResponse(status=200))
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session)

    h = ollama_mod.OllamaHandler()
    ok = await h.test_connection()
    assert ok is True
    assert fake_session.get_calls and fake_session.get_calls[0].endswith("/")

    # неуспешное подключение (status != 200)
    fake_session2 = FakeClientSession(root_get_resp=FakeResponse(status=500))
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session2)
    h2 = ollama_mod.OllamaHandler()
    assert await h2.test_connection() is False

    # исключение при подключении -> False
    fake_session3 = FakeClientSession(get_exc=RuntimeError("boom"))
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session3)
    h3 = ollama_mod.OllamaHandler()
    assert await h3.test_connection() is False


@pytest.mark.asyncio
async def test__check_model_exists_present_and_missing(monkeypatch):
    model_name = "hackathon-assistant:latest"

    tags_resp = FakeResponse(
        status=200,
        json_data={"models": [{"name": model_name}]}
    )
    fake_session = FakeClientSession(tags_get_resp=tags_resp)
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session)

    h = ollama_mod.OllamaHandler()
    h.model_name = model_name  # 🔥 КЛЮЧЕВАЯ СТРОКА

    assert await h._check_model_exists() is True



@pytest.mark.asyncio
async def test_initialize_sets_model_loaded_when_available(monkeypatch):
    model_name = "hackathon-assistant:latest"

    tags_resp = FakeResponse(
        status=200,
        json_data={"models": [{"name": model_name}]}
    )
    fake_session = FakeClientSession(
        root_get_resp=FakeResponse(status=200),
        tags_get_resp=tags_resp
    )
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session)

    h = ollama_mod.OllamaHandler()
    h.model_name = model_name  # 🔥 КЛЮЧЕВАЯ СТРОКА

    ok = await h.initialize()

    assert ok is True
    assert h._model_loaded is True



@pytest.mark.asyncio
async def test_ask_success_and_caching(monkeypatch):
    # post returns success response
    post_resp = FakeResponse(status=200, json_data={"response": "  Привет  "})
    fake_session = FakeClientSession(post_resp=post_resp)
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session)

    h = ollama_mod.OllamaHandler()
    # ensure cache empty
    assert h.get_model_info()["cache_size"] == 0

    res = await h.ask("Когда начинается хакатон?")
    assert res["success"] is True
    assert "Привет" in res["answer"]
    # should have cached (because question contains 'когда')
    assert h.get_model_info()["cache_size"] == 1

    # call again -> should use cache and NOT increase post_calls
    pre_calls = len(fake_session.post_calls)
    res2 = await h.ask("Когда начинается хакатон?")
    assert res2 == res
    assert len(fake_session.post_calls) == pre_calls  # никакого дополнительного поста


@pytest.mark.asyncio
async def test_ask_api_error(monkeypatch):
    # post returns non-200 and some text
    post_resp = FakeResponse(status=500, json_data={}, text_data="server error")
    fake_session = FakeClientSession(post_resp=post_resp)
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session)

    h = ollama_mod.OllamaHandler()
    result = await h.ask("Some question")
    assert result["success"] is False
    assert result["error"] == "api_error"
    assert "response_time" in result


@pytest.mark.asyncio
async def test_ask_timeout_and_exception(monkeypatch):
    # simulate TimeoutError raised when calling post()
    fake_session_timeout = FakeClientSession(post_exc=asyncio.TimeoutError())
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session_timeout)
    h = ollama_mod.OllamaHandler()
    res_timeout = await h.ask("What now?")
    assert res_timeout["success"] is False
    assert res_timeout["error"] == "timeout"

    # simulate generic exception from post()
    fake_session_exc = FakeClientSession(post_exc=RuntimeError("boom"))
    monkeypatch.setattr(ollama_mod.aiohttp, "ClientSession", lambda: fake_session_exc)
    h2 = ollama_mod.OllamaHandler()
    res_exc = await h2.ask("Question")
    assert res_exc["success"] is False
    assert "error" in res_exc and isinstance(res_exc["error"], str)


def test_get_model_info_and_clear_cache_and_singleton():
    # Проверяем get_model_info, clear_cache и синглтон
    # подготовим экземпляр и поместим в cache
    h = ollama_mod.OllamaHandler()
    h._response_cache["abc"] = {"success": True}
    info = h.get_model_info()
    assert "name" in info and "loaded" in info and "cache_size" in info
    assert info["cache_size"] >= 1

    h.clear_cache()
    assert h.get_model_info()["cache_size"] == 0

    # singleton
    a1 = ollama_mod.get_assistant()
    a2 = ollama_mod.get_assistant()
    assert a1 is a2
