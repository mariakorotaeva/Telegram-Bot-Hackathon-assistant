from ollama_handler import HackathonAssistant

print("🧪 Тестирование HackathonAssistant...")

# Создаем экземпляр
handler = HackathonAssistant()

# 1. Тестируем подключение
print("\n🔗 Проверка подключения к модели...")
if handler.test_connection():
    print("✅ Подключение успешно!")
else:
    print("❌ Не удалось подключиться к модели")
    print("Убедитесь что:")
    print("1. Ollama установлен: https://ollama.com/")
    print("2. Модель загружена: ollama pull hackathon-assistant")
    print("3. Ollama сервер запущен: ollama serve")
    exit(1)

# 2. Получаем информацию о модели
print("\n📊 Информация о модели...")
model_info = handler.get_model_info()
if model_info:
    print(f"✅ Модель: {model_info.get('name', 'N/A')}")
    print(f"📦 Размер: {model_info.get('size', 'N/A')}")
    print(f"🕐 Изменена: {model_info.get('modified', 'N/A')}")
else:
    print("⚠️ Не удалось получить информацию о модели")

# 3. Тестовый запрос
print("\n🧠 Тестовый запрос к модели...")
try:
    import asyncio
    
    # Запускаем асинхронный запрос
    async def test_question():
        result = await handler.ask("Когда начало хакатона?")
        
        if result['success']:
            print(f"✅ Ответ получен!")
            print(f"🤖 Модель: {result['model']}")
            print(f"⏱️ Время ответа: {result['response_time']}")
            print(f"📅 Ответ: {result['answer'][:200]}...")
        else:
            print(f"❌ Ошибка: {result.get('error', 'Unknown error')}")
            print(f"💬 Ответ: {result['answer']}")
    
    asyncio.run(test_question())
    
except Exception as e:
    print(f"❌ Ошибка при тестовом запросе: {e}")

print("\n🎯 Тестирование завершено!")
