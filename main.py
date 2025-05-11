import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config, load_config
from handlers import register_all_handlers
from services.telethon_service import TelethonService
from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from handlers.bot_forum_handlers import router as bot_forum_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting bot...")
    
    # Загружаем конфигурацию
    config: Config = load_config()
    
    # Инициализируем хранилище состояний
    storage = MemoryStorage()
    
    # Инициализируем бота и диспетчер с новым синтаксисом
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)
    
    # Инициализируем сервис Telethon
    telethon_service = TelethonService(
        api_id=config.telethon.api_id,
        api_hash=config.telethon.api_hash,
        session_name="user_session"  # Используем пользовательскую сессию
    )
    
    try:
        # Подключаем Telethon
        logger.info("Connecting Telethon client...")
        if not await telethon_service.ensure_client():
            logger.error("Failed to connect Telethon client")
            return
        
        # Регистрируем все обработчики
        logger.info("Registering handlers...")
        register_all_handlers(dp, telethon_service)
        dp.include_router(bot_forum_router)
        
        # Запускаем бота
        logger.info("Starting Aiogram polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.exception(f"Critical error: {e}")
    finally:
        # Закрываем соединения
        logger.info("Shutting down...")
        await telethon_service.disconnect()
        await bot.session.close()
        
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!") 