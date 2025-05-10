from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger

from client.http_client.ui.profile.ProfileWindow import ProfileWindow
from client.http_client.ui.main.tasks.TasksWindow import TasksWindow
from client.http_client.ui.main.Task import TaskWidget
from client.http_client.ui.main.createTask.create import CreateTaskWindow

import requests
from PyQt5 import uic
from datetime import datetime
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QMainWindow, QDialog

config = get_config("client/http_client/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("client", LOGGER_CONFIG_PATH)


class MainWindow(QMainWindow):
    def __init__(self, token):
        super().__init__()
        self.login_window = None
        self.tasks_window = None
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.projects = []
        self.project_id = None
        self.project_name = None
        self.user_role = None
        logger.info(f"token: {self.token}")
        logger.debug("Main window created")
        uic.loadUi('client/http_client/ui/main/Main.ui', self)
        logger.debug("Main window ui was loaded")

        with open('client/http_client/ui/styles/main.qss', 'r') as f:
            self.setStyleSheet(f.read())
            logger.debug("Main window styles loaded")

        self.pushButton_profile.clicked.connect(self.open_profile)
        self.pushButton_exit.clicked.connect(self.close_window)
        self.pushButton_tasks.clicked.connect(self.open_tasks)
        self.lineEdit_find_projects.textChanged.connect(self.filter_projects)
        self.lineEdit_find_by_tasks.textChanged.connect(self.find_by_tasks)
        self.listWidget_projects.itemClicked.connect(self.on_project_selected)

        self.verticalLayout_2.setAlignment(QtCore.Qt.AlignTop)
        self.verticalLayout_4.setAlignment(QtCore.Qt.AlignTop)
        self.verticalLayout_6.setAlignment(QtCore.Qt.AlignTop)
        self.verticalLayout_8.setAlignment(QtCore.Qt.AlignTop)

        self.pushButton_add_open_task.clicked.connect(lambda: self.open_create_task("open"))
        self.pushButton_progress_tasks.clicked.connect(lambda: self.open_create_task("in_progress"))
        self.pushButton_finish_tasks.clicked.connect(lambda: self.open_create_task("done"))
        self.pushButton_close_tasks.clicked.connect(lambda: self.open_create_task("closed"))

        logger.debug("Main window signals were connected")
        self.lineEdit_find_projects.setPlaceholderText("Название проекта")

        self.load_projects()

    def open_profile(self):
        profile = ProfileWindow(token=self.token)
        profile.exec_()

    def close_window(self):
        from client.http_client.ui.auth.LoginWindow import LoginWindow
        logger.debug("Main window closed")
        self.close()
        self.login_window = LoginWindow()
        self.login_window.exec_()

    def open_tasks(self):
        logger.debug("Tasks window opened")
        self.tasks_window = TasksWindow(token=self.token, project_id=self.project_id)
        self.tasks_window.exec_()
        self.show()

    def load_projects(self):
        try:
            url = config["URLS"]["get_projects"]
            response = requests.get(url,headers=self.headers)
            response.raise_for_status()

            self.projects = response.json()

            if not self.projects:
                QMessageBox.information(self, "Информация", "У вас нет доступных проектов")
                return

            self.update_projects_list(self.projects)
            if self.projects:
                self.listWidget_projects.setCurrentRow(0)
                self.on_project_selected(self.listWidget_projects.currentItem())

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить проекты: {str(e)}")
            logger.error(f"Failed to load projects: {str(e)}")

    def update_projects_list(self, projects):
        self.listWidget_projects.clear()

        for project in projects:
            item = QtWidgets.QListWidgetItem(project["name"])
            item.setData(QtCore.Qt.UserRole, project)
            self.listWidget_projects.addItem(item)

    def filter_projects(self):
        search_text = self.lineEdit_find_projects.text().strip().lower()

        if not search_text:
            self.update_projects_list(self.projects)
            return

        filtered_projects = [
            p for p in self.projects
            if (search_text in p["name"].lower()) or
               (p.get("description") and search_text in p["description"].lower())
        ]
        self.update_projects_list(filtered_projects)

    def on_project_selected(self, item):
        project = item.data(QtCore.Qt.UserRole)
        self.project_id = project["id"]
        self.project_name = project["name"]
        self.label_project_name.setText(f"Проект: {self.project_name}")
        self.label_project_description.setText(f"Описание проекта: {project['description']}")
        logger.info(f"Selected project: {project['name']} (ID: {project['id']})")

        self.load_tasks_from_project(self.project_id)

    def load_tasks_from_project(self, project_id):
        try:
            self.clear_all_task_widgets()

            url = config["URLS"]["get_tasks"]
            tasks = requests.get(url, headers=self.headers, params={"project_id": project_id}).json()

            for task in tasks:
                widget = TaskWidget(task)
                widget.taskClicked.connect(self.read_task_by_id)

                status = task["status"]
                if status == "open":
                    self.verticalLayout_2.addWidget(widget)
                elif status == "in_progress":
                    self.verticalLayout_4.addWidget(widget)
                elif status == "done":
                     self.verticalLayout_6.addWidget(widget)
                elif status == "closed":
                    self.verticalLayout_8.addWidget(widget)

        except Exception as e:
            logger.error(f"Error loading tasks: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки задач: {str(e)}")

    def clear_all_task_widgets(self):
        try:
            layouts = [
                self.verticalLayout_2,
                self.verticalLayout_4,
                self.verticalLayout_6,
                self.verticalLayout_8
            ]

            for layout in layouts:
                self.clear_layout(layout)

        except Exception as e:
            logger.error(f"Ошибка при очистке всех виджетов задач: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при очистке виджетов: {str(e)}")

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def find_by_tasks(self):
        search_text = self.lineEdit_find_by_tasks.text().strip()

        if not search_text:
            self.load_tasks_from_project(self.project_id)
            return

        try:
            params = {"project_id": self.project_id, "title": search_text}

            url = config["URLS"]["get_tasks"]
            response = requests.get(url,headers=self.headers,params=params)
            response.raise_for_status()

            tasks = response.json()
            self.display_filtered_tasks(tasks)

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка поиска: {str(e)}")

    def display_filtered_tasks(self, tasks):
        self.clear_all_task_widgets()

        for task in tasks:
            widget = TaskWidget(task)
            status = task["status"]

            if status == "open":
                self.verticalLayout_2.addWidget(widget)
            elif status == "in_progress":
                self.verticalLayout_4.addWidget(widget)
            elif status == "done":
                self.verticalLayout_6.addWidget(widget)
            elif status == "closed":
                self.verticalLayout_8.addWidget(widget)

    def open_create_task(self, status):
        if not self.project_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите проект")
            return

        dialog = CreateTaskWindow(self.token, self.project_id, status, self.project_name)
        if dialog.exec_() == QDialog.Accepted:
            self.load_tasks_from_project(self.project_id)

    def read_task_by_id(self, task_id: int):
        try:
            url = config["URLS"]["get_task_by_id"].replace("{task_id}", str(task_id))
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            task = response.json()

            status = task["status"]
            next_status_map = {
                "open": ("Взять в работу", "in_progress"),
                "in_progress": ("Завершить", "done"),
                "done": ("Закрыть", "closed"),
                "closed": ("Переоткрыть", "open")
            }

            valid_transitions_team_lead = {
                "open": "in_progress",
                "in_progress": "done",
                "done": "closed",
                "closed": "open"
            }

            valid_transitions_developer = {
                "open": "in_progress",
                "in_progress": "done"
            }

            response = requests.get(config["URLS"]["current_user"], headers=self.headers)

            if response.status_code == 200:
                user_data = response.json()
                self.user_role = user_data["role"]

            if self.user_role == "team_lead":
                next_status = valid_transitions_team_lead.get(status)
            elif self.user_role == "developer":
                next_status = valid_transitions_developer.get(status)
            else:
                next_status = None

            info_dialog = QtWidgets.QDialog(self)
            info_dialog.setWindowTitle("Информация о задаче")
            info_dialog.setMinimumSize(450, 400)

            layout = QtWidgets.QVBoxLayout(info_dialog)
            layout.setContentsMargins(15, 15, 15, 15)

            form_layout = QtWidgets.QFormLayout()
            form_layout.setVerticalSpacing(10)

            form_layout.addRow("Название:", QtWidgets.QLabel(task['title']))
            form_layout.addRow("Описание:", QtWidgets.QLabel(task.get('description', 'Нет описания')))
            form_layout.addRow("Статус:", QtWidgets.QLabel(self.get_status_text(status)))
            form_layout.addRow("Приоритет:", QtWidgets.QLabel(self.get_priority_text(task.get('priority'))))
            form_layout.addRow("Дедлайн:", QtWidgets.QLabel(self.format_datetime(task.get('deadline'))))
            form_layout.addRow("Проект:", QtWidgets.QLabel(task['project']['name']))

            creator_name = task['creator'].get('full_name', task['creator']['username'])
            form_layout.addRow("Создатель:", QtWidgets.QLabel(creator_name))

            if task.get('assignee'):
                assignee_name = task['assignee'].get('full_name', task['assignee']['username'])
                form_layout.addRow("Исполнитель:", QtWidgets.QLabel(assignee_name))
            else:
                form_layout.addRow("Исполнитель:", QtWidgets.QLabel("Не назначен"))

            layout.addLayout(form_layout)

            button_layout = QtWidgets.QHBoxLayout()
            button_layout.setContentsMargins(0, 10, 0, 0)

            if next_status:
                label, new_status = next_status_map.get(status)
                action_button = QtWidgets.QPushButton(label)
                action_button.setStyleSheet("background-color: #34a853; color: white; border-radius: 8px; padding: 6px 16px;")

                def on_action():
                    confirm_box = QMessageBox(self)
                    confirm_box.setIcon(QMessageBox.Question)
                    confirm_box.setWindowTitle("Подтвердите действие")
                    confirm_box.setText( f"Вы уверены, что хотите изменить статус на '{self.get_status_text(new_status)}'?")

                    yes_button = confirm_box.addButton("Применить", QMessageBox.YesRole)
                    no_button = confirm_box.addButton("Отменить", QMessageBox.NoRole)

                    confirm_box.exec_()
                    if confirm_box.clickedButton() == yes_button:
                        try:
                            update_url = config["URLS"]["update_task_status"].replace("{task_id}", str(task_id))
                            resp = requests.patch(update_url, headers=self.headers, json={"status": new_status})
                            if resp.status_code == 200:
                                QMessageBox.information(self, "Успех", "Статус задачи обновлен")
                                info_dialog.accept()
                                self.load_tasks_from_project(self.project_id)
                            else:
                                err = resp.json().get("detail", "Не удалось обновить статус")
                                QMessageBox.critical(self, "Ошибка", err)
                        except Exception as e:
                            QMessageBox.critical(self, "Ошибка", f"Ошибка обновления статуса: {str(e)}")
                    elif confirm_box.clickedButton() == no_button:
                        QMessageBox.information(self, "Информация", "Операция была отменена")

                action_button.clicked.connect(on_action)
                button_layout.addWidget(action_button, alignment=QtCore.Qt.AlignLeft)

            close_btn = QtWidgets.QPushButton("Закрыть")
            close_btn.clicked.connect(info_dialog.close)
            close_btn.setStyleSheet("background-color: #4285f4; color: white; border-radius: 8px; padding: 6px 16px;")
            button_layout.addWidget(close_btn, alignment=QtCore.Qt.AlignRight)

            layout.addLayout(button_layout)

            info_dialog.setStyleSheet("""QDialog { background-color: #f4f6f8; }QLabel { font-size: 14px; }""")
            info_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить задачу: {str(e)}")

    def get_priority_text(self, priority_value):
        try:
            priority = float(priority_value)
            if priority <= 0.35:
                return "низкий 🟢"
            elif 0.35 < priority <= 0.75:
                return "средний 🟡"
            elif 0.75 < priority <= 0.99:
                return "высокий 🔴"
            return "не определён"
        except:
            return "не определён"

    def get_status_text(self, status):
        status_map = {
            "open": "Открыта",
            "in_progress": "В работе",
            "done": "Готова",
            "closed": "Закрыта"
        }
        return status_map.get(status, status)

    def format_datetime(self, datetime_str):
        try:
            if not datetime_str:
                return ""

            datetime_str = datetime_str.rstrip("Z")

            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
                try:
                    dt = datetime.strptime(datetime_str, fmt)
                    return dt.strftime("%d.%m.%Y %H:%M")
                except ValueError:
                    continue

            return datetime_str
        except Exception as e:
            return datetime_str










