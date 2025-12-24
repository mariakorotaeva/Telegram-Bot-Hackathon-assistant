import pytest
import asyncio
from unittest.mock import AsyncMock, patch

import bot.main as main

@pytest.mark.asyncio
async def test_on_startup():
    with patch("bot.main.initialize_assistant", new=AsyncMock(return_value=True)):
        await main.on_startup()

@pytest.mark.asyncio
async def test_on_shutdown():
    await main.on_shutdown()

@pytest.mark.asyncio
async def test_main_startup(monkeypatch):
    monkeypatch.setattr(main, "Bot", lambda *a, **k: None)
    monkeypatch.setattr(main.dp, "start_polling", AsyncMock())
    monkeypatch.setattr(main, "schedule_reminder_checker", AsyncMock())

    await asyncio.wait_for(main.main(), timeout=0.1)