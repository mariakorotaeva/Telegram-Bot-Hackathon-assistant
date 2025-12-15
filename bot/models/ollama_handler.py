"""
Обработчик для работы с Ollama
"""
import os
import asyncio
import aiohttp
import json
import logging
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaHandler:
    """Обработчик запросов к Ollama"""
    
    def __init__(self):
        self.model_name = os.getenv('OLLAMA_MODEL', 'hackathon-assistant:latest')
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.timeout = int(os.getenv('RESPONSE_TIMEOUT', 30))
        
        # Кэш для частых вопросов
        self._response_cache = {}
        
        # Флаг загруженной модели
        self._model_loaded = False
        
        # Флаг прогрева модели
        self._warmup_task = None
        
        logger.info(f"OllamaHandler инициализирован: {self.model_name}")
    
    async def initialize(self):
        """Инициализация - вызывается после создания event loop"""
        await self._warmup_model()
    
    async def _warmup_model(self):
        """Прогрев модели - загружаем ее в память Ollama при старте"""
        try:
            logger.info(f"🔥 Прогрев модели {self.model_name}...")
            
            # Сначала проверяем подключение
            if not await self.test_connection():
                logger.warning("⚠️ Ollama недоступен, пропускаем прогрев")
                return
            
            # Используем очень короткий промпт для прогрева
            warmup_prompt = "hello"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": warmup_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 5,  # Всего 1 токен для прогрева
                            "num_thread": 4,
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        self._model_loaded = True
                        logger.info(f"✅ Модель {self.model_name} прогрета и готова")
                    else:
                        error_text = await response.text()
                        logger.warning(f"⚠️ Модель не прогрета, статус: {response.status}, ошибка: {error_text[:100]}")
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Таймаут при прогреве модели")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка прогрева модели: {e}")
    
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
            # Формируем промпт
            prompt = self._build_prompt(question, user_context)
            
            logger.info(f"📤 Отправка запроса к {self.model_name}: '{question[:50]}...'")
            
            # Оптимальные настройки для CPU в Codespace
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 100,
                            "num_thread": 4,
                            "top_k": 20,
                            "top_p": 0.9,
                            "repeat_penalty": 1.1,
                            "seed": 42
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=350)
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
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        # Кэшируем частые вопросы
                        if self._should_cache(question):
                            self._response_cache[cache_key] = result
                            logger.info(f"💾 Ответ закэширован")
                        
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка API: {response.status} - {error_text[:100]}")
                        raise Exception(f"API error {response.status}")
                        
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
                'answer': f"⚠️ Ошибка подключения к Ollama. Убедитесь что Ollama запущен.",
                'error': str(e),
                'response_time': f"{elapsed:.2f}с"
            }
    
    def _get_cache_key(self, question: str) -> str:
        """Создание ключа для кэша"""
        normalized = question.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _should_cache(self, question: str) -> bool:
        """Определяем, стоит ли кэшировать вопрос"""
        question_lower = question.lower()
        
        cache_keywords = [
            'когда', 'где', 'сколько', 'как', 'темы', 
            'призы', 'команды', 'начало', 'расписание',
            'хакатон', 'что такое', 'можно ли', 'требования'
        ]
        
        return any(keyword in question_lower for keyword in cache_keywords)
    
    def _build_prompt(self, question: str, user_context: Optional[Dict] = None) -> str:
        """Формирование промпта"""
        prompt = f"""Ты - ассистент хакатона. Отвечай кратко и информативно, 1-3 предложения.

Вопрос: {question}

Ответ:"""
        
        return prompt
    
    async def test_connection(self) -> bool:
        """Проверить подключение к Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.host}/api/tags", 
                    timeout=5
                ) as response:
                    if response.status == 200:
                        return True
                    return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Ollama: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Получить информацию о модели"""
        return {
            'name': self.model_name,
            'loaded': self._model_loaded,
            'cache_size': len(self._response_cache)
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