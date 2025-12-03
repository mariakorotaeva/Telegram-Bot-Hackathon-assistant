# Файл: ollama_client.py
import os
import sys
import subprocess
import time
import ollama
import json

# Определяем, находимся ли мы в Codespace или GitHub Actions
IS_CODESPACE = os.getenv("CODESPACE_NAME") is not None
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") is not None

class OllamaClient:
    def __init__(self, host="localhost", port=11434, auto_setup=True):
        """
        Инициализация Ollama клиента
        
        Args:
            host: Хост Ollama сервера
            port: Порт Ollama сервера
            auto_setup: Автоматически настраивать Ollama в Codespace
        """
        self.base_url = f"http://{host}:{port}"
        self.host = host
        self.port = port
        
        # Автоматическая установка в Codespace если нужно
        if auto_setup and (IS_CODESPACE or IS_GITHUB_ACTIONS):
            self._setup_environment()
        
        # Попытка подключения к клиенту
        self.client = self._create_client()
    
    def _setup_environment(self):
        """Настройка окружения в Codespace/GitHub Actions"""
        print("⚠️  Обнаружена среда Codespace/GitHub Actions")
        print("   Проверяю наличие Ollama...")
        
        try:
            # Проверяем, установлен ли Ollama
            result = subprocess.run(["which", "ollama"], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print("🔄 Ollama не найден. Устанавливаю...")
                self._install_ollama()
            else:
                print(f"✅ Ollama найден: {result.stdout.strip()}")
            
            # Проверяем, запущен ли сервер
            if not self._is_ollama_running():
                print("🔄 Запускаю Ollama сервер...")
                self._start_ollama_server()
            
        except Exception as e:
            print(f"❌ Ошибка настройки: {e}")
            print("   Продолжаю без Ollama...")
    
    def _install_ollama(self):
        """Установка Ollama"""
        try:
            print("Скачиваю установочный скрипт...")
            
            # Установка через официальный скрипт
            install_script = """
            curl -fsSL https://ollama.com/install.sh | sh
            """
            
            result = subprocess.run(
                install_script,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Ollama успешно установлен")
                
                # Добавляем в PATH если нужно
                path_cmd = """
                if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
                    echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.bashrc
                    source ~/.bashrc
                fi
                """
                subprocess.run(path_cmd, shell=True, shell=True)
                
            else:
                print(f"❌ Ошибка установки: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Ошибка при установке: {e}")
    
    def _is_ollama_running(self):
        """Проверка, запущен ли Ollama сервер"""
        try:
            # Пробуем подключиться к API
            import requests
            response = requests.get(f"http://{self.host}:{self.port}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _start_ollama_server(self):
        """Запуск Ollama сервера в фоне"""
        try:
            # Запускаем в фоне
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Ждем запуска
            print("⏳ Жду запуска сервера...")
            for i in range(10):  # 10 попыток по 2 секунды = 20 секунд
                time.sleep(2)
                if self._is_ollama_running():
                    print("✅ Ollama сервер запущен")
                    return True
                print(f"  Попытка {i+1}/10...")
            
            print("⚠️  Не удалось запустить сервер. Возможно требуется ручной запуск.")
            print("   Запустите вручную: ollama serve")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка запуска сервера: {e}")
            return False
    
    def _create_client(self):
        """Создание клиента с обработкой ошибок"""
        try:
            # Проверяем доступность сервера
            if not self._is_ollama_running():
                print("⚠️  Ollama сервер не доступен. Создаю заглушку...")
                return MockClient()
            
            # Создаем реальный клиент
            return ollama.Client(host=f"{self.host}:{self.port}")
            
        except Exception as e:
            print(f"⚠️  Ошибка создания клиента: {e}")
            print("   Использую заглушку для тестирования...")
            return MockClient()
    
    def list_models(self):
        """Показать все доступные модели"""
        try:
            return self.client.list()
        except Exception as e:
            print(f"❌ Ошибка при получении списка моделей: {e}")
            return {"models": []}
    
    def generate_response(self, model_name, prompt, system_prompt=None, **options):
        """Генерация ответа"""
        try:
            response = self.client.generate(
                model=model_name,
                prompt=prompt,
                system=system_prompt,
                options={
                    'temperature': options.get('temperature', 0.7),
                    'num_predict': options.get('max_tokens', 512),
                    'top_p': options.get('top_p', 0.9),
                    'top_k': options.get('top_k', 40)
                }
            )
            return response['response']
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
            return self._get_fallback_response(prompt)
    
    def chat_completion(self, model_name, messages, **options):
        """Чат-комплетирование с историей"""
        try:
            response = self.client.chat(
                model=model_name,
                messages=messages,
                options={
                    'temperature': options.get('temperature', 0.7),
                    'num_predict': options.get('max_tokens', 512)
                }
            )
            return response['message']['content']
        except Exception as e:
            print(f"❌ Ошибка чата: {e}")
            return "Извините, сервис временно недоступен."
    
    def stream_response(self, model_name, prompt, callback):
        """Стриминг ответа"""
        try:
            stream = self.client.generate(
                model=model_name,
                prompt=prompt,
                stream=True
            )
            
            full_response = ""
            for chunk in stream:
                if 'response' in chunk:
                    token = chunk['response']
                    full_response += token
                    callback(token)  # Колбек для обработки каждого токена
            
            return full_response
        except Exception as e:
            print(f"❌ Ошибка стриминга: {e}")
            fallback = "Извините, стриминг недоступен."
            callback(fallback)
            return fallback
    
    def _get_fallback_response(self, prompt):
        """Запасной ответ если Ollama недоступен"""
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["привет", "здравствуйте", "hello", "hi"]):
            return "👋 Привет! Я AI-ассистент. Ollama временно недоступен, но я могу помочь с общими вопросами."
        elif "расписание" in prompt_lower:
            return "📅 Обычное расписание хакатона:\n• 10:00 - Старт\n• 13:00 - Обед\n• 18:00 - Демо проектов"
        elif "команда" in prompt_lower:
            return "👥 Ищите команду на стенде регистрации или в общем чате!"
        elif "помощь" in prompt_lower:
            return "🆘 Я могу помочь с вопросами о расписании, командах и организации. Задавайте вопросы!"
        else:
            return "🤖 Извините, AI-сервис временно недоступен. Попробуйте позже или обратитесь к организаторам."


class MockClient:
    """Заглушка для клиента Ollama когда он не доступен"""
    
    def list(self):
        return {"models": [
            {"name": "test-model", "modified_at": "2024-01-01T00:00:00Z"}
        ]}
    
    def generate(self, model=None, prompt=None, system=None, options=None, **kwargs):
        return {"response": "Это mock-ответ. Ollama не доступен."}
    
    def chat(self, model=None, messages=None, options=None, **kwargs):
        return {"message": {"content": "Это mock-чат ответ. Ollama не доступен."}}


# Утилиты для работы с моделями
def setup_default_model(model_name="qwen2.5:3b"):
    """Настройка модели по умолчанию"""
    print(f"🔄 Настраиваю модель {model_name}...")
    
    client = OllamaClient()
    
    # Проверяем доступность модели
    models = client.list_models().get('models', [])
    available_models = [m['name'] for m in models]
    
    if model_name in available_models:
        print(f"✅ Модель {model_name} уже доступна")
        return True
    
    # Если в Codespace, пробуем скачать модель
    if IS_CODESPACE:
        try:
            print(f"📥 Скачиваю модель {model_name}...")
            subprocess.run(["ollama", "pull", model_name], 
                         capture_output=True, text=True, timeout=300)
            print(f"✅ Модель {model_name} скачана")
            return True
        except Exception as e:
            print(f"❌ Не удалось скачать модель: {e}")
    
    return False


# Использование
if __name__ == "__main__":
    print("🧪 Тестирование Ollama клиента...")
    print(f"Среда: {'Codespace' if IS_CODESPACE else 'GitHub Actions' if IS_GITHUB_ACTIONS else 'Локальная'}")
    
    # Создаем клиент
    client = OllamaClient(auto_setup=True)
    
    # Проверяем модели
    print("\n🔍 Проверяю доступные модели...")
    models = client.list_models()
    
    if models.get('models'):
        print("✅ Доступные модели:")
        for model in models['models']:
            print(f"  - {model['name']}")
    else:
        print("⚠️  Модели не найдены или Ollama недоступен")
    
    # Тест генерации
    print("\n🧪 Тест генерации ответа...")
    
    # Пробуем использовать доступную модель или заглушку
    test_model = "qwen2.5:3b" if "qwen2.5:3b" in [m['name'] for m in models.get('models', [])] else "test-model"
    
    response = client.generate_response(
        model_name=test_model,
        prompt="Привет! Как проходит хакатон?",
        temperature=0.7,
        max_tokens=100
    )
    
    print("🤖 Ответ модели:")
    print(response)
    
    # Настройка модели по умолчанию
    print("\n⚙️  Настройка окружения...")
    setup_default_model()
    
    print("\n✅ Тестирование завершено!")