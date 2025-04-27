from config.config_client import get_config
from logger.logger_client import get_logger

def main():
    config = get_config("client/http_client/config/config.ini")
    host = config["server"]["host"]
    port = int(config["server"]["port"])
    LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
    logger = get_logger("client", LOGGER_CONFIG_PATH)


    logger.info("Созданы таблицы БД (при первом запуске сервера)")
    logger.info("Запущено приложение fastapi с данными: {host}:{port}".format(host=host, port=port))


if __name__ == "__main__":
    main()