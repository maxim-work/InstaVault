from aiogram import Router

from .broadcast import admin_router as broadcast_router
from .panel import admin_router as panel_router
from .search import admin_router as search_router
from .statistics import admin_router as statistics_router
from .users import admin_router as users_router

admin_router = Router()

admin_router.include_router(panel_router)
admin_router.include_router(users_router)
admin_router.include_router(search_router)
admin_router.include_router(broadcast_router)
admin_router.include_router(statistics_router)
