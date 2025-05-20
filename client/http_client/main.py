import sys
import os
from PyQt5.QtGui import QIcon

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'images', 'icon.png'))
print("ICON PATH:", icon_path)
print("Файл существует:", os.path.exists(icon_path))

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
    app.setWindowIcon(QIcon(icon_path))
    window = LoginWindow()
    window.setWindowIcon(QIcon(icon_path))
    window.show()
    app.exec_()
    main()