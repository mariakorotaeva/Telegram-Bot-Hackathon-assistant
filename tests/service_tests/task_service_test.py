import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
import uuid
from services.task_service import TaskService
from models.task_model import Task


@pytest.fixture
def mock_task_repository():
    return AsyncMock()


@pytest.fixture
def task_service(mock_task_repository):
    with patch('services.task_service.TaskRepository', return_value=mock_task_repository):
        return TaskService()


@pytest.fixture
def sample_task_data():
    return {
        "id": 1,
        "telegram_id": "task_1703250000_abc123def",
        "title": "Test Task",
        "description": "Test Description",
        "assigned_to": "volunteer123",
        "created_by": "organizer456",
        "is_active": True,
        "is_completed": False
    }


class TestGetTaskById:
    # Тест для получения задачи по ID
    @pytest.mark.asyncio
    async def test_get_task_by_id_success(self, task_service, mock_task_repository):
        mock_task = Mock(spec=Task)
        mock_task.id = 1
        mock_task.title = "Test Task"

        mock_task_repository.get_by_id.return_value = mock_task

        result = await task_service.get_task_by_id(1)

        assert result == mock_task
        mock_task_repository.get_by_id.assert_called_once_with(1)

    # Тест для получения несуществующей задачи по ID
    @pytest.mark.asyncio
    async def test_get_task_by_id_not_found(self, task_service, mock_task_repository):
        mock_task_repository.get_by_id.return_value = None

        result = await task_service.get_task_by_id(999)

        assert result is None
        mock_task_repository.get_by_id.assert_called_once_with(999)


class TestGetTaskByTelegramId:
    # Тест для получения задачи по telegram_id
    @pytest.mark.asyncio
    async def test_get_task_by_telegram_id_success(self, task_service, mock_task_repository):
        mock_task = Mock()
        mock_task.telegram_id = "task_123"
        mock_task.title = "Test Task"

        mock_task_repository.get_by_telegram_id.return_value = mock_task

        result = await task_service.get_task_by_telegram_id("task_123")

        assert result == mock_task
        mock_task_repository.get_by_telegram_id.assert_called_once_with("task_123")

    # Тест для получения несуществующей задачи по telegram_id
    @pytest.mark.asyncio
    async def test_get_task_by_telegram_id_not_found(self, task_service, mock_task_repository):
        mock_task_repository.get_by_telegram_id.return_value = None

        result = await task_service.get_task_by_telegram_id("task_nonexistent")

        assert result is None
        mock_task_repository.get_by_telegram_id.assert_called_once_with("task_nonexistent")


class TestUpdateTask:
    # Тест для успешного обновления задачи
    @pytest.mark.asyncio
    async def test_update_task_success(self, task_service, mock_task_repository):
        mock_task = Mock()
        mock_task.telegram_id = "task_123"
        mock_task.title = "Old Title"
        mock_task.description = "Old Description"
        mock_task.assigned_to = "old_volunteer"

        mock_task_repository.get_by_telegram_id.return_value = mock_task

        updated_task = Mock()
        mock_task_repository.update.return_value = updated_task

        result = await task_service.update_task(
            telegram_id="task_123",
            title="New Title",
            description="New Description",
            assigned_to="new_volunteer"
        )

        assert result == updated_task
        assert mock_task.title == "New Title"
        assert mock_task.description == "New Description"
        assert mock_task.assigned_to == "new_volunteer"
        mock_task_repository.get_by_telegram_id.assert_called_once_with("task_123")
        mock_task_repository.update.assert_called_once_with(mock_task)


    # Тест для частичного обновления задачи
    @pytest.mark.asyncio
    async def test_update_task_partial(self, task_service, mock_task_repository):
        mock_task = Mock()
        mock_task.telegram_id = "task_123"
        mock_task.title = "Old Title"
        mock_task.description = "Old Description"

        mock_task_repository.get_by_telegram_id.return_value = mock_task
        mock_task_repository.update.return_value = mock_task

        result = await task_service.update_task(
            telegram_id="task_123",
            title="New Title"
        )

        assert result == mock_task
        assert mock_task.title == "New Title"
        assert mock_task.description == "Old Description"
        mock_task_repository.update.assert_called_once_with(mock_task)

    # Тест для обновления задачи без изменений
    @pytest.mark.asyncio
    async def test_update_task_no_changes(self, task_service, mock_task_repository):
        mock_task = Mock()
        mock_task.telegram_id = "task_123"

        mock_task_repository.get_by_telegram_id.return_value = mock_task
        mock_task_repository.update.return_value = mock_task

        result = await task_service.update_task(telegram_id="task_123")

        assert result == mock_task
        mock_task_repository.update.assert_called_once_with(mock_task)


class TestDeleteTask:
    # Тест для успешного удаления задачи
    @pytest.mark.asyncio
    async def test_delete_task_success(self, task_service, mock_task_repository):
        mock_task_repository.delete.return_value = True

        result = await task_service.delete_task("task_123")

        assert result is True
        mock_task_repository.delete.assert_called_once_with("task_123")

    # Тест для неудачного удаления задачи
    @pytest.mark.asyncio
    async def test_delete_task_failure(self, task_service, mock_task_repository):
        mock_task_repository.delete.return_value = False

        result = await task_service.delete_task("task_123")

        assert result is False
        mock_task_repository.delete.assert_called_once_with("task_123")


class TestGetAllTasks:
    # Тест для получения всех задач
    @pytest.mark.asyncio
    async def test_get_all_tasks_with_active(self, task_service, mock_task_repository):
        task1 = Mock(id=1, title="Task 1")
        task2 = Mock(id=2, title="Task 2")

        mock_task_repository.get_all.return_value = [task1, task2]

        result = await task_service.get_all_tasks(only_active=True)

        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2
        mock_task_repository.get_all.assert_called_once_with(only_active=True)

    # Тест для получения всех задач включая неактивные
    @pytest.mark.asyncio
    async def test_get_all_tasks_including_inactive(self, task_service, mock_task_repository):
        task1 = Mock(id=1, title="Active Task")
        task2 = Mock(id=2, title="Inactive Task")

        mock_task_repository.get_all.return_value = [task1, task2]

        result = await task_service.get_all_tasks(only_active=False)

        assert len(result) == 2
        mock_task_repository.get_all.assert_called_once_with(only_active=False)



class TestGetOrganizerTasks:
    # Тест для получения задач организатора
    @pytest.mark.asyncio
    async def test_get_organizer_tasks_success(self, task_service, mock_task_repository):
        task1 = Mock(id=1, created_by="organizer123")
        task2 = Mock(id=2, created_by="organizer123")

        mock_task_repository.get_by_creator.return_value = [task1, task2]

        result = await task_service.get_organizer_tasks("organizer123")

        assert len(result) == 2
        assert result[0].created_by == "organizer123"
        assert result[1].created_by == "organizer123"
        mock_task_repository.get_by_creator.assert_called_once_with("organizer123")

    # Тест для получения задач организатора когда их нет
    @pytest.mark.asyncio
    async def test_get_organizer_tasks_empty(self, task_service, mock_task_repository):
        mock_task_repository.get_by_creator.return_value = []

        result = await task_service.get_organizer_tasks("organizer456")

        assert result == []
        mock_task_repository.get_by_creator.assert_called_once_with("organizer456")


class TestGetVolunteerTasks:
    # Тест для получения задач волонтера
    @pytest.mark.asyncio
    async def test_get_volunteer_tasks_success(self, task_service, mock_task_repository):
        task1 = Mock(id=1, assigned_to="volunteer123")
        task2 = Mock(id=2, assigned_to="volunteer123")

        mock_task_repository.get_by_assignee.return_value = [task1, task2]

        result = await task_service.get_volunteer_tasks("volunteer123")

        assert len(result) == 2
        assert result[0].assigned_to == "volunteer123"
        assert result[1].assigned_to == "volunteer123"
        mock_task_repository.get_by_assignee.assert_called_once_with("volunteer123")

    # Тест для получения задач волонтера когда их нет
    @pytest.mark.asyncio
    async def test_get_volunteer_tasks_empty(self, task_service, mock_task_repository):
        mock_task_repository.get_by_assignee.return_value = []

        result = await task_service.get_volunteer_tasks("volunteer456")

        assert result == []
        mock_task_repository.get_by_assignee.assert_called_once_with("volunteer456")


class TestGetVolunteerActiveTasks:
    # Тест для получения активных задач волонтера
    @pytest.mark.asyncio
    async def test_get_volunteer_active_tasks_success(self, task_service, mock_task_repository):
        task1 = Mock(id=1, assigned_to="volunteer123", is_active=True)
        task2 = Mock(id=2, assigned_to="volunteer123", is_active=True)

        mock_task_repository.get_active_by_assignee.return_value = [task1, task2]

        result = await task_service.get_volunteer_active_tasks("volunteer123")

        assert len(result) == 2
        assert all(task.assigned_to == "volunteer123" for task in result)
        mock_task_repository.get_active_by_assignee.assert_called_once_with("volunteer123")


class TestGetVolunteerCompletedTasks:
    # Тест для получения выполненных задач волонтера
    @pytest.mark.asyncio
    async def test_get_volunteer_completed_tasks_success(self, task_service, mock_task_repository):
        task1 = Mock(id=1, assigned_to="volunteer123", is_completed=True)
        task2 = Mock(id=2, assigned_to="volunteer123", is_completed=True)

        mock_task_repository.get_completed_by_assignee.return_value = [task1, task2]

        result = await task_service.get_volunteer_completed_tasks("volunteer123")

        assert len(result) == 2
        assert all(task.assigned_to == "volunteer123" for task in result)
        mock_task_repository.get_completed_by_assignee.assert_called_once_with("volunteer123")



class TestGetTasksStatistics:
    # Тест для получения статистики по задачам
    @pytest.mark.asyncio
    async def test_get_tasks_statistics_with_organizer(self, task_service, mock_task_repository):
        mock_statistics = {
            "total_tasks": 10,
            "active_tasks": 7,
            "completed_tasks": 3,
            "organizer_name": "organizer123"
        }

        mock_task_repository.get_statistics.return_value = mock_statistics

        result = await task_service.get_tasks_statistics("organizer123")

        assert result == mock_statistics
        assert result["total_tasks"] == 10
        mock_task_repository.get_statistics.assert_called_once_with("organizer123")

    # Тест для получения общей статистики
    @pytest.mark.asyncio
    async def test_get_tasks_statistics_general(self, task_service, mock_task_repository):
        mock_statistics = {
            "total_tasks": 25,
            "active_tasks": 15,
            "completed_tasks": 10
        }

        mock_task_repository.get_statistics.return_value = mock_statistics

        result = await task_service.get_tasks_statistics()

        assert result == mock_statistics
        mock_task_repository.get_statistics.assert_called_once_with(None)

    # Тест для получения пустой статистики
    @pytest.mark.asyncio
    async def test_get_tasks_statistics_empty(self, task_service, mock_task_repository):
        mock_task_repository.get_statistics.return_value = {}

        result = await task_service.get_tasks_statistics()

        assert result == {}
        mock_task_repository.get_statistics.assert_called_once_with(None)


class TestMarkTaskCompleted:
    # Тест для успешной пометки задачи как выполненной
    @pytest.mark.asyncio
    async def test_mark_task_completed_success(self, task_service, mock_task_repository):
        mock_task_repository.mark_completed.return_value = True

        result = await task_service.mark_task_completed("task_123", "volunteer123")

        assert result is True
        mock_task_repository.mark_completed.assert_called_once_with("task_123", "volunteer123")

    # Тест для неудачной пометки задачи как выполненной
    @pytest.mark.asyncio
    async def test_mark_task_completed_failure(self, task_service, mock_task_repository):
        mock_task_repository.mark_completed.return_value = False

        result = await task_service.mark_task_completed("task_123", "volunteer123")

        assert result is False
        mock_task_repository.mark_completed.assert_called_once_with("task_123", "volunteer123")


class TestIsTaskAssignedTo:
    # Тест для проверки назначения задачи волонтеру
    @pytest.mark.asyncio
    async def test_is_task_assigned_to_true(self, task_service, mock_task_repository):
        mock_task = Mock()
        mock_task.is_assigned_to.return_value = True

        mock_task_repository.get_by_telegram_id.return_value = mock_task

        result = await task_service.is_task_assigned_to("task_123", "volunteer123")

        assert result is True
        mock_task_repository.get_by_telegram_id.assert_called_once_with("task_123")
        mock_task.is_assigned_to.assert_called_once_with("volunteer123")

    # Тест для проверки назначения несуществующей задачи
    @pytest.mark.asyncio
    async def test_is_task_assigned_to_task_not_found(self, task_service, mock_task_repository):
        mock_task_repository.get_by_telegram_id.return_value = None

        result = await task_service.is_task_assigned_to("task_nonexistent", "volunteer123")

        assert result is False
        mock_task_repository.get_by_telegram_id.assert_called_once_with("task_nonexistent")


class TestIsTaskCompletedBy:
    # Тест для проверки выполнения задачи волонтером
    @pytest.mark.asyncio
    async def test_is_task_completed_by_true(self, task_service, mock_task_repository):
        mock_task = Mock()
        mock_task.is_completed_by.return_value = True

        mock_task_repository.get_by_telegram_id.return_value = mock_task

        result = await task_service.is_task_completed_by("task_123", "volunteer123")

        assert result is True
        mock_task_repository.get_by_telegram_id.assert_called_once_with("task_123")
        mock_task.is_completed_by.assert_called_once_with("volunteer123")

    # Тест для проверки что задача не выполнена волонтером
    @pytest.mark.asyncio
    async def test_is_task_completed_by_false(self, task_service, mock_task_repository):
        mock_task = Mock()
        mock_task.is_completed_by.return_value = False

        mock_task_repository.get_by_telegram_id.return_value = mock_task

        result = await task_service.is_task_completed_by("task_123", "volunteer123")

        assert result is False
        mock_task_repository.get_by_telegram_id.assert_called_once_with("task_123")
        mock_task.is_completed_by.assert_called_once_with("volunteer123")



class TestGetTasksForBroadcast:
    # Тест для получения задач для рассылки с указанием волонтера
    @pytest.mark.asyncio
    async def test_get_tasks_for_broadcast_with_volunteer(self, task_service, mock_task_repository):
        task1 = Mock(id=1, assigned_to="volunteer123")
        task2 = Mock(id=2, assigned_to="volunteer123")

        mock_task_repository.get_active_by_assignee.return_value = [task1, task2]

        result = await task_service.get_tasks_for_broadcast("volunteer123")

        assert len(result) == 2
        assert result[0].assigned_to == "volunteer123"
        assert result[1].assigned_to == "volunteer123"
        mock_task_repository.get_active_by_assignee.assert_called_once_with("volunteer123")

    # Тест для получения задач для рассылки без указания волонтера
    @pytest.mark.asyncio
    async def test_get_tasks_for_broadcast_without_volunteer(self, task_service, mock_task_repository):
        task1 = Mock(id=1, is_active=True)
        task2 = Mock(id=2, is_active=True)

        mock_task_repository.get_all.return_value = [task1, task2]

        result = await task_service.get_tasks_for_broadcast()

        assert len(result) == 2
        mock_task_repository.get_all.assert_called_once_with(only_active=True)



