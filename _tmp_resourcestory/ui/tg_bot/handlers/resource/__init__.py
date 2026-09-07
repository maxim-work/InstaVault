from aiogram import Router

from .add import add_router
from .export import export_router
from .import_data import import_data_router
from .import_urls import import_urls_router
from .list import list_router
from .search import search_router
from .settings import settings_router

resource_router = Router()

resource_router.include_router(add_router)
resource_router.include_router(list_router)
resource_router.include_router(search_router)
resource_router.include_router(settings_router)
resource_router.include_router(export_router)
resource_router.include_router(import_data_router)
resource_router.include_router(import_urls_router)
