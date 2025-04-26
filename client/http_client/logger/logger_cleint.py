import logging
import logging.config
import os


def get_logger(name, path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Файл конфигурации по этому пути: {path} не найден!")

    logging.config.fileConfig(path)
    logger = logging.getLogger(name)
    return logger
