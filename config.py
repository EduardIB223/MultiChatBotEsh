from dataclasses import dataclass
import os
from os import getenv
from dotenv import load_dotenv

@dataclass
class TgBot:
    token: str
    admin_ids: list[int]

@dataclass
class Telethon:
    api_id: int
    api_hash: str
    session_name: str = "user_session"

@dataclass
class Config:
    tg_bot: TgBot
    telethon: Telethon

def load_config() -> Config:
    # Загружаем переменные окружения из файла .env
    load_dotenv()
    
    # Загружаем конфигурацию бота
    return Config(
        tg_bot=TgBot(
            token=getenv("BOT_TOKEN"),
            admin_ids=list(map(int, getenv("ADMIN_IDS", "").split(",")))
        ),
        telethon=Telethon(
            api_id=int(getenv("API_ID")),
            api_hash=getenv("API_HASH"),
            session_name=getenv("SESSION_NAME", "user_session")
        )
    )

# Настройки бота
MAX_TOPICS = 20  # Максимальное количество топиков
MAX_TEMPLATES = 10  # Максимальное количество шаблонов на пользователя

# Database settings
DATABASE_URL = "sqlite+aiosqlite:///bot_data.db"

# Bot settings
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id] 