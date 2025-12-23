"""
Pytest configuration for tests
"""
import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.storage.memory import MemoryStorage

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables"""
    old_env = os.environ.copy()
    
    os.environ['OLLAMA_MODEL'] = 'test-model:latest'
    os.environ['OLLAMA_HOST'] = 'http://localhost:11434'
    os.environ['RESPONSE_TIMEOUT'] = '10'
    
    yield
    
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def mock_ollama_handler():
    """Mock OllamaHandler for testing"""
    with patch('models.ollama_handler.get_assistant') as mock_get_assistant:
        mock_handler = AsyncMock()
        mock_handler.ask.return_value = {
            'success': True,
            'answer': 'Test answer from AI',
            'model': 'test-model',
            'response_time': '1.23с'
        }
        mock_handler.test_connection.return_value = True
        mock_handler._model_loaded = True
        mock_handler.clear_cache = MagicMock()
        mock_handler.get_model_info.return_value = {
            'name': 'test-model',
            'loaded': True,
            'cache_size': 0
        }
        mock_get_assistant.return_value = mock_handler
        yield mock_handler


@pytest.fixture
def fsm_storage():
    """FSM storage for testing"""
    return MemoryStorage()


@pytest.fixture
def state(fsm_storage):
    """FSM state for testing"""
    from aiogram.fsm.context import FSMContext
    return FSMContext(storage=fsm_storage, key='test')


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires Ollama running)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "aiogram: mark test as aiogram-related"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests by default"""
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(
            reason="need --run-integration option to run"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add command line options"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests (requires Ollama running)"
    )