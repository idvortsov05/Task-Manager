from config.config_server import get_config
from logger.logger_server import get_logger

from database import get_db
import crud, models, schemas
from auth import (authenticate_user, create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES)

from typing import Optional
from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

config = get_config("server/http_server/config/config.ini")
LOGGER_CONFIG_PATH = config["logger"]["LOGGER_CONFIG_PATH"]
logger = get_logger("server", LOGGER_CONFIG_PATH)

router = APIRouter()

# ===== Аутентификация =====
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/register", response_model=schemas.UserPublic)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Registering user with username {user.username} started")
    if crud.get_user_by_username(db, user.username):
        logger.error(f"User with username -  {user.username} already exists")
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    if crud.get_user_by_email(db, user.email):
        logger.error(f"User with email -  {user.email} already exists")
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    logger.info(f"Registering user successful {user.username}")
    return crud.create_user(db=db, user=user)


@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logger.info(f"Logging in with username {form_data.username} started")
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.error(f"User with username {form_data.username} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    logger.info(f"Logging in with token {access_token} finished")
    return {"access_token": access_token, "token_type": "bearer"}


# ===== Пользователи =====
@router.get("/users/me", response_model=schemas.UserPublic)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    logger.info(f"Reading user with username {current_user.username}")
    return current_user


@router.get("/users/{user_id}", response_model=schemas.UserPublic)
def read_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    logger.info(f"Reading user with username {user_id} started")
    if current_user.id != user_id and current_user.role != "team_lead":
        logger.error(f"User with id {user_id} is not a team lead")
        raise HTTPException(status_code=403, detail="Not enough permissions")

    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        logger.error(f"User with id {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.get("/users/", response_model=list[schemas.UserPublic])
def get_users(role: str = None, db: Session = Depends(get_db),current_user: models.User = Depends(get_current_user)):
    query = db.query(models.User)

    if role:
        query = query.filter(models.User.role == role)

    users = query.all()
    return users


@router.put("/users/{user_id}", response_model=schemas.UserPublic)
def update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.id != user_id and current_user.role != "team_lead":
        logger.error(f"User with id {user_id} is not a team lead")
        raise HTTPException(status_code=403, detail="Not enough permissions")

    updated_user = crud.update_user(db, user_id, user_update)
    if updated_user is None:
        logger.error(f"User with id {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user


# ===== Проекты =====
@router.post("/projects/", response_model=schemas.ProjectInDB)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db),current_user: models.User = Depends(get_current_user)):
    if current_user.role != "team_lead":
        raise HTTPException(status_code=403, detail="Only team leads can create projects")

    return crud.create_project(db=db, project=project)

@router.get("/projects/", response_model=list[schemas.ProjectInDB])
def read_projects(skip: int = 0, limit: int = 100, query: Optional[str] = None, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "team_lead":
        return crud.get_projects(db, team_lead_id=current_user.id, skip=skip, limit=limit, query=query)
    return crud.get_projects(db, skip=skip, limit=limit, query=query)

@router.get("/projects/{project_id}", response_model=schemas.ProjectInDB)
def read_project(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == "team_lead" and db_project.team_lead_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this project")

    return db_project


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        success = crud.delete_project(db, project_id, current_user)
    except HTTPException as e:
        raise e

    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"message": "Project deleted"}


# ===== Задачи =====
@router.post("/tasks/", response_model=schemas.TaskPublic)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    assigned_user = crud.get_user(db, task.assigned_to)
    if not assigned_user:
        logger.error(f"User with username {assigned_user.username} not found")
        raise HTTPException(status_code=400, detail="Assigned user not found")

    project = crud.get_project(db, task.project_id)
    if not project:
        logger.error(f"Project with id {task.project_id} not found")
        raise HTTPException(status_code=400, detail="Project not found")

    return crud.create_task(db=db, task=task, creator_id=current_user.id)


@router.get("/tasks/", response_model=list[schemas.TaskPublic])
def get_tasks(
    title: Optional[str] = Query(None, description="Поиск по названию"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    project_id: Optional[int] = Query(None, description="Фильтр по проекту"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_user_related_tasks(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role,
        title=title,
        status=status,
        project_id=project_id
    )

@router.get("/tasks/{task_id}", response_model=schemas.TaskPublic)
def read_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_task = crud.get_task(db, task_id=task_id)
    if db_task is None:
        logger.error(f"Task with id {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.assigned_to != current_user.id and current_user.role != "team_lead":
        logger.error(f"User with username {current_user.username} cannot read task")
        raise HTTPException(status_code=403, detail="Not enough permissions")

    logger.info(f"Reading task with id {task_id} finished")
    return db_task


@router.patch("/tasks/{task_id}/status", response_model=schemas.TaskPublic)
def update_task_status(
        task_id: int,
        status_update: schemas.TaskStatusUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    try:
        db_task = crud.update_task_status(
            db=db,
            task_id=task_id,
            new_status=status_update.status,
            changed_by_id=current_user.id
        )
        if not db_task:
            logger.error(f"Task with id {task_id} not found")
            raise HTTPException(status_code=404, detail="Task not found")

        logger.info(f"Task with id {task_id} updated")
        return db_task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/tasks/{task_id}/assign", response_model=schemas.TaskPublic)
def reassign_task(
        task_id: int,
        assign_data: schemas.TaskAssignUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "team_lead":
        logger.error(f"User with username {current_user.username} cannot reassign task")
        raise HTTPException(status_code=403, detail="Only team leads can reassign tasks")

    new_assignee = crud.get_user(db, assign_data.new_assignee_id)
    if not new_assignee or new_assignee.role != "developer":
        logger.error(f"User with id {assign_data.new_assignee_id} not found or he is not a developer")
        raise HTTPException(status_code=400, detail="Invalid assignee")

    db_task = crud.reassign_task(
        db=db,
        task_id=task_id,
        new_assignee_id=assign_data.new_assignee_id,
        changed_by_id=current_user.id
    )
    if not db_task:
        logger.error(f"Task with id {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    logger.info(f"Reassigning task with id {task_id} finished")
    return db_task


@router.delete("/tasks/{task_id}")
def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "team_lead":
        logger.error(f"User with username {current_user.username} cannot delete task")
        raise HTTPException(status_code=403, detail="Only team leads can delete tasks")

    if not crud.delete_task(db, task_id=task_id, deleted_by_id=current_user.id):
        logger.info(f"Task id = {task_id}")
        logger.error(f"Task with id {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")

    logger.info(f"Deleting task with id {task_id} finished")
    return {"message": "Task deleted"}

# ==== История задач ====
@router.get("/task-history/{task_id}", response_model=list[schemas.TaskHistoryInDB])
def get_task_history(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    history = crud.get_task_history_by_task_id(db, current_user.id, task_id)
    if not history:
        raise HTTPException(status_code=404, detail="Task history not found")
    return history







