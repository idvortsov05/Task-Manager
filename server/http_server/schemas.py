from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# Базовые классы
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )

# Пользователи
class UserBase(BaseSchema):
    username: str
    full_name: str
    email: str
    role: str
    image: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseSchema):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    image: Optional[str] = None

class UserInDB(UserBase):
    id: int
    password_hash: str

class UserPublic(UserBase):
    id: int

# Проекты
class ProjectBase(BaseSchema):
    name: str
    description: Optional[str] = None
    status: str

class ProjectCreate(ProjectBase):
    pass

class ProjectInDB(ProjectBase):
    id: int

# Задачи
class TaskBase(BaseSchema):
    title: str
    description: Optional[str] = None
    status: str
    deadline: Optional[datetime] = None
    priority: float
    project_id: int
    assigned_to: int

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[float] = None
    assigned_to: Optional[int] = None

class TaskInDB(TaskBase):
    id: int
    project_id: int
    created_by: int
    assigned_to: int

class TaskPublic(TaskInDB):
    creator: UserPublic
    assignee: UserPublic
    project: ProjectInDB

# История задач
class TaskHistoryBase(BaseSchema):
    changed_field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None

class TaskHistoryInDB(TaskHistoryBase):
    id: int
    task_id: int
    changed_by: int
    changed_at: datetime

# Уведомления
class NotificationBase(BaseSchema):
    message: str

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationInDB(NotificationBase):
    id: int
    user_id: int
    sent_at: datetime

# Ответы API
class MessageResponse(BaseSchema):
    message: str

class TokenResponse(BaseSchema):
    access_token: str
    token_type: str

# Токены
class TokenData(BaseModel):
    username: str | None = None

class TaskStatusUpdate(BaseModel):
    status: str

class TaskAssignUpdate(BaseModel):
    new_assignee_id: int

class PredictRequest(BaseSchema):
    description: str
    project_id: int


TaskPublic.model_rebuild()

