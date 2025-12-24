# services/poll_service.py
"""
Сервисный слой для работы с опросами.
Бизнес-логика для организаторов и участников.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from repositories.poll_repository import PollRepository
from repositories.poll_vote_repository import PollVoteRepository
from repositories.user_repository import UserRepository
from models.poll import Poll, PollMessage
from models.poll_vote import PollVote
from models.user import User, UserRole


class PollService:
    """Сервис для работы с опросами."""

    def __init__(self, poll_repository: PollRepository | None = None, vote_repository: PollVoteRepository | None = None):
        self.poll_repo = poll_repository or PollRepository()
        self.vote_repo = vote_repository or PollVoteRepository()
        self.user_repo = UserRepository()

    # ==================== СОЗДАНИЕ И УПРАВЛЕНИЕ ОПРОСАМИ ====================

    async def create_poll(
            self,
            question: str,
            creator_id: int,
            creator_name: str,
            options: List[str],
            is_anonymous: bool = False,
            allow_multiple_votes: bool = False,
            show_results_immediately: bool = True,
            category: Optional[str] = None,
            expires_in_hours: Optional[int] = None
    ) -> Poll:
        """Создаёт новый опрос."""

        # Проверяем, что есть варианты ответов
        if not options or len(options) < 2:
            raise ValueError("Опрос должен иметь минимум 2 варианта ответа")

        # Создаём объект опроса
        poll = Poll(
            poll_id=f"poll_{uuid.uuid4().hex[:8]}",
            question=question,
            creator_id=creator_id,
            creator_name=creator_name,
            options=options,
            is_anonymous=is_anonymous,
            allow_multiple_votes=allow_multiple_votes,
            show_results_immediately=show_results_immediately,
            category=category
        )

        # Устанавливаем время окончания, если указано
        if expires_in_hours:
            poll.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        # Сохраняем в БД
        return await self.poll_repo.create(poll)

    async def update_poll(self, poll_id: int, **kwargs) -> bool:
        """Обновляет опрос."""
        return await self.poll_repo.update(poll_id, **kwargs)

    async def create_poll_message(self, poll_id: int, user_id: int, poll_tg_id: str) -> Optional[PollMessage]:
        poll = await self.poll_repo.get_by_id(poll_id)
        user = await self.user_repo.get_by_id(user_id)
        if user and poll:
            return await self.poll_repo.create_poll_message(poll, user, poll_tg_id)
        return None

    async def get_poll_by_message(self, user_id: int, tg_poll_id: str) -> Optional[Poll]:
        return await self.poll_repo.get_poll_by_message(user_id, tg_poll_id)

    async def deactivate_poll(self, poll_id: int) -> bool:
        """Деактивирует опрос."""
        return await self.poll_repo.deactivate(poll_id)

    async def delete_poll(self, poll_id: int) -> bool:
        """Удаляет опрос."""
        return await self.poll_repo.delete(poll_id)

    async def close_expired_polls(self) -> List[Poll]:
        """Закрывает опросы с истекшим сроком."""
        expired_polls = await self.poll_repo.get_expired_polls()

        for poll in expired_polls:
            await self.poll_repo.update(poll.id, is_active=False)

        return expired_polls

    # ==================== ПОЛУЧЕНИЕ ОПРОСОВ ====================

    async def get_poll(self, poll_id: int) -> Optional[Poll]:
        """Возвращает опрос по ID."""
        return await self.poll_repo.get_by_id(poll_id)

    async def get_poll_by_uid(self, poll_uid: str) -> Optional[Poll]:
        """Возвращает опрос по уникальному строковому ID."""
        return await self.poll_repo.get_by_poll_id(poll_uid)

    async def get_active_polls(self) -> List[Poll]:
        """Возвращает все активные опросы."""
        return await self.poll_repo.get_all_active()

    async def get_polls_by_creator(self, creator_id: int) -> List[Poll]:
        """Возвращает опросы создателя."""
        return await self.poll_repo.get_by_creator(creator_id)

    async def search_polls(self, search_term: str) -> List[Poll]:
        """Ищет опросы по тексту."""
        return await self.poll_repo.search_polls(search_term)

    async def get_polls_by_category(self, category: str) -> List[Poll]:
        """Возвращает опросы по категории."""
        return await self.poll_repo.get_by_category(category)

    # ==================== ГОЛОСОВАНИЕ ====================

    async def vote_in_poll(
            self,
            poll_id: int,
            user_id: int,
            option_index: int
    ) -> Dict[str, Any]:
        """
        Голосует в опросе.
        Возвращает результат голосования.
        """
        # Получаем опрос
        poll = await self.get_poll(poll_id)
        if not poll:
            return {"success": False, "error": "Опрос не найден"}

        # Проверяем, можно ли голосовать
        if not poll.can_vote():
            return {"success": False, "error": "Опрос закрыт или истек срок"}

        # Проверяем допустимый индекс варианта
        if option_index < 0 or option_index >= len(poll.options):
            return {"success": False, "error": "Неверный вариант ответа"}

        # Проверяем, голосовал ли уже пользователь
        existing_vote = await self.vote_repo.get_vote_by_user_and_poll(user_id, poll_id)

        if existing_vote and not poll.allow_multiple_votes:
            # Пользователь уже голосовал и повторное голосование запрещено
            return {
                "success": False,
                "error": "Вы уже голосовали в этом опросе",
                "previous_vote": existing_vote.option_index
            }

        if existing_vote:
            # Обновляем существующий голос
            await self.vote_repo.update(existing_vote.id, option_index=option_index)
            vote_id = existing_vote.id
        else:
            # Создаём новый голос
            vote = PollVote(
                poll_id=poll_id,
                user_id=user_id,
                option_index=option_index
            )
            created_vote = await self.vote_repo.create(vote)
            vote_id = created_vote.id

            # Обновляем общее количество голосов в опросе
            await self.poll_repo.update(poll_id, total_votes=poll.total_votes + 1)

        # Получаем обновлённые результаты
        results = await self.vote_repo.get_poll_results(poll_id)

        return {
            "success": True,
            "vote_id": vote_id,
            "poll_id": poll_id,
            "option_index": option_index,
            "option_text": poll.options[option_index],
            "total_votes": poll.total_votes + (0 if existing_vote else 1),
            "results": results
        }

    async def unvote_in_poll(
        self,
        poll_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        poll = await self.get_poll(poll_id)
        if not poll:
            return {"success": False, "error": "Опрос не найден"}

        # Проверяем, можно ли голосовать
        if not poll.can_vote():
            return {"success": False, "error": "Опрос закрыт или истек срок"}


        existing_vote = await self.vote_repo.get_vote_by_user_and_poll(user_id, poll_id)

        if existing_vote:
            # Обновляем существующий голос
            await self.vote_repo.delete(existing_vote.id)
            await self.poll_repo.update(poll_id, total_votes=poll.total_votes - 1)
        else:
            return {
                "success": False,
                "error": "Вы ещё не голосовали в этом опросе"
            }

        results = await self.vote_repo.get_poll_results(poll_id)

        return {
            "success": True,
            "poll_id": poll.id,
            "total_votes": poll.total_votes - (0 if existing_vote else 1),
            "results": results
        }

    async def get_user_vote(self, user_id: int, poll_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает голос пользователя в опросе."""
        return await self.vote_repo.get_user_vote_details(user_id, poll_id)

    async def has_user_voted(self, user_id: int, poll_id: int) -> bool:
        """Проверяет, голосовал ли пользователь."""
        return await self.vote_repo.has_user_voted(user_id, poll_id)

    # ==================== РЕЗУЛЬТАТЫ И СТАТИСТИКА ====================

    async def get_poll_results(self, poll_id: int) -> Dict[str, Any]:
        """Возвращает результаты опроса."""
        poll = await self.get_poll(poll_id)
        if not poll:
            return {}

        results = await self.vote_repo.get_poll_results(poll_id)
        total_votes = sum(results.values())

        return {
            "poll": poll.to_dict(),
            "results": results,
            "total_votes": total_votes,
            "is_active": poll.is_active,
            "has_expired": poll.has_expired()
        }

    async def get_detailed_results(self, poll_id: int) -> Dict[str, Any]:
        """Возвращает детализированные результаты (включая ID голосовавших, если не анонимно)."""
        poll = await self.get_poll(poll_id)
        if not poll:
            return {}

        # Если опрос анонимный, не показываем кто голосовал
        if poll.is_anonymous:
            detailed = await self.vote_repo.get_poll_results(poll_id)
            voter_info = {}
        else:
            detailed = await self.vote_repo.get_detailed_results(poll_id)
            voter_info = {item["option_index"]: item["voter_ids"] for item in detailed}

        return {
            "poll": poll.to_dict(),
            "results": detailed,
            "voter_info": voter_info,
            "total_votes": poll.total_votes
        }

    async def get_polls_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Возвращает статистику опросов."""
        return await self.poll_repo.get_polls_statistics(days)

    async def get_participation_rate(self, poll_id: int, total_users: int) -> float:
        """Рассчитывает процент участия в опросе."""
        votes_count = await self.vote_repo.get_votes_count_by_poll(poll_id)

        if total_users == 0:
            return 0.0

        return (votes_count / total_users) * 100

    # ==================== ЭКСПОРТ И ОТЧЕТЫ ====================

    async def export_poll_data(self, poll_id: int) -> Dict[str, Any]:
        """Экспортирует все данные опроса."""
        poll = await self.get_poll(poll_id)
        if not poll:
            return {}

        results = await self.get_detailed_results(poll_id)

        return {
            "metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "poll_id": poll_id,
                "poll_uid": poll.poll_id
            },
            "poll": poll.to_dict(),
            "results": results,
            "voters_count": poll.total_votes,
            "summary": {
                "question": poll.question,
                "options": poll.options,
                "total_votes": poll.total_votes,
                "created_by": poll.creator_name,
                "created_at": poll.created_at.isoformat() if poll.created_at else None,
                "status": "active" if poll.is_active and not poll.has_expired() else "closed"
            }
        }