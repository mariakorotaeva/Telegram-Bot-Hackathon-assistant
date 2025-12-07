@echo off
echo ============================================
echo Настройка Хакатон Ассистента
echo ============================================

echo 1. Проверка установки Ollama...
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo Ollama не найден! Установите с https://ollama.com
    pause
    exit /b 1
)

echo 2. Загрузка модели qwen2.5-vl:4b...
ollama pull qwen2.5-vl:4b

echo 3. Установка Python зависимостей...
pip install -r requirements.txt

echo 4. Создание конфигурационных файлов...
if not exist ".env" (
    copy .env.example .env
    echo Создан файл .env. Отредактируйте его!
)

echo 5. Проверка базы знаний...
if not exist "knowledge_base" (
    mkdir knowledge_base
    echo Создана папка knowledge_base
)

echo.
echo ============================================
echo НАСТРОЙКА ЗАВЕРШЕНА!
echo ============================================
echo.
echo Дальнейшие шаги:
echo 1. Отредактируйте файл .env (добавьте токен бота)
echo 2. Заполните базу знаний в папке knowledge_base/
echo 3. Запустите бота: python bot.py
echo.
pause