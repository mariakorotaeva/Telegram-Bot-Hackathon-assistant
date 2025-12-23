import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine.result import ScalarResult

from repositories.user_repository import UserRepository
from models.user import User, UserRole, ParticipantStatus


class TestUserRepository:
    """Тесты для UserRepository"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = 1
        user.telegram_id = 123456
        user.username = "test_user"
        user.role = UserRole.PARTICIPANT
        user.is_active = True
        user.team_id = None
        user.profile_active = False
        user.profile_text = None
        user.participant_status = ParticipantStatus.LOOKING_FOR_TEAM
        return user

    @pytest.fixture
    def repo(self):
        return UserRepository()

    @pytest.mark.asyncio
    async def test_join_team_success(self, repo):
        with patch.object(repo, 'update', AsyncMock(return_value=True)):
            result = await repo.join_team(1, 5)

            assert result is True
            repo.update.assert_called_once_with(
                1,
                team_id=5,
                participant_status=ParticipantStatus.IN_TEAM
            )

    @pytest.mark.asyncio
    async def test_leave_team_success(self, repo):
        with patch.object(repo, 'update', AsyncMock(return_value=True)):
            result = await repo.leave_team(1)

            assert result is True
            repo.update.assert_called_once_with(
                1,
                team_id=None,
                participant_status=ParticipantStatus.LOOKING_FOR_TEAM
            )

    @pytest.mark.asyncio
    async def test_update_profile_success(self, repo):
        with patch.object(repo, 'update', AsyncMock(return_value=True)):
            result = await repo.update_profile(1, "New profile text")

            assert result is True
            repo.update.assert_called_once_with(
                1,
                profile_text="New profile text"
            )

    @pytest.mark.asyncio
    async def test_set_profile_active_without_user(self, repo):
        with patch.object(repo, 'get_by_id', AsyncMock(return_value=None)):
            result = await repo.set_profile_active(1, True)

            assert result is False

    @pytest.mark.asyncio
    async def test_set_profile_active_with_team(self, repo, mock_user):
        mock_user.team_id = 5
        with patch.object(repo, 'get_by_id', AsyncMock(return_value=mock_user)):
            result = await repo.set_profile_active(1, True)

            assert result is False

    @pytest.mark.asyncio
    async def test_set_profile_active_empty_profile(self, repo, mock_user):
        mock_user.team_id = None
        mock_user.profile_text = ""
        with patch.object(repo, 'get_by_id', AsyncMock(return_value=mock_user)):
            result = await repo.set_profile_active(1, True)

            assert result is False

    @pytest.mark.asyncio
    async def test_set_profile_active_success(self, repo, mock_user):
        mock_user.team_id = None
        mock_user.profile_text = "Valid profile"
        with patch.object(repo, 'get_by_id', AsyncMock(return_value=mock_user)), \
                patch.object(repo, 'update', AsyncMock(return_value=True)):
            result = await repo.set_profile_active(1, True)

            assert result is True
            repo.update.assert_called_once_with(1, profile_active=True)

