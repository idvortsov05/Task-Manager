from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger
from client.http_client.ui.auth.RegisterWindow import RegisterWindow
from client.http_client.ui.main.MainWindow import MainWindow

import requests
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QMessageBox

config = get_config("client/http_client/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("client", LOGGER_CONFIG_PATH)


class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.main_window = None
        logger.debug("Login window created")
        uic.loadUi('client/http_client/ui/auth/Login.ui', self)
        logger.debug("Login window ui was loaded")

        with open('client/http_client/ui/styles/auth.qss', 'r') as f:
            self.setStyleSheet(f.read())
            logger.debug("Login window styles loaded")

        self.pushButton_register.clicked.connect(self.register)
        self.pushButton_login.clicked.connect(self.login)
        logger.debug("Login window signals was triggered")

    def login(self):
        username = self.lineEdit_login.text()
        password = self.lineEdit_password.text()

        if not username or not password:
            QMessageBox.warning(None, "Предупреждение", "Поля логина и пароля должны быть заполнены!")
            return

        url_login = config["URLS"]["login"]
        url_get_current_user = config["URLS"]["current_user"]

        try:
            response = requests.post(url_login, data={'username': username, 'password': password})

            if response.status_code == 200:
                token = response.json().get("access_token")
                headers = { "Authorization": f"Bearer {token}" }

                user_info_response = requests.get(url_get_current_user, headers=headers)

                if user_info_response.status_code == 200:
                    user = user_info_response.json()
                    full_name = user["full_name"]
                    role = user["role"]

                    if role == "team_lead":
                        role = 'Руководитель проекта'
                    else:
                        role = 'Разработчик'

                    QMessageBox.information(None, "Информация", "Добро пожаловать, " + full_name + '!' +'\n' + "Ваша роль - " + role)
                    self.accept()
                    self.close()
                    self.main_window = MainWindow(token=token)
                    self.main_window.show()
                else:
                    QMessageBox.warning(None, "Ошибка", f"Не удалось получить данные пользователя: {user_info_response.text}")
            else:
                logger.error("Error while logging in")

        except Exception as e:
            logger.error(f"Error while logging in: {e}")

    def register(self):
        self.hide()
        register_window = RegisterWindow()
        register_window.exec_()
        self.show()
