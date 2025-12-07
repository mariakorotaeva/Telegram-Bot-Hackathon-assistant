import requests
import json
import logging
from typing import Dict, Any, Optional
from config import Config
from database_handler import KnowledgeBaseHandler

# Настройка логгирования
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class OllamaHackathonHandler:
    def __init__(self):
        self.base_url = Config.OLLAMA_BASE_URL
        self.model = Config.OLLAMA_MODEL
        self.knowledge_base = KnowledgeBaseHandler() if Config.ENABLE_KNOWLEDGE_BASE else None
        logger.info(f"Инициализирован обработчик для модели: {self.model}")
    
    def _call_ollama_api(self, prompt: str, context: str = None) -> str:
        """Вызывает API Ollama с промптом и контекстом"""
        url = f"{self.base_url}/api/generate"
        
        # Формируем полный промпт
        full_prompt = prompt
        
        if context and Config.ENABLE_KNOWLEDGE_BASE:
            full_prompt = f"""Контекст из базы знаний:
{context}

Вопрос участника: {prompt}

Ответь, используя информацию из контекста выше. Если в контексте нет ответа, скажи об этом."""
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 512
            }
        }
        
        try:
            logger.debug(f"Отправка запроса к модели {self.model}")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Извлекаем ответ
            if "response" in result:
                return result["response"]
            else:
                logger.error(f"Неожиданный формат ответа: {result}")
                return "Ошибка обработки ответа модели."
                
        except requests.exceptions.ConnectionError:
            error_msg = "Не могу подключиться к Ollama. Убедитесь, что 'ollama serve' запущен."
            logger.error(error_msg)
            return f"❌ {error_msg}"
        except requests.exceptions.Timeout:
            error_msg = "Таймаут запроса к модели. Попробуйте позже."
            logger.error(error_msg)
            return f"⏱️ {error_msg}"
        except Exception as e:
            error_msg = f"Произошла ошибка: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"❌ {error_msg}"
    
    def generate_response(self, user_message: str) -> str:
        """Генерирует ответ на сообщение пользователя"""
        
        # 1. Проверяем, относится ли вопрос к хакатону
        if not self._is_hackathon_related(user_message):
            return self._get_off_topic_response()
        
        # 2. Ищем в базе знаний (если включена)
        context = None
        if self.knowledge_base and Config.ENABLE_KNOWLEDGE_BASE:
            context = self.knowledge_base.search_faq(user_message)
        
        # 3. Генерируем ответ
        response = self._call_ollama_api(user_message, context)
        
        # 4. Пост-обработка
        response = self._post_process_response(response)
        
        return response
    
    def _is_hackathon_related(self, message: str) -> bool:
        """Проверяет, относится ли сообщение к хакатону"""
        hackathon_keywords = [
            'хакатон', 'хакатона', 'хакатону', 'хакатоном',
            'мероприятие', 'мероприятия',
            'регистрация', 'регистрации',
            'команда', 'команды', 'участник', 'участники',
            'расписание', 'график', 'время',
            'правила', 'требования', 'условия',
            'организатор', 'организаторы',
            'проект', 'проекты', 'задание', 'задания',
            'приз', 'призы', 'победитель', 'победители',
            'ментор', 'менторы', 'эксперт', 'эксперты',
            'техподдержка', 'помощь', 'вопрос'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in hackathon_keywords)
    
    def _get_off_topic_response(self) -> str:
        """Возвращает ответ на оффтоп-вопрос"""
        responses = [
            "Я могу отвечать только на вопросы, связанные с хакатоном. Задайте, пожалуйста, организационный вопрос.",
            "Моя специализация - помощь с вопросами о хакатоне. Пожалуйста, задайте вопрос по теме мероприятия.",
            "Этот вопрос не относится к хакатону. Я могу помочь с регистрацией, расписанием, правилами и другими организационными моментами."
        ]
        import random
        return random.choice(responses)
    
    def _post_process_response(self, response: str) -> str:
        """Пост-обработка ответа модели"""
        # Обрезаем если слишком длинный
        if len(response) > 2000:
            response = response[:2000] + "..."
        
        # Добавляем стандартное окончание
        if not response.endswith(('.', '!', '?')):
            response += "."
        
        return response.strip()
    
    def check_ollama_status(self) -> Dict[str, Any]:
        """Проверяет статус Ollama и доступность модели"""
        try:
            # Проверяем доступность сервера
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_available = any(
                    model.get("name") == self.model or 
                    model.get("name") == f"{self.model}:latest" 
                    for model in models
                )
                
                return {
                    "status": "running",
                    "model": self.model,
                    "model_available": model_available,
                    "available_models": [m.get("name") for m in models],
                    "server": self.base_url
                }
        except requests.exceptions.ConnectionError:
            return {
                "status": "not_running", 
                "model": self.model,
                "model_available": False,
                "error": "Не могу подключиться к Ollama"
            }
        except Exception as e:
            return {
                "status": "error",
                "model": self.model,
                "model_available": False,
                "error": str(e)
            }