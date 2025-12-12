# Файл: ollama_clients.py
"""
Минимальный Ollama клиент для создания модели
Только с qwen3-vl:4b-model.Modelfile
"""

import os
import sys
import subprocess
import json
import time

class OllamaModelCreator:
    """Создает модель из Modelfile"""
    
    def __init__(self, modelfile_path="/bot/models/qwen3-vl:4b-model.Modelfile"):
        self.modelfile_path = modelfile_path
        self.model_name = "qwen3-vl:4b-model"
        
    def check_ollama_installed(self):
        """Проверка установки Ollama"""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def install_ollama(self):
        """Установка Ollama"""
        print("📦 Устанавливаю Ollama...")
        try:
            # Скачиваем и устанавливаем
            install_cmd = "curl -fsSL https://ollama.com/install.sh | sh"
            result = subprocess.run(
                install_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Ollama установлен")
                return True
            else:
                print(f"❌ Ошибка установки: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def start_ollama_server(self):
        """Запуск сервера Ollama"""
        print("🚀 Запускаю Ollama сервер...")
        
        # Проверяем, не запущен ли уже
        try:
            result = subprocess.run(
                ["pgrep", "ollama"],
                capture_output=True
            )
            if result.returncode == 0:
                print("✅ Сервер уже запущен")
                return True
        except:
            pass
        
        # Запускаем в фоне
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Ждем запуска
            for i in range(10):
                time.sleep(2)
                try:
                    # Проверяем доступность через API
                    import requests
                    response = requests.get("http://localhost:11434/api/tags", timeout=2)
                    if response.status_code == 200:
                        print("✅ Сервер запущен")
                        return True
                except:
                    print(f"  Ожидание... {i+1}/10")
            
            print("⚠️  Сервер не запустился автоматически")
            print("   Запустите вручную: ollama serve")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
            return False
    
    def check_model_exists(self):
        """Проверка существования модели"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True
            )
            
            if self.model_name in result.stdout:
                print(f"✅ Модель '{self.model_name}' уже существует")
                return True
            return False
            
        except Exception as e:
            print(f"❌ Ошибка проверки: {e}")
            return False
    
    def create_model_from_modelfile(self):
        """Создание модели из Modelfile"""
        print(f"🔨 Создаю модель '{self.model_name}'...")
        
        # Проверяем существование Modelfile
        if not os.path.exists(self.modelfile_path):
            print(f"❌ Файл {self.modelfile_path} не найден!")
            print("Создаю базовый Modelfile...")
            self._create_basic_modelfile()
        
        try:
            # Создаем модель
            result = subprocess.run(
                ["ollama", "create", self.model_name, "-f", self.modelfile_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 минут
            )
            
            if result.returncode == 0:
                print(f"✅ Модель '{self.model_name}' создана!")
                return True
            else:
                print(f"❌ Ошибка создания: {result.stderr}")
                
                # Пробуем скачать готовую модель
                print("🔄 Пробую скачать базовую модель...")
                return self.download_base_model()
                
        except subprocess.TimeoutExpired:
            print("❌ Таймаут при создании модели")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def _create_basic_modelfile(self):
        """Создание базового Modelfile если его нет"""
        basic_content = """FROM qwen2.5:3b

# Системный промпт для хакатона
SYSTEM \"\"\"
Ты - полезный AI-ассистент для участников хакатона.
Отвечай кратко и по делу на русском языке.
Помогай с вопросами о расписании, командах и проектах.
\"\"\"

# Параметры модели
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_predict 512
"""
        
        # Создаем директорию если нужно
        os.makedirs(os.path.dirname(self.modelfile_path), exist_ok=True)
        
        # Записываем файл
        with open(self.modelfile_path, "w") as f:
            f.write(basic_content)
        
        print(f"✅ Создан базовый Modelfile: {self.modelfile_path}")
    
    def download_base_model(self):
        """Скачивание базовой модели"""
        try:
            print("📥 Скачиваю базовую модель qwen2.5:3b...")
            result = subprocess.run(
                ["ollama", "pull", "qwen2.5:3b"],
                capture_output=True,
                text=True,
                timeout=600  # 10 минут
            )
            
            if result.returncode == 0:
                print("✅ Модель скачана")
                return True
            else:
                print(f"❌ Ошибка скачивания: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def test_model(self):
        """Тестирование модели"""
        print("\n🧪 Тестирую модель...")
        
        try:
            result = subprocess.run(
                ["ollama", "run", self.model_name, "Привет! Как дела?"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Модель работает!")
                print(f"\nПример ответа:\n{result.stdout[:200]}...")
                return True
            else:
                print(f"⚠️  Модель создана, но есть ошибка: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")
            return False
    
    def setup_model(self):
        """Полная настройка модели"""
        print("="*60)
        print("🚀 НАСТРОЙКА МОДЕЛИ OLLAMA")
        print("="*60)
        
        # 1. Проверяем Ollama
        if not self.check_ollama_installed():
            print("❌ Ollama не установлен")
            if not self.install_ollama():
                return False
        
        # 2. Запускаем сервер
        if not self.start_ollama_server():
            print("⚠️  Проблема с сервером, но продолжаем...")
        
        # 3. Проверяем модель
        if self.check_model_exists():
            # Модель уже есть, тестируем
            return self.test_model()
        
        # 4. Создаем модель
        if not self.create_model_from_modelfile():
            return False
        
        # 5. Тестируем
        return self.test_model()

# Создаем глобальный экземпляр
model_creator = OllamaModelCreator()


# ============================================================================
# ПРОСТОЙ КЛИЕНТ ДЛЯ РАБОТЫ С МОДЕЛЬЮ
# ============================================================================

class SimpleOllamaClient:
    """Простой клиент для работы с созданной моделью"""
    
    def __init__(self):
        self.model_name = "qwen3-vl:4b-model"
        self.base_url = "http://localhost:11434"
        
    async def ask(self, question: str) -> str:
        """Задать вопрос модели через API"""
        try:
            import requests
            
            payload = {
                "model": self.model_name,
                "prompt": question,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 512
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "Нет ответа")
            else:
                return f"Ошибка API: {response.status_code}"
                
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def ask_sync(self, question: str) -> str:
        """Синхронная версия"""
        try:
            import requests
            import json
            
            payload = {
                "model": self.model_name,
                "prompt": question,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "Нет ответа")
            else:
                return f"Ошибка: {response.status_code}"
                
        except Exception as e:
            return f"Ошибка: {str(e)}"

# Глобальный клиент
simple_client = SimpleOllamaClient()


# ============================================================================
# ТЕСТИРОВАНИЕ
# ============================================================================

if __name__ == "__main__":
    """Запуск настройки модели"""
    
    # Запускаем настройку
    success = model_creator.setup_model()
    
    if success:
        print("\n" + "="*60)
        print("🎉 МОДЕЛЬ ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
        print("="*60)
        
        print("\n💡 Пример использования в коде:")
        print("""
from ollama_clients import simple_client

# Синхронный вызов
response = simple_client.ask_sync("Привет! Что такое хакатон?")
print(response)

# Асинхронный вызов (если используете async)
import asyncio
response = asyncio.run(simple_client.ask("Как пройти регистрацию?"))
print(response)
        """)
        
        # Тестовый вопрос
        print("\n🧪 Тестовый вопрос:")
        response = simple_client.ask_sync("Привет! Расскажи о себе в двух предложениях.")
        print(f"🤖 {response}")
        
    else:
        print("\n" + "="*60)
        print("❌ НЕ УДАЛОСЬ НАСТРОИТЬ МОДЕЛЬ")
        print("="*60)
        print("\nПопробуйте выполнить вручную:")
        print("1. Установите Ollama: curl -fsSL https://ollama.com/install.sh | sh")
        print("2. Запустите сервер: ollama serve")
        print("3. Создайте модель: ollama create qwen3-vl:4b-model -f /models/qwen3-vl:4b-model.Modelfile")
        print("4. Протестируйте: ollama run qwen3-vl:4b-model 'Привет!'")