from dotenv import load_dotenv
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis
from handlers.commands import router, register_commands
from middleware.telethon_middleware import TelethonMiddleware
from services.telethon import TelethonService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot settings
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telethon settings
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")

async def main():
    try:
        # Initialize Redis with more reliable settings
        redis = Redis(
            host='localhost',
            port=6379,
            db=0,
            encoding='utf-8',
            decode_responses=True,
            socket_timeout=5,
            retry_on_timeout=True
        )
        
        # Test Redis connection
        try:
            await redis.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
        # Initialize Redis storage with custom key builder
        key_builder = DefaultKeyBuilder(
            with_bot_id=True,
            with_destiny=True,
            separator=":"
        )
        storage = RedisStorage(redis=redis, key_builder=key_builder)
        
        # Initialize bot and dispatcher
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher(storage=storage)
        
        # Initialize Telethon service
        telethon_service = TelethonService()
        await telethon_service.start()
        
        # Add middleware
        dp.message.middleware(TelethonMiddleware(telethon_service))
        dp.callback_query.middleware(TelethonMiddleware(telethon_service))
        
        # Include router and register commands
        dp.include_router(router)
        await register_commands(bot)
        
        # Start polling
        logger.info("Bot started")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
    finally:
        if 'redis' in locals():
            await redis.close()
        if 'storage' in locals():
            await storage.close()
        if 'telethon_service' in locals():
            await telethon_service.disconnect()
        if 'bot' in locals():
            await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
