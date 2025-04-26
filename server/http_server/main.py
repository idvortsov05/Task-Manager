from config.config_server import get_config
from logger.logger_server import get_logger
from routers import router
from database import create_table

import uvicorn
from fastapi import FastAPI

def main():
    config = get_config("server/http_server/config/config.ini")
    host = config["server"]["host"]
    port = int(config["server"]["port"])
    LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
    logger = get_logger("server", LOGGER_CONFIG_PATH)

    create_table()

    logger.info("Созданы таблицы БД (при первом запуске сервера)")

    app = FastAPI()
    app.include_router(router)
    uvicorn.run(app, host=host, port=port)
    logger.info("Запущено приложение fastapi с данными: {host}:{port}".format(host=host, port=port))


if __name__ == "__main__":
    main()