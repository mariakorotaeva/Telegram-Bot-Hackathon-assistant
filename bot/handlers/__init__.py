from aiogram import Router
from .start import router as start_router
from .menu import router as menu_router

router = Router()
router.include_router(start_router)
router.include_router(menu_router)