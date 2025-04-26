import requests
import json

from config.config_client import get_config
from logger.logger_cleint import get_logger

config = get_config("client/http_client/config/config.ini")
host = config["server"]["host"]
port = int(config["server"]["port"])
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("server", LOGGER_CONFIG_PATH)

auth_data = {
    "username": "ваш_логин",
    "password": "ваш_пароль"
}

# 1. Отправка запроса на авторизацию
try:
    response = requests.post(
        "http://localhost:8000/token",
        json=auth_data,  # Отправка как JSON
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()  # Проверка на ошибки

    # Получаем токен из ответа
    token = response.json().get("access_token")
    print("Успешная авторизация. Токен:", token)

except requests.exceptions.RequestException as e:
    print("Ошибка авторизации:", e)

# 2. Пример запроса с токеном
if token:
    try:
        tasks_response = requests.get(
            "http://localhost:8000/tasks/",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        print("Список задач:", tasks_response.json())

    except requests.exceptions.RequestException as e:
        print("Ошибка запроса задач:", e)