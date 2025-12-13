from aiogram import Router
from .start import router as start_router
from .menu import router as menu_router
from .broadcast import router as broadcast_router
from .faq import router as faq_router
from .schedule import router as schedule_router

router = Router()
router.include_router(start_router)
router.include_router(menu_router)
router.include_router(broadcast_router)
router.include_router(faq_router)
router.include_router(schedule_router)