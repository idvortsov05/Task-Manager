@echo off
setlocal
echo Переход в папку server
cd server

if not exist venv (
    echo Создание виртуального окружения
    python -m venv venv
)

echo Активация окружения
call venv\Scripts\activate.bat

echo Установка зависимостей
venv\Scripts\python.exe -m pip install -r requirements.txt

cd ..
echo Подготовка данных для обучения
python server\ml\prepare_data.py

echo Обучение модели
python server\ml\train_model.py

echo Запуск сервера
python server\http_server\main.py

