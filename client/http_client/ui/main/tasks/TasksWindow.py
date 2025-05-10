from client.http_client.config.config_client import get_config
from client.http_client.logger.logger_client import get_logger

import requests
from PyQt5 import uic
from PyQt5.QtCore import Qt
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QDialog, QMessageBox

config = get_config("client/http_client/config/config.ini")
logger = get_logger("client", config["logger"]["LOGGER_CONFIG_PATH"])


class TasksWindow(QDialog):
    def __init__(self, token, project_id):
        super().__init__()
        self.token = token
        self.project_id = project_id
        self.project_name = None
        self.user_id = None
        self.user_role = None
        self.task_description = None
        self.headers = {"Authorization": f"Bearer {self.token}"}

        uic.loadUi('client/http_client/ui/main/tasks/Tasks.ui', self)

        with open('client/http_client/ui/styles/tasks.qss', 'r') as f:
            self.setStyleSheet(f.read())
            logger.debug("Tasks window styles loaded")

        self.init_ui()
        self.load_user_data()

        if self.user_role == "developer":
            self.pushButton_reassign_task.setEnabled(False)
            self.pushButton_reassign_task.setVisible(False)

            self.pushButton_delete_task.setEnabled(False)
            self.pushButton_delete_task.setVisible(False)

        self.pushButton_exit.clicked.connect(self.close)
        self.pushButton_apply_filters.clicked.connect(self.apply_filters)
        self.pushButton_reset_filters.clicked.connect(self.reset_filters)
        self.pushButton_read_task.clicked.connect(self.read_task)
        self.pushButton_update_status_task.clicked.connect(self.update_status_task)
        self.pushButton_reassign_task.clicked.connect(self.reassign_task)
        self.pushButton_delete_task.clicked.connect(self.delete_task)
        self.tableView_tasks.selectionModel().selectionChanged.connect(self.on_task_selected)

        self.tableView_tasks_history.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.tableView_tasks_history.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.tableView_tasks_history.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.tableView_tasks_history.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)

        self.groupBox_task_history.setVisible(False)
        self.label_task_description.setVisible(False)

        self.apply_filters()

    def init_ui(self):
        url_project = config["URLS"]["get_project_by_id"].replace("{project_id}", str(self.project_id))

        try:
            response = requests.get(url_project, headers=self.headers)

            if response.status_code == 200:
                project = response.json()
                self.project_name = project["name"]

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить данные по проекту: {str(e)}")

        self.label_current_project.setText(f"Задачи по проекту: {self.project_name} ")
        self.tasks_model = QtGui.QStandardItemModel()
        self.tasks_model.setHorizontalHeaderLabels(["ID", "Название", "Статус", "Приоритет", "Дедлайн", "Разработчик"])
        self.tableView_tasks.setModel(self.tasks_model)
        self.tableView_tasks.setColumnHidden(0, True)
        self.tableView_tasks.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableView_tasks.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        self.history_model = QtGui.QStandardItemModel()
        self.history_model.setHorizontalHeaderLabels(["Дата", "Поле", "Старое значение", "Новое значение"])
        self.tableView_tasks_history.setModel(self.history_model)
        self.tableView_tasks_history.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        self.comboBox.addItem("Все статусы", "")
        self.comboBox.addItem("Открыта", "open")
        self.comboBox.addItem("В работе", "in_progress")
        self.comboBox.addItem("Готова", "done")
        self.comboBox.addItem("Закрыта", "closed")

    def load_user_data(self):
        try:
            response = requests.get(config["URLS"]["current_user"], headers=self.headers)

            if response.status_code == 200:
                user_data = response.json()
                self.user_id = user_data["id"]
                self.user_role = user_data["role"]

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить данные пользователя: {str(e)}")

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

    def apply_filters(self):
        search_text = self.lineEdit.text().strip().lower()
        status_filter = self.comboBox.currentData()

        try:
            params = {"creator_id": self.user_id, "project_id": self.project_id}

            if status_filter:
                params["status"] = status_filter

            response = requests.get(config["URLS"]["get_tasks"], headers=self.headers, params=params)
            response.raise_for_status()

            self.tasks_model.setRowCount(0)

            tasks = response.json()

            if not tasks:
                self.tableView_tasks.setVisible(False)
                QMessageBox.information(self, "Информация", "У вас нет задач с выбранными параметрами!")
                return

            for task in tasks:
                if search_text:
                    task_text = (
                            task["title"].lower() +
                            self.get_status_text(task["status"]).lower() +
                            self.get_priority_text(task.get("priority")).lower() +
                            self.format_datetime(task.get("deadline")).lower() +
                            task.get("assignee", {}).get("full_name", "").lower() +
                            task.get("assignee", {}).get("username", "").lower()
                    )
                    if search_text not in task_text:
                        continue

                row = self.tasks_model.rowCount()
                self.tasks_model.insertRow(row)

                assignee = task.get("assignee", {})
                assignee_name = assignee.get("full_name", assignee.get("username", "Не назначен"))
                deadline = self.format_datetime(task["deadline"])

                self.tasks_model.setItem(row, 0, QtGui.QStandardItem(str(task["id"])))
                self.tasks_model.setItem(row, 1, QtGui.QStandardItem(task["title"]))
                self.tasks_model.setItem(row, 2, QtGui.QStandardItem(self.get_status_text(task["status"])))
                self.tasks_model.setItem(row, 3, QtGui.QStandardItem(self.get_priority_text(task.get("priority"))))
                self.tasks_model.setItem(row, 4, QtGui.QStandardItem(deadline))
                self.tasks_model.setItem(row, 5, QtGui.QStandardItem(assignee_name))

            self.tableView_tasks.resizeColumnsToContents()
            self.tableView_tasks.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            self.tableView_tasks.setVisible(True)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить задачи: {str(e)}")

    def load_task_history(self, task_id):
        try:
            url = config["URLS"]["task_history"].replace("{task_id}", str(task_id))
            response = requests.get(url, headers=self.headers)

            if response.status_code == 404:
                self.groupBox_task_history.setVisible(False)
                QMessageBox.information(self, "Информация", "Эта задача еще не имеет истории изменений!")
                return

            response.raise_for_status()
            history_data = response.json()
            self.history_model.setRowCount(0)

            if not history_data:
                self.groupBox_task_history.setVisible(False)
                QMessageBox.information(self, "Информация", "История изменений задачи пуста")
                return

            self.groupBox_task_history.setVisible(True)

            url = config["URLS"]["get_task_by_id"].replace("{task_id}", str(task_id))
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            task = response.json()
            self.task_description = task["description"]

            self.label_task_description.setVisible(True)
            self.label_task_description.setText(f"Описание задачи: {self.task_description}")

            for record in history_data:
                row = self.history_model.rowCount()
                self.history_model.insertRow(row)
                changed_at = self.format_datetime(record["changed_at"])

                field_name = self.get_field_name(record["changed_field"])
                old_value = self.format_field_value(record["changed_field"], record["old_value"])
                new_value = self.format_field_value(record["changed_field"], record["new_value"])

                self.history_model.setItem(row, 0, QtGui.QStandardItem(changed_at))
                self.history_model.setItem(row, 1, QtGui.QStandardItem(field_name))
                self.history_model.setItem(row, 2, QtGui.QStandardItem(old_value))
                self.history_model.setItem(row, 3, QtGui.QStandardItem(new_value))

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.groupBox_task_history.setVisible(False)
                QMessageBox.information(self, "Информация", "История изменений для этой задачи не найдена")
            else:
                self.groupBox_task_history.setVisible(False)
                QMessageBox.warning(self, "Ошибка", f"Ошибка сервера при загрузке истории: {str(e)}")

        except Exception as e:
            self.groupBox_task_history.setVisible(False)
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить историю: {str(e)}")

    def get_field_name(self, field):
        field_names = {
            "assigned_to": "Назначена на",
            "status": "Статус",
            "created": "Задача",
            "title": "Название",
            "description": "Описание",
            "deadline": "Срок выполнения",
            "priority": "Приоритет",
            "task_created": "Задача создана"
        }
        return field_names.get(field, field)

    def format_field_value(self, field, value):
        if value is None:
            return "Поле не изменялось"

        if value == "task_created":
            return "Задача создана"

        if field == "assigned_to":
            return self.get_developer_name(value)
        elif field == "status":
            return self.get_status_text(value)
        elif field == "created":
            return self.format_datetime(value) if value else "Не задано"

        return str(value)

    def get_developer_name(self, developer_id):
        if not developer_id:
            return "Не назначен"

        try:
            url = config["URLS"]["get_user_by_id"].replace("{user_id}", str(developer_id))
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                developer = response.json()
                return developer["username"]
        except:
            pass

        return str(developer_id)

    def on_task_selected(self, selected):
        if selected.indexes():
            selected_row = selected.indexes()[0].row()
            task_id = self.tasks_model.item(selected_row, 0).text()
            self.load_task_history(task_id)

    def reset_filters(self):
        self.comboBox.setCurrentIndex(0)
        self.lineEdit.clear()
        self.apply_filters()
        self.groupBox_task_history.setVisible(False)
        self.label_task_description.setVisible(False)

    def read_task(self):
        selected = self.tableView_tasks.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите задачу для просмотра")
            return

        task_id = self.tasks_model.item(selected[0].row(), 0).text()

        try:
            url = config["URLS"]["get_task_by_id"].replace("{task_id}", str(task_id))
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            task = response.json()
            self.task_description = task["description"]

            info_dialog = QtWidgets.QDialog(self)
            info_dialog.setWindowTitle(f"Информация о задаче")
            info_dialog.setMinimumSize(450, 350)

            layout = QtWidgets.QVBoxLayout(info_dialog)
            layout.setContentsMargins(15, 15, 15, 15)

            form_layout = QtWidgets.QFormLayout()
            form_layout.setVerticalSpacing(10)

            form_layout.addRow("Название:", QtWidgets.QLabel(task['title']))
            form_layout.addRow("Описание:", QtWidgets.QLabel(task.get('description', 'Нет описания')))
            form_layout.addRow("Статус:", QtWidgets.QLabel(self.get_status_text(task['status'])))
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

            close_btn = QtWidgets.QPushButton("Закрыть")
            close_btn.clicked.connect(info_dialog.close)
            layout.addWidget(close_btn, alignment=QtCore.Qt.AlignRight)

            info_dialog.setStyleSheet("""
                QDialog {
                    background-color: #f4f6f8;
                }
                QLabel {
                    color: #3c4043;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #4285f4;
                    color: #ffffff;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 6px 12px;
                    border: none;
                    min-width: 100px;
                    min-height: 30px;
                }
                QPushButton:hover {
                    background-color: #357ae8;
                }
            """)

            info_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить информацию о задаче: {str(e)}")

    def update_status_task(self):
        selected = self.tableView_tasks.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите задачу для изменения статуса")
            return

        try:
            task_id = self.tasks_model.item(selected[0].row(), 0).text()
            current_status_display = self.tasks_model.item(selected[0].row(), 2).text()

            status_mapping_reverse = {
                "Открыта": "open",
                "В работе": "in_progress",
                "Готова": "done",
                "Закрыта": "closed"
            }
            current_status = status_mapping_reverse.get(current_status_display)

            if current_status is None:
                raise ValueError("Неизвестный текущий статус задачи")

            valid_transactions_for_dev = {
                'open': ['in_progress'],
                'in_progress': ['done'],
            }

            valid_transitions = {
                'open': ['in_progress'],
                'in_progress': ['done'],
                'done': ['closed'],
                'closed': ['open']
            }

            if self.user_role == "team_lead":
                allowed_statuses = valid_transitions.get(current_status, [])
            else:
                allowed_statuses = valid_transactions_for_dev.get(current_status, [])

            if not allowed_statuses:
                QMessageBox.information(self, "Информация",
                                        f"Нет доступных переходов для текущего статуса '{current_status_display}'")
                return

            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Изменение статуса задачи")
            dialog.setMinimumWidth(360)

            layout = QtWidgets.QVBoxLayout(dialog)

            current_status_label = QtWidgets.QLabel(f"<b>Текущий статус:</b> {current_status_display}")
            layout.addWidget(current_status_label)
            current_status_label.setAlignment(QtCore.Qt.AlignCenter)

            status_combo = QtWidgets.QComboBox()
            for status in allowed_statuses:
                status_combo.addItem(self.get_status_text(status), status)
            status_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

            form_layout = QtWidgets.QFormLayout()
            form_layout.setLabelAlignment(Qt.AlignRight)
            form_layout.addRow("Новый статус:", status_combo)
            layout.addLayout(form_layout)

            button_layout = QtWidgets.QHBoxLayout()
            button_layout.addStretch()

            apply_button = QtWidgets.QPushButton("Применить")
            apply_button.setObjectName("pushButton_apply")
            apply_button.clicked.connect(dialog.accept)

            cancel_button = QtWidgets.QPushButton("Отменить")
            cancel_button.setObjectName("pushButton_cancel")
            cancel_button.clicked.connect(dialog.reject)

            button_layout.addWidget(cancel_button)
            button_layout.addWidget(apply_button)

            layout.addLayout(button_layout)

            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f4f6f8;
                    padding: 10px;
                }
                QLabel {
                    font-size: 13px;
                    margin-bottom: 6px;
                }
                QComboBox {
                    background-color: #ffffff;
                    border: 1px solid #d0d5d8;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 14px;
                    color: #202124;
                    min-height: 25px;
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
                new_status = status_combo.currentData()
                logger.info(f"Попытка изменить статус задачи {task_id} с '{current_status}' на '{new_status}'")

                url = config["URLS"]["update_task_status"].replace("{task_id}", str(task_id))
                response = requests.patch(url, headers=self.headers, json={"status": new_status})

                if response.status_code == 200:
                    logger.info(f"Статус задачи {task_id} успешно изменен на '{new_status}'")
                    QMessageBox.information(self, "Успех", "Статус задачи обновлен")
                    self.apply_filters()
                else:
                    error_msg = response.json().get("detail", "Неизвестная ошибка")
                    logger.error(f"Ошибка изменения статуса: {error_msg}")
                    QMessageBox.critical(self, "Ошибка", f"Не удалось изменить статус: {error_msg}")

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Ошибка сети при изменении статуса: {error_msg}")
            QMessageBox.critical(self, "Ошибка сети", f"Не удалось соединиться с сервером: {error_msg}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Неожиданная ошибка при изменении статуса: {error_msg}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {error_msg}")

    def reassign_task(self):
        selected = self.tableView_tasks.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите задачу для переназначения")
            return

        try:
            task_id = self.tasks_model.item(selected[0].row(), 0).text()

            url = config["URLS"]["get_users"]
            response = requests.get(url,headers=self.headers,params={"role": "developer"})
            response.raise_for_status()
            developers = response.json()

            if not developers:
                QMessageBox.warning(self, "Ошибка", "Нет доступных разработчиков для назначения")
                return

            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Переназначение задачи")
            dialog.setMinimumWidth(350)

            layout = QtWidgets.QVBoxLayout(dialog)
            grid_layout = QtWidgets.QGridLayout()

            current_assignee = self.tasks_model.item(selected[0].row(), 5).text()
            label_current = QtWidgets.QLabel("Текущий исполнитель:")
            value_current = QtWidgets.QLabel(current_assignee)
            grid_layout.addWidget(label_current, 0, 0)
            grid_layout.addWidget(value_current, 0, 1)

            label_new = QtWidgets.QLabel("Новый исполнитель:")
            developer_combo = QtWidgets.QComboBox()
            developer_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
            for dev in developers:
                display_name = dev.get('full_name', dev['username'])
                developer_combo.addItem(display_name, dev['id'])
            grid_layout.addWidget(label_new, 1, 0)
            grid_layout.addWidget(developer_combo, 1, 1)

            layout.addLayout(grid_layout)

            button_layout = QtWidgets.QHBoxLayout()
            button_layout.addStretch()

            button_cancel = QtWidgets.QPushButton("Отменить")
            button_cancel.setObjectName("pushButton_cancel")
            button_cancel.clicked.connect(dialog.reject)

            button_apply = QtWidgets.QPushButton("Применить")
            button_apply.setObjectName("pushButton_apply")
            button_apply.clicked.connect(dialog.accept)

            button_layout.addWidget(button_cancel)
            button_layout.addWidget(button_apply)
            layout.addLayout(button_layout)

            dialog.setStyleSheet("""
                QDialog {
                    background-color: #f4f6f8;
                    padding: 10px;
                }
                QLabel {
                    font-size: 13px;
                    margin-bottom: 5px;
                }
                QComboBox {
                    background-color: #ffffff;
                    border: 1px solid #d0d5d8;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 14px;
                    color: #202124;
                    min-height: 25px;
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
                new_assignee_id = developer_combo.currentData()

                logger.info(f"Попытка переназначить задачу {task_id} на пользователя {new_assignee_id}")

                url = config["URLS"]["reassign_task"].replace("{task_id}", str(task_id))
                response = requests.patch(
                    url,
                    headers=self.headers,
                    json={"new_assignee_id": new_assignee_id}
                )

                if response.status_code == 200:
                    logger.info(f"Задача {task_id} успешно переназначена")
                    QMessageBox.information(self, "Успех", "Исполнитель задачи обновлен")
                    self.apply_filters()
                else:
                    error_msg = response.json().get("detail", "Неизвестная ошибка")
                    logger.error(f"Ошибка переназначения: {error_msg}")
                    QMessageBox.critical(self, "Ошибка", f"Не удалось переназначить задачу: {error_msg}")

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Ошибка сети при переназначении: {error_msg}")
            QMessageBox.critical(self, "Ошибка сети", f"Не удалось соединиться с сервером: {error_msg}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Неожиданная ошибка при переназначении: {error_msg}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {error_msg}")

    def delete_task(self):
        selected = self.tableView_tasks.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Ошибка", "Выберите задачу для удаления")
            return

        try:
            task_id = self.tasks_model.item(selected[0].row(), 0).text()
            task_title = self.tasks_model.item(selected[0].row(), 1).text()

            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("Подтверждение удаления")
            dialog.setMinimumWidth(400)

            layout = QtWidgets.QVBoxLayout(dialog)

            label = QtWidgets.QLabel(f'Вы точно хотите удалить задачу "<b>{task_title}</b>" (ID: {task_id})?')
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
                logger.info(f"Попытка удаления задачи {task_id}")

                url = config["URLS"]["delete_task"].replace("{task_id}", str(task_id))
                response = requests.delete(url, headers=self.headers, json={"task_id": int(task_id)})

                if response.status_code == 200:
                    logger.info(f"Задача {task_id} успешно удалена")
                    QMessageBox.information(self, "Успех", "Задача успешно удалена")
                    self.apply_filters()
                else:
                    error_msg = response.json().get("message", "Неизвестная ошибка")
                    logger.error(f"Ошибка удаления: {error_msg}")
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить задачу: {error_msg}")

            else:
                logger.info(f"Удаление задачи {task_id} отменено пользователем")

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            logger.error(f"Ошибка сети при удалении: {error_msg}")
            QMessageBox.critical(self, "Ошибка сети", f"Не удалось соединиться с сервером: {error_msg}")


