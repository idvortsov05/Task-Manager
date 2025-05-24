from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger

import base64
import hashlib
import requests
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QMessageBox, QFileDialog

config = get_config("client/http_client/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("client", LOGGER_CONFIG_PATH)


class ProfileWindow(QDialog):
    def __init__(self,token):
        super().__init__()
        self.token = token
        self.photo_path = None
        self.user_id = None
        self.initial_full_name = None
        self.initial_email = None

        logger.debug("Profile window created")
        uic.loadUi('client/http_client/ui/profile/Profile.ui', self)
        logger.debug("Profile window ui was loaded")

        with open('client/http_client/ui/styles/profile.qss', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())
            logger.debug("Profile window styles loaded")

        self.pushButton_update_profile.clicked.connect(self.update_profile)
        self.pushButton_select_photo.clicked.connect(self.select_photo)
        self.pushButton_exit.clicked.connect(self.close)
        logger.debug("Register window signals were connected")

        self.load_user_data()

    def load_user_data(self):
        url_get_current_user = config["URLS"]["current_user"]
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            logger.debug(f"Sending request to get current user: {url_get_current_user}")
            response = requests.get(url_get_current_user, headers=headers)

            if response.status_code == 200:
                user_info = response.json()
                self.initial_full_name = user_info["full_name"]
                self.initial_email = user_info["email"]
                self.lineEdit_FIO.setText(user_info.get("full_name", ""))
                self.lineEdit_email.setText(user_info.get("email", ""))
                self.user_id = user_info.get("id", "")
                logger.debug("User data loaded into profile window")
            else:
                logger.error(f"Failed to get user data: {response.text}")
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить данные пользователя")

        except Exception as e:
            logger.exception(f"Exception while loading user data: {str(e)}")
            QMessageBox.critical(self, "Ошибка", "Ошибка подключения при загрузке данных")

    def select_photo(self):
        file_name = QFileDialog.getOpenFileName(self, "Выбрать фото", "", "Images (*.png *.jpg *.jpeg *.bmp)")

        if file_name:
            self.photo_path = file_name
            logger.debug(f"Photo selected: {file_name}")
        else:
            logger.debug("Photo selection cancelled")

    def update_profile(self):
        data = {}

        full_name = self.lineEdit_FIO.text().strip()
        if full_name != self.initial_full_name:
            data["full_name"] = full_name

        email = self.lineEdit_email.text().strip()
        if email != self.initial_email:
            data["email"] = email

        password = self.lineEdit_password.text().strip()
        if password:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            data["password"] = hashed_password

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

        if not data:
            QMessageBox.about(self, "Нет изменений", "Вы не изменили ни одного поля.")
            return

        try:
            self.pushButton_update_profile.setEnabled(False)

            url_template = config["URLS"]["update_user"]
            url = url_template.replace("{user_id}", str(self.user_id))
            logger.debug(f"Sending update profile request: {url}")

            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.put(url, headers=headers, json=data)

            if response.status_code == 200:
                QMessageBox.about(self, "Успех", "Обновление профиля прошло успешно!")
                self.accept()
            else:
                logger.error(f"Error while profile updated: {response.text}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка обновления данных: {response.text}")

        except Exception as e:
            logger.exception(f"Error while request send: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения к серверу")
        finally:
            self.pushButton_update_profile.setEnabled(True)