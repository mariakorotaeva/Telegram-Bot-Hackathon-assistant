import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine.result import ScalarResult

from repositories.team_repository import TeamRepository
from models.team import Team
from models.user import User, UserRole


class TestTeamRepository:
    """Тесты для TeamRepository"""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_team(self):
        team = MagicMock(spec=Team)
        team.id = 1
        team.name = "Test Team"
        team.captain_id = 1
        team.mentor_id = None
        return team

    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = 1
        user.team_id = 1
        user.role = UserRole.PARTICIPANT
        return user

    @pytest.fixture
    def repo(self):
        return TeamRepository()

    @pytest.mark.asyncio
    async def test_is_user_in_team_true(self, repo, mock_session, mock_user):
        with patch('repositories.team_repository.get_db', return_value=mock_session):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await repo.is_user_in_team(1)

            assert result is True

    @pytest.mark.asyncio
    async def test_is_user_captain_true(self, repo, mock_session, mock_team):
        with patch('repositories.team_repository.get_db', return_value=mock_session):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=mock_team)
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await repo.is_user_captain(1)

            assert result is True

