from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from services.telethon_service import TelethonService

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db_service):
        self.db_service = db_service
        
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        data["db"] = self.db_service
        return await handler(event, data)

class TelethonMiddleware(BaseMiddleware):
    def __init__(self, telethon_service: TelethonService):
        self.telethon_service = telethon_service
        
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        data["telethon"] = self.telethon_service
        return await handler(event, data)

class BotAPIMiddleware(BaseMiddleware):
    def __init__(self, bot_api_service):
        self.bot_api_service = bot_api_service
        
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        data["bot_api"] = self.bot_api_service
        return await handler(event, data) 