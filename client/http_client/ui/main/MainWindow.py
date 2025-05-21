from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger

from client.http_client.ui.profile.ProfileWindow import ProfileWindow
from client.http_client.ui.main.tasks.TasksWindow import TasksWindow
from client.http_client.ui.main.TaskWindow import TaskWidget
from client.http_client.ui.main.createTask.createTaskWidget import CreateTaskWindow
from client.http_client.ui.main.ProjectWidget import ProjectWindow
from client.http_client.ui.reports.report_generator import generate_pdf_report

import os
import requests
from PyQt5 import uic
from datetime import datetime
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QMainWindow, QDialog, QFileDialog

config = get_config("client/http_client/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("client", LOGGER_CONFIG_PATH)


class MainWindow(QMainWindow):
    def __init__(self, token):
        super().__init__()
        self.login_window = None
        self.tasks_window = None
        self.project_window = None
        self.token = token
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.projects = []
        self.project_id = None
        self.project_name = None
        self.user_role = None
        self.user_id = None
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
        self.pushButton_create_project.clicked.connect(self.create_project)
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
        self.pushButton_delete_project.clicked.connect(self.delete_project)
        self.pushButton_create_report.clicked.connect(self.generate_project_report)

        logger.debug("Main window signals were connected")
        self.lineEdit_find_projects.setPlaceholderText("Название проекта")
        self.label_project_name.setVisible(False)
        self.label_project_description.setVisible(False)

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

    def create_project(self):
        logger.debug("Create project window opened")

        response = requests.get(config["URLS"]["current_user"], headers=self.headers)

        if response.status_code == 200:
            user_data = response.json()
            self.user_id = user_data["id"]
        self.project_window = ProjectWindow(token=self.token, teamlead_id=self.user_id)
        logger.debug(f"user id: {self.user_id}")
        self.project_window.exec_()
        self.load_projects()
        self.show()

    def load_projects(self):
        try:
            url = config["URLS"]["get_projects"]
            response = requests.get(url,headers=self.headers)
            response.raise_for_status()

            self.projects = response.json()

            if not self.projects:
                QMessageBox.about(self, "Информация", "У вас нет доступных проектов")
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
        self.label_project_name.setVisible(True)
        self.label_project_description.setText(f"Описание проекта: {project['description']}")
        self.label_project_description.setVisible(True)
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
                                QMessageBox.about(self, "Успех", "Статус задачи обновлен")
                                info_dialog.accept()
                                self.load_tasks_from_project(self.project_id)
                            else:
                                err = resp.json().get("detail", "Не удалось обновить статус")
                                QMessageBox.critical(self, "Ошибка", err)
                        except Exception as e:
                            QMessageBox.critical(self, "Ошибка", f"Ошибка обновления статуса: {str(e)}")
                    elif confirm_box.clickedButton() == no_button:
                        QMessageBox.about(self, "Информация", "Операция была отменена")

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

    def delete_project(self):
        if self.project_id is None:
            QMessageBox.warning(self, "Ошибка", "Проект не выбран")
            return

        try:
            project_name = self.project_name

            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Подтверждение удаления")
            dialog.setMinimumWidth(400)

            layout = QtWidgets.QVBoxLayout(dialog)

            label = QtWidgets.QLabel(f'Вы точно хотите удалить проект "<b>{project_name}</b>" (ID: {self.project_id})?')
            label.setWordWrap(True)
            layout.addWidget(label)

            button_box = QtWidgets.QHBoxLayout()

            btn_cancel = QtWidgets.QPushButton("Отменить")
            btn_cancel.setObjectName("pushButton_cancel")
            btn_cancel.clicked.connect(dialog.reject)
            button_box.addWidget(btn_cancel)

            btn_apply = QtWidgets.QPushButton("Подтвердить")
            btn_apply.setObjectName("pushButton_apply")
            btn_apply.clicked.connect(dialog.accept)
            button_box.addWidget(btn_apply)

            layout.addLayout(button_box)

            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f4f6f8;
                    padding: 10px;
                }
                QLabel {
                    font-size: 13px;
                    margin-bottom: 5px;
                }
                QPushButton#pushButton_apply {
                    background-color: #34a853;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 6px 16px;
                    border: none;
                    min-width: 100px;
                }
                QPushButton#pushButton_cancel {
                    background-color: #ea4335;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 6px 16px;
                    border: none;
                    min-width: 100px;
                }
            """)

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                logger.info(f"Попытка удаления проекта {self.project_id}")

                url = config["URLS"]["delete_project"].replace("{project_id}", str(self.project_id))
                response = requests.delete(url, headers=self.headers, json={"project_id": int(self.project_id)})

                if response.status_code == 200:
                    logger.info(f"Проект {self.project_id} успешно удален")
                    QMessageBox.about(self, "Успех", "Проект успешно удален")
                    self.project_id = None
                    self.load_projects()
                else:
                    error_msg = response.json().get("message", "Неизвестная ошибка")
                    logger.error(f"Ошибка удаления: {error_msg}")
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить проект: {error_msg}")

            else:
                logger.info(f"Удаление проекта {self.project_id} отменено пользователем")

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Ошибка сети при удалении: {error_msg}")
            QMessageBox.critical(self, "Ошибка сети", f"Не удалось соединиться с сервером: {error_msg}")

    def generate_project_report(self):
        if not self.project_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите проект")
            return

        try:
            url_project = config["URLS"]["get_project_by_id"].format(project_id=self.project_id)
            project = requests.get(url_project, headers=self.headers).json()

            url_user = config["URLS"]["get_user_by_id"].format(user_id=project["team_lead_id"])
            team_lead = requests.get(url_user, headers=self.headers).json()

            url_tasks = config["URLS"]["get_tasks"]
            tasks = requests.get(url_tasks, headers=self.headers, params={"project_id": self.project_id}).json()

            directory = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения отчёта")
            if directory:
                safe_name = project['name'].replace(" ", "_")
                filename = os.path.join(directory, f"{safe_name}_отчёт.pdf")

                icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'images', 'icon.png'))
                generate_pdf_report(project, tasks, team_lead, filename, icon_path)
                QMessageBox.information(self, "Успех", f"Отчёт успешно сохранён в:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при генерации отчёта: {str(e)}")










