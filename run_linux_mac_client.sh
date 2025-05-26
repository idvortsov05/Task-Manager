#!/bin/bash
set -e

echo "Переход в папку client"
cd client

if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения"
    python3 -m venv venv
fi

echo "Активация окружения"
source venv/bin/activate

echo "Установка зависимостей"
pip install -r requirements.txt

cd ..

echo "Запуск клиента"
python3 client/http_client/main.py
