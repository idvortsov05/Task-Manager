from config.config_server import get_config
from logger.logger_server import get_logger

from datetime import datetime
import models

import smtplib
from sqlalchemy.orm import Session
from models import Notification, User
from email.message import EmailMessage

config = get_config("server/http_server/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("server", LOGGER_CONFIG_PATH)

def build_notification_message(task: models.Task, project: models.Project, user: User) -> str:
    priority = None
    important = None
    formatted_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    deadline = task.deadline.strftime("%d.%m.%Y %H:%M")

    if task.priority <= 0.35:
        priority = "низкий🟢"
        important = "прошу приступить к выполнению задачи в свободное время!"
    elif 0.35 < task.priority <= 0.75:
        priority = "средний🟡"
        important =  "приступите к выполнению задачи в ближайшее время!"
    elif 0.75 < task.priority <= 0.99:
        priority = "высокий🔴"
        important = "начните выполнение задачи немедленно!"

    message =  (f"Здравствуйте, {user.full_name}! \n"
                f"На Вас была назначена задача - '{task.title}', в проекте - '{project.name}' в {formatted_time}! \n"
                f"Краткое описание поставленной задачи: {task.description} \n"
                f"Приоритет данной задачи - {priority}, {important} \n"
                f"Дедлайн для выполнения поставленной задачи: {deadline}\n"
                f"С уважением, руководитель проекта!")

    return message

def notify_user_about_task(db: Session, user: User, task: models.Task, project: models.Project) -> None:
    message = build_notification_message(task, project, user)

    send_email(to=user.email, subject="Новая задача назначена", body=message)

    db_notification = Notification(user_id=user.id, message=message, sent_at=datetime.now())
    db.add(db_notification)
    db.commit()

def send_email(to: str, subject: str, body: str):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = config["email"]["email_from"]
    msg['To'] = to
    msg.set_content(body)

    try:
        with smtplib.SMTP(config["email"]["smtp_server"], int(config["email"]["smtp_port"])) as server:
            server.starttls()
            server.login(config["email"]["email_login"], config["email"]["email_password"])
            server.send_message(msg)
            logger.info(f"Email sent to {to}")
    except smtplib.SMTPException as e:
        logger.error(f"Failed to send email to {to}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while sending email to {to}: {e}")
