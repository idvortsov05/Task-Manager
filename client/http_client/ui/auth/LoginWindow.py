from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger
from client.http_client.ui.auth.RegisterWindow import RegisterWindow
from client.http_client.ui.profile.ProfileWindow import ProfileWindow

from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5 import uic
import requests

config = get_config("client/http_client/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("login window", LOGGER_CONFIG_PATH)


class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.profile_window = None
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

                if not token:
                    QMessageBox.warning(None, "Ошибка", "Токен для входа не получен!")
                    return

                headers = {
                    "Authorization": f"Bearer {token}"
                }

                user_info_response = requests.get(url_get_current_user, headers=headers)

                if user_info_response.status_code == 200:
                    user_info = user_info_response.json()
                    full_name = user_info.get("full_name", "Неизвестный пользователь")
                    role = user_info.get("role", "Неизвестная роль")

                    role_to_see = ''
                    if role == "team_lead":
                        role_to_see = 'Руководитель проекта'
                    elif role == "developer":
                        role_to_see = 'Разработчик'

                    QMessageBox.information(None, "Информация", "Добро пожаловать, " + full_name + '!' +'\n' + "Ваша роль - " + role_to_see)
                    self.accept()
                    self.profile_window = ProfileWindow(token=token)
                    self.profile_window.show()
                else:
                    QMessageBox.warning(None, "Ошибка", f"Не удалось получить данные пользователя: {user_info_response.text}")
            else:
                print("Ошибка входа:", response.text)
        except Exception as e:
            print("Ошибка запроса:", e)

    def register(self):
        register_window = RegisterWindow()
        if register_window.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Регистрация", "Теперь вы можете войти в систему.")
