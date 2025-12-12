import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    # Телеграм
    TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
    
    # Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "hackathon-assistant")  # ← Кастомная модель
    
    # База знаний
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./knowledge_base/faq.json")
    KNOWLEDGE_BASE_DIR = Path("./knowledge_base")
    ENABLE_KNOWLEDGE_BASE = os.getenv("ENABLE_KNOWLEDGE_BASE", "true").lower() == "true"
    
    # Настройки
    ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",") if os.getenv("ADMIN_IDS") else []
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Валидация
    @classmethod
    def validate(cls):
        errors = []
        if not cls.TELEGRAM_TOKEN:
            errors.append("TELEGRAM_BOT_TOKEN не установлен")
        return errors