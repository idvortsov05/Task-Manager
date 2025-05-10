import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger

from ui.auth.LoginWindow import LoginWindow
from PyQt5.QtWidgets import QApplication

def main():
    config = get_config("client/http_client/config/config.ini")
    LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
    logger = get_logger("client", LOGGER_CONFIG_PATH)

if __name__ == "__main__":
    app = QApplication([])
    window = LoginWindow()
    window.show()
    app.exec_()
    main()