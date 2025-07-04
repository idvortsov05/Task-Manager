from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger

import requests
from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QMessageBox

config = get_config("client/http_client/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("client", LOGGER_CONFIG_PATH)


class ProjectWindow(QDialog):
    def __init__(self, token, teamlead_id):
        super().__init__()
        self.token = token
        self.teamlead_id = teamlead_id
        logger.debug(f"teamlead id: {self.teamlead_id}")
        self.headers = {"Authorization": f"Bearer {self.token}"}

        self.status_mapping = {
            "Открыт": "open",
            "Активен": "active",
            "Завершен": "completed"
        }

        logger.debug("CreateProject window created")
        uic.loadUi('client/http_client/ui/main/Project.ui', self)
        logger.debug("CreateProject window ui was loaded")

        with open('client/http_client/ui/styles/project.qss', 'r', encoding='utf-8') as f:
            self.setStyleSheet(f.read())
            logger.debug("CreateProject window styles loaded")

        self.init_ui()
        self.pushButton_create_project.clicked.connect(self.create_project)

    def init_ui(self):
        self.comboBox_status.addItems(self.status_mapping.keys())
        self.lineEdit_name.setPlaceholderText("Введите название проекта")
        self.lineEdit_description.setPlaceholderText("Опишите проект")

    def validate_input(self):
        if not self.lineEdit_name.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название проекта")
            return False

        if not self.lineEdit_description.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите описание проекта")
            return False

        return True

    def create_project(self):
        if not self.validate_input():
            return

        try:
            selected_status = self.comboBox_status.currentText()
            status_value = self.status_mapping.get(selected_status, "open")

            project_data = {
                "name": self.lineEdit_name.text().strip(),
                "description": self.lineEdit_description.text().strip(),
                "status": status_value,
                "team_lead_id": self.teamlead_id
            }

            logger.debug(f"Creating project with data: {project_data}")

            response = requests.post(
                config["URLS"]["create_project"],
                headers=self.headers,
                json=project_data
            )
            response.raise_for_status()

            QMessageBox.about(self, "Успех", "Проект успешно создан")
            self.accept()

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response.text:
                error_msg = e.response.text
            logger.error(f"Failed to create project: {error_msg}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать проект:\n{error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")