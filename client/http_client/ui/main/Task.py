from PyQt5 import uic
from datetime import datetime
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSignal, Qt


class TaskWidget(QDialog):
    taskClicked = pyqtSignal(int)

    def __init__(self, task):
        super().__init__()

        self.task_id = task['id']
        self.title = task['title']
        self.assignee = task['assignee']['full_name']
        self.priority = task['priority']
        self.deadline = task['deadline']

        uic.loadUi('client/http_client/ui/main/TaskWidget.ui', self)

        with open('client/http_client/ui/styles/task.qss', 'r') as f:
            self.setStyleSheet(f.read())

        self.setup_task_info()
        self.setMouseTracking(True)

    def setup_task_info(self):
        self.label_title.setText(f"📌Название: {self.title}")
        self.label_assignee.setText(f"👤Разработчик: {self.assignee}")
        self.label_priority.setText(f"Приоритет: {self.get_priority_text(self.priority)}")
        self.label_deadline.setText(f"📅Дедлайн: {self.format_datetime(self.deadline)}")

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.taskClicked.emit(self.task_id)
