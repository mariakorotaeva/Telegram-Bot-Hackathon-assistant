@echo off
echo Создание кастомной модели для хакатон-ассистента...
echo.

echo 1. Проверка наличия базовой модели...
ollama list | findstr "qwen2.5-vl"
if %errorlevel% neq 0 (
    echo Базовая модель не найдена. Скачиваю...
    ollama pull qwen2.5-vl:4b
)

echo.
echo 2. Создание модели hackathon-assistant из Modelfile...
ollama create hackathon-assistant -f Modelfile

echo.
echo 3. Проверка созданной модели...
ollama list

echo.
echo 4. Тестовый запуск...
echo Запускаю тестовый запрос...
ollama run hackathon-assistant "Привет! Я участник хакатона"

echo.
echo Модель успешно создана!
pause