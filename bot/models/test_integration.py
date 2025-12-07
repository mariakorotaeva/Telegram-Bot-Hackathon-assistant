"""
Тестирование интеграции хакатон-ассистента
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ollama_handler import OllamaHackathonHandler
from config import Config

def test_model():
    print("🧪 Тестирование интеграции хакатон-ассистента")
    print("=" * 50)
    
    # Проверка конфигурации
    errors = Config.validate()
    if errors:
        print("❌ Ошибки конфигурации:")
        for error in errors:
            print(f"   - {error}")
        return
    
    # Инициализация обработчика
    print("🔄 Инициализация обработчика...")
    handler = OllamaHackathonHandler()
    
    # Проверка статуса Ollama
    print("\n🔍 Проверка статуса Ollama...")
    status = handler.check_ollama_status()
    
    print(f"   Сервер: {status.get('server', 'N/A')}")
    print(f"   Статус: {status.get('status', 'unknown')}")
    print(f"   Модель: {status.get('model', 'N/A')}")
    print(f"   Доступна: {'✅' if status.get('model_available') else '❌'}")
    
    if status.get('status') != 'running' or not status.get('model_available'):
        print("\n❌ Ollama не готова!")
        print("   Запустите: ollama serve")
        print("   Убедитесь, что модель создана: ollama create hackathon-assistant -f Modelfile")
        return
    
    # Тестовые вопросы
    print("\n🤖 Тестовые вопросы к модели:")
    print("-" * 50)
    
    test_questions = [
        "Когда начинается хакатон?",
        "Как зарегистрироваться?",
        "Какое расписание?",
        "Какая погода завтра?",
        "Какие требования к команде?"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{i}. Вопрос: {question}")
        print("-" * 30)
        
        response = handler.generate_response(question)
        print(f"Ответ: {response[:150]}...")
    
    print("\n" + "=" * 50)
    print("✅ Интеграция готова к использованию!")
    print("\nДля запуска бота выполните: python bot.py")

if __name__ == "__main__":
    test_model()