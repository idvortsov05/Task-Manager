''' Для запуска программы необходимо использовать абсолютные импорты, так как программа запускается из корневой директории'''
import notificatons # ДЛЯ ЗАПУСКА ПРОГРАММЫ
import models, schemas # ДЛЯ ЗАПУСКА ПРОГРАММЫ
from config.config_server import get_config

''' Для тестов необходимо использовать относительные импорты, так как они запускаются из директории тестов'''
# from ..http_server import models, schemas # ДЛЯ ТЕСТОВ
# import notificatons # ДЛЯ ТЕСТОВ
# from server.http_server.config.config_server import get_config # ДЛЯ ТЕСТОВ

import joblib
import hashlib
from sqlalchemy import or_
from functools import cache
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext

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

    if db_user:
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

    return None

def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)

    if db_user:
        db.delete(db_user)
        db.commit()
        return True

    return False

# ===== CRUD для проектов =====
def create_project(db: Session, project: schemas.ProjectCreate) -> models.Project:
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def get_project(db: Session, project_id: int) -> models.Project:
    return db.query(models.Project).get(project_id)

def get_projects(db: Session, team_lead_id: Optional[int] = None, skip: int = 0, limit: int = 100, query: Optional[str] = None) -> list[models.Project]:
    q = db.query(models.Project)

    if team_lead_id is not None:
        q = q.filter(models.Project.team_lead_id == team_lead_id)

    if query:
        search = f"%{query.lower()}%"
        q = q.filter(or_(models.Project.name.ilike(search), models.Project.description.ilike(search)))

    return q.offset(skip).limit(limit).all()


def delete_project(db: Session, project_id: int, current_user: models.User) -> bool:
    db_project = get_project(db, project_id)

    if not db_project or current_user.role != "team_lead" or db_project.team_lead_id != current_user.id:
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
    priority = calc_priority(input_text)
    project = get_project(db, task.project_id)

    db_task = models.Task(**task.model_dump(exclude={"priority"}), created_by=creator_id, priority=priority)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    db_history = models.TaskHistory(
        task_id=db_task.id,
        changed_by=creator_id,
        changed_field="created",
        old_value=str(None),
        new_value="task_created"
    )
    db.add(db_history)

    db_history_status = models.TaskHistory(
        task_id=db_task.id,
        changed_by=creator_id,
        changed_field="status",
        old_value=str(None),
        new_value="open"
    )
    db.add(db_history_status)

    if task.assigned_to:
        db_history_assign = models.TaskHistory(
            task_id=db_task.id,
            changed_by=creator_id,
            changed_field="assigned_to",
            old_value=str(None),
            new_value=str(task.assigned_to)
        )
        db.add(db_history_assign)

    db.commit()

    '''Необходимо комментировать при выполнении тестов, так как выполняется реальная отправка уведомления на почту'''
    assigned_user = db.query(models.User).get(task.assigned_to)
    if assigned_user:
        notificatons.notify_user_about_task(db, assigned_user, db_task, project)
    return db_task

def get_task(db: Session, task_id: int) -> models.Task:
    return db.query(models.Task).get(task_id)

def get_filtered_tasks(
    db: Session,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[int] = None,
    status: Optional[str] = None,
    project_id: Optional[int] = None,
) -> list[models.Task]:
    query = db.query(models.Task)

    if title:
        query = query.filter(models.Task.title.ilike(f"%{title}%"))
    if description:
        query = query.filter(models.Task.description.ilike(f"%{description}%"))
    if priority is not None:
        query = query.filter(models.Task.priority == priority)
    if status:
        query = query.filter(models.Task.status == status)
    if project_id is not None:
        query = query.filter(models.Task.project_id == project_id)

    return query.all()

def get_user_related_tasks(
        db: Session,
        user_id: int,
        user_role: str,
        title: Optional[str] = None,
        status: Optional[str] = None,
        project_id: Optional[int] = None
) -> list[models.Task]:
    query = db.query(models.Task)

    if user_role == "team_lead":
        query = query.filter(models.Task.created_by == user_id)
    else:
        query = query.filter(models.Task.assigned_to == user_id)

    if title:
        query = query.filter(models.Task.title.ilike(f"%{title}%"))
    if status:
        query = query.filter(models.Task.status == status)
    if project_id is not None:
        query = query.filter(models.Task.project_id == project_id)

    return query.order_by(models.Task.created_by.desc()).all()

def get_tasks_by_project(db: Session, project_id: int) -> list[models.Task]:
    return db.query(models.Task).filter(models.Task.project_id == project_id).order_by(models.Task.status).all()

def get_user_tasks(db: Session, user_id: int) -> list[models.Task]:
    return db.query(models.Task).filter(models.Task.assigned_to == user_id).order_by(models.Task.status).all()

def update_task_status(db: Session, task_id: int, new_status: str, changed_by_id: int) -> models.Task:
    db_task = get_task(db, task_id)
    if not db_task:
        return None

    valid_transitions ={
        'open': ['in_progress'],
        'in_progress': ['done'],
        'done': ['closed'],
        'closed': ['open']
    }

    if new_status not in valid_transitions.get(db_task.status, []):
        raise ValueError(f"Invalid status transition from {db_task.status} to {new_status}")

    db_history = models.TaskHistory(
        task_id=task_id,
        changed_by=changed_by_id,
        changed_field="status",
        old_value=db_task.status,
        new_value=new_status
    )
    db.add(db_history)

    db_task.status = new_status
    db.commit()
    db.refresh(db_task)
    return db_task

def reassign_task(db: Session,task_id: int,new_assignee_id: int,changed_by_id: int) -> models.Task:
    db_task = get_task(db, task_id)
    if not db_task:
        return None

    new_assignee = db.query(models.User).get(new_assignee_id)
    if not new_assignee:
        raise ValueError("New assignee not found")

    db_history = models.TaskHistory(
        task_id=task_id,
        changed_by=changed_by_id,
        changed_field="assigned_to",
        old_value=str(db_task.assigned_to),
        new_value=str(new_assignee_id)
    )
    db.add(db_history)

    db_task.assigned_to = new_assignee_id
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int, deleted_by_id: int) -> bool:
    db_task = get_task(db, task_id)
    if not db_task:
        return False

    db_task_data = models.TaskHistory(
        task_id=task_id,
        changed_by=deleted_by_id,
        changed_field="task_data",
        old_value=f"Title: {db_task.title}, Desc: {db_task.description}",
        new_value=str(None)
    )
    db.add(db_task_data)

    db.flush()
    db.delete(db_task)
    db.commit()
    return True

# ==== CRUD для истории задач ====
def get_task_history_by_user(db: Session, user_id: int) -> list[models.TaskHistory]:
    return db.query(models.TaskHistory).join(models.Task).filter(or_(models.Task.assigned_to == user_id, models.TaskHistory.changed_by == user_id)).order_by(models.TaskHistory.changed_at.desc()).all()

def get_task_history_by_task_id(db: Session, user_id: int, task_id: int) -> list[models.TaskHistory]:
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        return []

    if task.assigned_to != user_id:
        history = db.query(models.TaskHistory).filter(
            models.TaskHistory.task_id == task_id,
            models.TaskHistory.changed_by == user_id
        ).order_by(models.TaskHistory.changed_at.desc()).all()
        return history

    return db.query(models.TaskHistory).filter(models.TaskHistory.task_id == task_id).order_by(models.TaskHistory.changed_at.desc()).all()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password
