"""
Обработчик для работы с Ollama
"""
import os
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaHandler:
    """Обработчик запросов к Ollama"""
    
    def __init__(self):
        self.model_name = os.getenv('OLLAMA_MODEL', 'hackathon-assistant:latest')
        self.host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        self.timeout = int(os.getenv('RESPONSE_TIMEOUT', 60))  # Увеличили таймаут
        logger.info(f"OllamaHandler инициализирован: {self.model_name}")
    
    async def ask(self, question: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Задать вопрос модели"""
        start_time = datetime.now()
        
        try:
            # Формируем промпт
            prompt = self._build_prompt(question, user_context)
            
            # УВЕЛИЧЕННЫЙ ТАЙМАУТ - 60 секунд
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 200,  # Меньше токенов для скорости
                            "num_thread": 4,     # Больше потоков
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=350)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        answer = data.get('response', '').strip()
                        
                        elapsed = (datetime.now() - start_time).total_seconds()
                        
                        return {
                            'success': True,
                            'answer': answer,
                            'model': self.model_name,
                            'response_time': f"{elapsed:.2f}с",
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text}")
                        
        except asyncio.TimeoutError:
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                'success': False,
                'answer': "⏰ Извините, обработка заняла слишком много времени.",
                'error': 'timeout',
                'response_time': f"{elapsed:.2f}с"
            }
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            return {
                'success': False,
                'answer': f"⚠️ Ошибка: {str(e)[:100]}",
                'error': str(e),
                'response_time': f"{elapsed:.2f}с"
            }
    
    def _build_prompt(self, question: str, user_context: Optional[Dict] = None) -> str:
        """Формирование промпта"""
        prompt = f"""Ты - ассистент хакатона. Отвечай кратко и информативно.

Вопрос: {question}
"""
        if user_context:
            prompt += f"\nКонтекст: {json.dumps(user_context)}\n"
        
        prompt += "\nОтвет:"
        return prompt
    
    async def test_connection(self) -> bool:
        """Проверить подключение к Ollama"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.host}/api/tags", timeout=5) as response:
                    return response.status == 200
        except:
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Получить информацию о модели"""
        return {
            'name': self.model_name,
            'size': 'N/A',
            'modified': 'N/A'
        }


# Синглтон
_assistant_instance = None

def get_assistant() -> OllamaHandler:
    """Получить экземпляр обработчика"""
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = OllamaHandler()
    return _assistant_instance

