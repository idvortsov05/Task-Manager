import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from ..http_server import crud
from ..http_server.models import User, Project, Task
from ..http_server.schemas import UserCreate, UserUpdate, ProjectCreate, TaskCreate


# ===== Тесты для пользователей =====
def test_create_user():
    mock_db = Mock(spec=Session)

    user_data = UserCreate(
        username="testuser",
        full_name="Test User",
        email="test@example.com",
        password="password123",
        role="user",
        image="image.jpg"
    )

    mock_user = User(

        username="testuser",
        full_name="Test User",
        email="test@example.com",
        password_hash=crud.hash_password("password123"),
        role="developer",
        image="image.jpg"
    )

    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    with patch('server.http_server.crud.models.User', return_value=mock_user):
        result = crud.create_user(mock_db, user_data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert isinstance(result, User)
    assert result.username == "testuser"
    assert len(result.password_hash) == 64


def test_get_user():
    mock_db = Mock(spec=Session)

    mock_user = User(id=1, username="testuser")
    mock_db.query().get.return_value = mock_user

    result = crud.get_user(mock_db, 1)

    assert result == mock_user
    assert result.id == 1


def test_get_user_by_username():
    mock_db = Mock(spec=Session)

    mock_user = User(username="testuser")
    mock_db.query().filter().first.return_value = mock_user

    result = crud.get_user_by_username(mock_db, "testuser")

    assert result == mock_user
    assert result.username == "testuser"


def test_update_user():
    mock_db = Mock(spec=Session)

    existing_user = User(
        id=1,
        username="olduser",
        full_name="Old Name",
        email="old@example.com"
    )

    update_data = UserUpdate(
        full_name="New Name",
        email="new@example.com"
    )

    mock_db.query().get.return_value = existing_user

    result = crud.update_user(mock_db, 1, update_data)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert result.full_name == "New Name"
    assert result.email == "new@example.com"
    assert result.username == "olduser"  # Не изменялось


def test_delete_user():
    mock_db = Mock(spec=Session)

    mock_user = User(id=1)
    mock_db.query().get.return_value = mock_user

    result = crud.delete_user(mock_db, 1)

    mock_db.delete.assert_called_once_with(mock_user)
    mock_db.commit.assert_called_once()
    assert result is True


# ===== Тесты для проектов =====
def test_create_project():
    mock_db = Mock(spec=Session)

    project_data = ProjectCreate(
        name="Test Project",
        description="Test Description",
        status = "active",
        team_lead_id=1
    )

    mock_project = Project(id=1, name="Test Project", status = "active", description="Test Description")
    mock_db.query().get.return_value = mock_project
    with patch('server.http_server.crud.models.Project', return_value=mock_project):
        result = crud.create_project(mock_db, project_data)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert isinstance(result, Project)
    assert result.name == "Test Project"


def test_get_project():
    mock_db = Mock(spec=Session)

    mock_project = Project(id=1)
    mock_db.query().get.return_value = mock_project

    result = crud.get_project(mock_db, 1)

    assert result == mock_project


# ===== Тесты для задач =====
def test_create_task():
    mock_db = Mock(spec=Session)
    task_data = TaskCreate(
        title="Test Task",
        description="Test Description",
        project_id=1,
        assigned_to=1,
        status="open",
        priority=1,
    )
    mock_task = Task(id=1, title="Test Task", created_by=1)

    with patch('server.http_server.crud.models.Task', return_value=mock_task), \
         patch('server.http_server.crud.calc_priority', return_value=0.5):
        result = crud.create_task(mock_db, task_data, creator_id=1)
        assert result is not None

    assert mock_db.add.call_count == 4
    assert mock_db.commit.call_count == 2
    mock_db.refresh.assert_called_once()

    assert isinstance(result, Task)
    assert result.title == "Test Task"
    assert result.created_by == 1


def test_update_task_status():
    mock_db = Mock(spec=Session)

    mock_task = Task(id=1, status="open")
    mock_db.query().get.return_value = mock_task

    result = crud.update_task_status(mock_db, 1, "in_progress", 2)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert result.status == "in_progress"

def test_reassign_task():
    mock_db = Mock(spec=Session)

    mock_task = Task(id=1, assigned_to=1)
    mock_db.query().get.return_value = mock_task

    result = crud.reassign_task(mock_db, 1, 2, 3)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()

    assert result.assigned_to == 2


def test_delete_task():
    mock_db = Mock(spec=Session)

    mock_task = Task(id=1)
    mock_db.query().get.return_value = mock_task

    result = crud.delete_task(mock_db, 1, deleted_by_id=1)

    mock_db.delete.assert_called_once_with(mock_task)
    mock_db.commit.assert_called_once()
    assert result is True
