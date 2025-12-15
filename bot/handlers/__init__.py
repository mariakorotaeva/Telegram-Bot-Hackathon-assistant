from aiogram import Router
from .start import router as start_router
from .menu import router as menu_router
from .broadcast import router as broadcast_router
from .faq import router as faq_router
from .schedule import router as schedule_router
from .profile import router as profile_router
from .notifications import router as notifications_router
from .task import router as task_router
from .ai_assistant import router as assistant_router

router = Router()
router.include_router(start_router)
router.include_router(menu_router)
router.include_router(broadcast_router)
router.include_router(faq_router)
router.include_router(schedule_router)
router.include_router(profile_router)
router.include_router(notifications_router)
router.include_router(task_router)
router.include_router(assistant_router)