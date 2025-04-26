from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    image = Column(Text, nullable=True)

    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.created_by")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assigned_to")
    notifications = relationship("Notification", back_populates="user")

    __table_args__ = (
        CheckConstraint("role IN ('team_lead', 'developer')", name='check_user_role'),
    )


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False)

    tasks = relationship("Task", back_populates="project")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed')", name='check_project_status'),
    )


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False)
    deadline = Column(DateTime)
    priority = Column(Float)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    assigned_to = Column(Integer, ForeignKey('users.id'), nullable=False)

    project = relationship("Project", back_populates="tasks")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tasks")
    history = relationship("TaskHistory", back_populates="task")

    __table_args__ = (
        CheckConstraint("status IN ('open', 'in_progress', 'done', 'closed')", name='check_task_status'),
    )


class TaskHistory(Base):
    __tablename__ = 'task_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    changed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    changed_field = Column(String(50), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_at = Column(DateTime, server_default=func.now())

    task = relationship("Task", back_populates="history")
    user = relationship("User", foreign_keys=[changed_by])


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications", foreign_keys=[user_id])