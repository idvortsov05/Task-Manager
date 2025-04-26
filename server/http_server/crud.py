import hashlib
from functools import cache
from config.config_server import get_config

from sqlalchemy.orm import Session
import models, schemas # ДЛЯ ЗАПУСКА ПРОГРАММЫ
# from ..http_server import models, schemas # ДЛЯ ТЕСТОВ
from passlib.context import CryptContext

import joblib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

config = get_config("server/http_server/config/config.ini")

# ===== CRUD для пользователей =====
def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        password_hash=hash_password(user.password),
        role=user.role,
        image=user.image
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int) -> models.User:
    return db.query(models.User).get(user_id)

def get_user_by_username(db: Session, username: str) -> models.User:
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str) -> models.User:
   return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> models.User:
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)

    if "password" in update_data:
        password_hash = update_data.pop("password")
        if len(password_hash) != 64 or not all(c in "0123456789abcdef" for c in password_hash):
            raise ValueError("Invalid password hash format. Expected SHA-256 hex digest")
        update_data["password_hash"] = password_hash

    for key, value in update_data.items():
        if value is not None:
            setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    db.delete(db_user)
    db.commit()
    return True


# ===== CRUD для проектов =====
def create_project(db: Session, project: schemas.ProjectCreate) -> models.Project:
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project(db: Session, project_id: int) -> models.Project:
    return db.query(models.Project).get(project_id)


def get_projects(db: Session, skip: int = 0, limit: int = 100) -> list[models.Project]:
    return db.query(models.Project).offset(skip).limit(limit).all()


def delete_project(db: Session, project_id: int) -> bool:
    db_project = get_project(db, project_id)
    if not db_project:
        return False
    db.delete(db_project)
    db.commit()
    return True


@cache
def get_model():
    return joblib.load(config["model"]["model_path"])

def calc_priority(description: str) -> float:
    model = get_model()
    priority = model.predict([description])[0]
    return max(0.0, min(1.0, float(priority)))

# ===== CRUD для задач =====
def create_task(db: Session, task: schemas.TaskCreate, creator_id: int) -> models.Task:
    input_text = f"{task.title} {task.description}"
    db_task = models.Task(
        **task.model_dump(exclude={"priority"}),
        created_by=creator_id,
        priority=calc_priority(input_text)
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task(db: Session, task_id: int) -> models.Task:
    return db.query(models.Task).get(task_id)


def get_tasks_by_project(db: Session, project_id: int) -> list[models.Task]:
    return db.query(models.Task).filter(models.Task.project_id == project_id).order_by(models.Task.status).all()


def get_user_tasks(db: Session, user_id: int) -> list[models.Task]:
    return db.query(models.Task).filter(models.Task.assigned_to == user_id).order_by(models.Task.status).all()


def update_task_status(db: Session,task_id: int,new_status: str,changed_by_id: int) -> models.Task:
    db_task = get_task(db, task_id)
    if not db_task:
        return None

    valid_transitions ={
        'open': ['in_progress'],
        'in_progress': ['done'],
        'done': ['closed'],
        'closed': []
    }

    if new_status not in valid_transitions.get(db_task.status, []):
        raise ValueError(f"Invalid status transition from {db_task.status} to {new_status}")

    db_task.status = new_status
    db.commit()
    db.refresh(db_task)
    return db_task


def reassign_task(db: Session,task_id: int,new_assignee_id: int,changed_by_id: int) -> models.Task:
    db_task = get_task(db, task_id)
    if not db_task:
        return None

    db_task.assigned_to = new_assignee_id
    db.commit()
    db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int) -> bool:
    db_task = get_task(db, task_id)
    if not db_task:
        return False
    db.delete(db_task)
    db.commit()
    return True

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password
