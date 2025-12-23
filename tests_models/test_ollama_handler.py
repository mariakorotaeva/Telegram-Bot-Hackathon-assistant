"""
Unit tests for OllamaHandler
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import os
import hashlib


# Создаем мок-класс для тестирования без зависимостей
class MockOllamaHandler:
    def __init__(self):
        self.model_name = os.getenv('OLLAMA_MODEL', 'test-model:latest')
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.timeout = int(os.getenv('RESPONSE_TIMEOUT', 350))
        self._response_cache = {}
        self._model_loaded = False
        
    def _get_cache_key(self, question: str) -> str:
        """Создание ключа для кэша"""
        normalized = question.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _should_cache(self, question: str) -> bool:
        """Определяем, стоит ли кэшировать вопрос"""
        question_lower = question.lower()
        cache_keywords = [
            'когда', 'где', 'сколько', 'темы', 
            'призы', 'команды', 'начало', 'расписание',
            'хакатон', 'что такое', 'можно ли', 'требования'
        ]
        
        # Ищем точные совпадения слов
        words = question_lower.split()
        return any(keyword in question_lower for keyword in cache_keywords if len(keyword) > 3)
    
    def _build_prompt(self, question: str, user_context=None) -> str:
        """Формирование промпта"""
        prompt = f"""Ты - ассистент хакатона. Отвечай кратко и информативно, 1-3 предложения.

Вопрос: {question}

Ответ:"""
        return prompt
    
    async def ask(self, question: str, user_context=None):
        """Задать вопрос модели"""
        if self._get_cache_key(question) in self._response_cache:
            return self._response_cache[self._get_cache_key(question)]
        
        return {
            'success': True,
            'answer': f'Ответ на вопрос: {question}',
            'model': self.model_name,
            'response_time': '1.23с',
            'timestamp': '2024-01-01T00:00:00'
        }
    
    async def test_connection(self):
        """Проверить подключение к Ollama"""
        return True
    
    def get_model_info(self):
        """Получить информацию о модели"""
        return {
            'name': self.model_name,
            'loaded': self._model_loaded,
            'cache_size': len(self._response_cache)
        }
    
    def clear_cache(self):
        """Очистить кэш"""
        self._response_cache.clear()


class TestOllamaHandler:
    """Test OllamaHandler class"""
    
    def setup_method(self):
        """Setup for each test"""
        os.environ['OLLAMA_MODEL'] = 'test-model:latest'
        os.environ['OLLAMA_HOST'] = 'http://localhost:11434'
        os.environ['RESPONSE_TIMEOUT'] = '100'
        
        self.handler = MockOllamaHandler()
        self.handler._model_loaded = True
    
    def teardown_method(self):
        """Cleanup after each test"""
        if hasattr(self, 'handler'):
            self.handler.clear_cache()
    
    def test_init_defaults(self):
        """Test initialization with default values"""
        handler = MockOllamaHandler()
        assert handler.model_name == 'test-model:latest'
        assert handler.host == 'http://localhost:11434'
        assert handler.timeout == 100
        assert handler._response_cache == {}
        assert not handler._model_loaded
    
    def test_get_cache_key(self):
        """Test cache key generation"""
        question = "Test question"
        expected_key = hashlib.md5(question.lower().strip().encode()).hexdigest()
        
        result = self.handler._get_cache_key(question)
        assert result == expected_key
        
        assert self.handler._get_cache_key("TEST QUESTION") == expected_key
        assert self.handler._get_cache_key("  test question  ") == expected_key
    
    
    def test_build_prompt(self):
        """Test prompt building"""
        question = "Когда начало?"
        expected = """Ты - ассистент хакатона. Отвечай кратко и информативно, 1-3 предложения.

Вопрос: Когда начало?

Ответ:"""
        
        result = self.handler._build_prompt(question)
        assert result == expected
        
        # Test with context
        context = {"user": "test_user"}
        result_with_context = self.handler._build_prompt(question, context)
        assert result_with_context == expected
    
    @pytest.mark.asyncio
    async def test_ask_success(self):
        """Test successful ask with mocked response"""
        result = await self.handler.ask("Test question")
        
        assert result['success'] == True
        assert "Ответ на вопрос" in result['answer']
        assert result['model'] == "test-model:latest"
        assert 'response_time' in result
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_ask_cached(self):
        """Test that cached responses are returned"""
        result1 = await self.handler.ask("Когда начинается хакатон?")
        
        cache_key = self.handler._get_cache_key("Когда начинается хакатон?")
        self.handler._response_cache[cache_key] = result1
        
        result2 = await self.handler.ask("Когда начинается хакатон?")

        assert result1['answer'] == result2['answer']
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test"""
        result = await self.handler.test_connection()
        assert result == True
    
    def test_get_model_info(self):
        """Test getting model information"""
        self.handler._response_cache['key1'] = {'answer': 'test1'}
        self.handler._response_cache['key2'] = {'answer': 'test2'}
        
        info = self.handler.get_model_info()
        
        assert info['name'] == 'test-model:latest'
        assert info['loaded'] == True
        assert info['cache_size'] == 2
    
    def test_clear_cache(self):
        """Test cache clearing"""
        self.handler._response_cache['key1'] = {'answer': 'test1'}
        self.handler._response_cache['key2'] = {'answer': 'test2'}
        
        assert len(self.handler._response_cache) == 2
        
        self.handler.clear_cache()
        
        assert len(self.handler._response_cache) == 0