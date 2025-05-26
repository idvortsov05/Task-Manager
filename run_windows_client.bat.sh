@echo off
setlocal

echo Переход в папку client
cd client

if not exist venv (
    echo Создание виртуального окружения
    python -m venv venv
)

echo Активация окружения
call venv\Scripts\activate.bat

echo Установка зависимостей
venv\Scripts\python.exe -m pip install -r requirements.txt

cd ..

echo Запуск клиента
python client\http_client\main.py
