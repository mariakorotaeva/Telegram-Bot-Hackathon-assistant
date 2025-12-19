"""
Обработчик для работы с Ollama
"""
import os
import asyncio
import aiohttp
import logging
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

# Настройка логгера
logger = logging.getLogger(__name__)

class OllamaHandler:
    """Обработчик запросов к Ollama"""
    
    def __init__(self):
        self.model_name = os.getenv('OLLAMA_MODEL', 'hackathon-assistant:latest')
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.timeout = int(os.getenv('RESPONSE_TIMEOUT', 350))
        
        # Кэш для частых вопросов
        self._response_cache = {}
        
        # Флаг загруженной модели
        self._model_loaded = False
        
        logger.info(f"🤖 OllamaHandler инициализирован для модели: {self.model_name}")
    
    async def initialize(self):
        """Инициализация - проверяем доступность модели"""
        try:
            logger.info(f"🔍 Проверка доступности модели {self.model_name}...")
            
            # Сначала проверяем подключение к Ollama
            if not await self.test_connection():
                logger.error("❌ Ollama недоступен! Проверьте, запущен ли ollama serve")
                return False
            
            # Проверяем, что модель доступна
            model_exists = await self._check_model_exists()
            
            if model_exists:
                logger.info(f"✅ Модель {self.model_name} доступна")
                self._model_loaded = True
                return True
            else:
                logger.error(f"❌ Модель {self.model_name} не найдена в Ollama!")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            return False
    
    async def _check_model_exists(self) -> bool:
        """Проверяем, существует ли модель в Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.host}/api/tags", 
                    timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get('models', [])
                        
                        for model in models:
                            if model.get('name') == self.model_name:
                                return True
                        return False
                    return False
        except Exception as e:
            logger.error(f"❌ Ошибка проверки моделей: {e}")
            return False
    
    async def ask(self, question: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Задать вопрос модели"""
        start_time = datetime.now()
        
        # Проверяем кэш для частых вопросов
        cache_key = self._get_cache_key(question)
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            logger.info(f"🔄 Используем кэшированный ответ")
            return cached
        
        try:
            logger.info(f"📤 Отправка запроса: '{question[:50]}...'")
            
            # Отправляем чистый вопрос модели
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": question,  # Только вопрос пользователя
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 200,
                            "num_thread": 4,
                            "top_k": 40,
                            "top_p": 0.9,
                            "repeat_penalty": 1.1,
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    if response.status == 200:
                        data = await response.json()
                        answer = data.get('response', '').strip()
                        
                        logger.info(f"✅ Ответ получен за {elapsed:.2f}с")
                        
                        result = {
                            'success': True,
                            'answer': answer,
                            'model': self.model_name,
                            'response_time': f"{elapsed:.2f}с",
                            'timestamp': datetime.now().isoformat(),
                        }
                        
                        # Кэшируем частые вопросы
                        if self._should_cache(question):
                            self._response_cache[cache_key] = result
                        
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка API: {response.status}")
                        return {
                            'success': False,
                            'answer': f"Ошибка сервера",
                            'error': 'api_error',
                            'response_time': f"{elapsed:.2f}с"
                        }
                        
        except asyncio.TimeoutError:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"⏰ Таймаут через {elapsed:.2f}с")
            return {
                'success': False,
                'answer': "⏰ Извините, обработка заняла слишком много времени.",
                'error': 'timeout',
                'response_time': f"{elapsed:.2f}с"
            }
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Ошибка: {e}")
            return {
                'success': False,
                'answer': "⚠️ Ошибка подключения к AI.",
                'error': str(e),
                'response_time': f"{elapsed:.2f}с"
            }
    
    def _get_cache_key(self, question: str) -> str:
        """Создание ключа для кэша"""
        normalized = question.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def _should_cache(self, question: str) -> bool:
        """Определяем, стоит ли кэшировать вопрос"""
        question_lower = question.lower()
        
        cache_keywords = [
            'когда', 'где', 'сколько', 'как', 'темы', 
            'призы', 'команды', 'начало', 'расписание',
            'хакатон', 'что такое', 'можно ли', 'требования',
            'длится', 'время', 'участие', 'регистрация',
            'стоит', 'цена', 'бесплатно', 'принять участие',
            'место', 'адрес', 'формат', 'организатор'
        ]
        
        return any(keyword in question_lower for keyword in cache_keywords)
    
    async def test_connection(self) -> bool:
        """Проверить подключение к Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.host}/", 
                    timeout=3
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Не удалось подключиться к Ollama")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Получить базовую информацию о модели"""
        return {
            'name': self.model_name,
            'loaded': self._model_loaded,
            'cache_size': len(self._response_cache),
        }
    
    def clear_cache(self):
        """Очистить кэш"""
        self._response_cache.clear()
        logger.info("🗑️ Кэш очищен")


# Синглтон
_assistant_instance = None

def get_assistant() -> OllamaHandler:
    """Получить экземпляр обработчика"""
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = OllamaHandler()
    return _assistant_instance