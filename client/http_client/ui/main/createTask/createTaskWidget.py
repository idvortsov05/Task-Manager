from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger

import requests
from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import QDialog, QMessageBox

config = get_config("client/http_client/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("client", LOGGER_CONFIG_PATH)


class CreateTaskWindow(QDialog):
    def __init__(self, token, project_id, status, project_name):
        super().__init__()
        self.token = token
        self.project_name = project_name
        self.project_id = project_id
        self.status = status
        self.headers = {"Authorization": f"Bearer {self.token}"}

        logger.debug("CreateTask window created")
        uic.loadUi('client/http_client/ui/main/createTask/createTask.ui', self)
        logger.debug("CreateTask window ui was loaded")

        with open('client/http_client/ui/styles/createTask.qss', 'r') as f:
            self.setStyleSheet(f.read())
            logger.debug("CreateTask window styles loaded")

        self.pushButton_open_calendar.clicked.connect(self.toggle_calendar)
        self.pushButton_create_task.clicked.connect(self.create_task)
        self.calendarWidget_select_date.clicked.connect(self.set_date_from_calendar)
        logger.debug("CreateTask window signals loaded")

        self.init_ui()
        self.load_users()

    def init_ui(self):
        self.calendarWidget_select_date.setVisible(False)
        self.label_info.setText(f"Создание задачи в проекте {self.project_name}")
        self.label_status.setText(f"Статус добавляемой задачи: {self.get_status_text(self.status)}")
        self.lineEdit_title.setPlaceholderText("Введите название задачи")
        self.lineEdit_description.setPlaceholderText("Введите описание задачи")
        self.dateTimeEdit.setDateTime(QtCore.QDateTime.currentDateTime().addDays(1))
        self.calendarWidget_select_date.setSelectedDate(QtCore.QDate.currentDate())

    def toggle_calendar(self):
        self.calendarWidget_select_date.setVisible(not self.calendarWidget_select_date.isVisible())

    def set_date_from_calendar(self, date):
        qdate = self.calendarWidget_select_date.selectedDate()
        current_time = self.dateTimeEdit.time()
        self.dateTimeEdit.setDateTime(QtCore.QDateTime(qdate, current_time))
        self.calendarWidget_select_date.setVisible(False)

    def load_users(self):
        try:
            url = config["URLS"]["get_users"]
            response = requests.get(url,headers=self.headers)
            response.raise_for_status()
            developers = response.json()

            self.comboBox_select_assignee.clear()
            for dev in developers:
                self.comboBox_select_assignee.addItem(dev['full_name'], dev['id'])

        except Exception as e:
            logger.error(f"Failed to load developers: {str(e)}")
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить список разработчиков")

    def validate_input(self):
        if not self.lineEdit_title.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите заголовок задачи")
            return False

        if not self.lineEdit_description.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите описание задачи")
            return False

        if self.comboBox_select_assignee.currentIndex() == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите исполнителя")
            return False

        return True

    def create_task(self):
        if not self.validate_input():
            return

        try:
            task_data = {
                "title": self.lineEdit_title.text().strip(),
                "description": self.lineEdit_description.text().strip(),
                "status": self.status,
                "deadline": self.dateTimeEdit.dateTime().toString(QtCore.Qt.ISODate),
                "priority": 0,
                "project_id": self.project_id,
                "assigned_to": self.comboBox_select_assignee.currentData()
            }

            logger.debug(f"Creating task with data: {task_data}")

            url = config["URLS"]["create_task"]
            response = requests.post(url,headers=self.headers,json=task_data)
            response.raise_for_status()

            QMessageBox.about(self, "Успех", "Задача успешно создана")
            self.accept()

        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать задачу: {str(e)}")

    def get_status_text(self, status):
        status_map = {
            "open": "Открыта",
            "in_progress": "В работе",
            "done": "Готова",
            "closed": "Закрыта"
        }
        return status_map.get(status, status)