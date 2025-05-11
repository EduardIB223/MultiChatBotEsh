from aiogram import Dispatcher
from .commands import register_commands
from services.telethon_service import TelethonService
from .forum_handlers import router as forum_router

def register_all_handlers(dp: Dispatcher, telethon_service: TelethonService) -> None:
    """
    Регистрация всех обработчиков
    """
    # Регистрируем роутеры
    dp.include_router(forum_router)
    
    handlers = (
        register_commands,
        # Здесь можно добавить другие группы обработчиков
    )
    
    for handler in handlers:
        handler(dp, telethon_service) 