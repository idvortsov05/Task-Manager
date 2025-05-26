#!/bin/bash
set -e  # Остановить выполнение при любой ошибке

echo "Переход в папку server"
cd server

if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения"
    python3 -m venv venv
fi

echo "Активация окружения"
source venv/bin/activate

echo "Установка зависимостей"
pip install -r requirements.txt

cd ..
echo "Подготовка данных для обучения"
python3 server/ml/prepare_data.py

echo "Обучение модели"
python3 server/ml/train_model.py

echo "Запуск сервера"
python3 server/http_server/main.py
