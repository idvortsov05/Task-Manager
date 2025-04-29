from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger

from PyQt5.QtWidgets import QDialog, QMessageBox, QFileDialog
from PyQt5 import uic
import requests
import base64

config = get_config("client/http_client/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("register window", LOGGER_CONFIG_PATH)


class RegisterWindow(QDialog):
    def __init__(self):
        super().__init__()
        logger.debug("Register window created")
        uic.loadUi('client/http_client/ui/auth/Register.ui', self)
        logger.debug("Register window ui was loaded")

        with open('client/http_client/ui/styles/auth.qss', 'r') as f:
            self.setStyleSheet(f.read())
            logger.debug("Register window styles loaded")

        self.pushButton_register.clicked.connect(self.register)
        self.pushButton_select_photo.clicked.connect(self.select_photo)
        logger.debug("Register window signals were connected")

        self.photo_path = None

        self.comboBox.addItems(["Руководитель проекта", "Разработчик"])

    def select_photo(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Выбрать фото", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_name:
            self.photo_path = file_name
            logger.debug(f"Photo selected: {file_name}")
        else:
            logger.debug("Photo selection cancelled")

    def register(self):
        username = self.lineEdit_username.text().strip()
        full_name = self.lineEdit_name.text().strip()
        email = self.lineEdit_email.text().strip()
        password = self.lineEdit_password.text().strip()
        role = self.comboBox.currentText()

        if not username or not full_name or not email or not password or not role:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните все обязательные поля!")
            return

        role_to_db = ''
        if role == 'Руководитель проекта':
            role_to_db = 'team_lead'
        elif role == 'Разработчик':
            role_to_db = 'developer'

        data = {
            "username": username,
            "full_name": full_name,
            "email": email,
            "password": password,
            "role": role_to_db,
            "image": None
        }

        if self.photo_path:
            try:
                with open(self.photo_path, "rb") as img_file:
                    encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                    data["image"] = encoded_string
                    logger.debug("Photo encoded to base64")
            except Exception as e:
                logger.error(f"Error while encoded photo: {str(e)}")
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить фото")
                return

        try:
            self.pushButton_register.setEnabled(False)

            url = config["URLS"]["register"]
            logger.debug("Sending register request: {url}")

            response = requests.post(url, json=data)

            if response.status_code == 200:
                QMessageBox.information(self, "Успех", "Регистрация прошла успешно!")
                self.accept()
            else:
                logger.error(f"Error while register: {response.text}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка регистрации: {response.text}")

        except Exception as e:
            logger.exception(f"Ошибка при отправке запроса регистрации: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения к серверу")
        finally:
            self.pushButton_register.setEnabled(True)