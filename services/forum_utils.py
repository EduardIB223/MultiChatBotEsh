import logging
import asyncio
from typing import Optional, Union
from telethon.tl.functions.channels import EditForumTopicRequest
from telethon.tl import functions
from aiogram import Bot
from telethon import TelegramClient

logger = logging.getLogger(__name__)

STANDARD_EMOJIS = {"📌", "⭐", "❗", "⚠️", "🔒", "📝", "📢", "💡", "❓", "📚", "🎮", "🎵", "🎬", "📷"}

async def smart_change_icon(
    chat_id: int,
    topic_id: int,
    emoji: str,
    bot: Bot,
    max_retries: int = 3,
    delay: int = 10
) -> bool:
    """Смена иконки с задержкой и повторами через Bot API для стандартных эмодзи"""
    if emoji not in STANDARD_EMOJIS:
        logger.warning(f"Эмодзи {emoji} не поддерживается Bot API")
        return False
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(delay if attempt > 0 else 0)
            await bot.request(
                "editForumTopic",
                {
                    "chat_id": chat_id,
                    "message_thread_id": topic_id,
                    "icon_emoji_id": emoji
                }
            )
            logger.info(f"Иконка {emoji} успешно установлена на попытке {attempt+1}")
            return True
        except Exception as e:
            logger.warning(f"Попытка {attempt+1} не удалась: {e}")
            if "CHAT_NOT_FOUND" in str(e) or "not enough rights" in str(e):
                continue
            else:
                break
    return False

async def change_topic_icon(
    chat_id: Union[int, str],
    topic_id: int,
    emoji: str,
    telethon_client: Optional[TelegramClient] = None,
    bot: Optional[Bot] = None
) -> bool:
    """
    Автоматически выбирает оптимальный метод для смены иконки:
    1. Bot API (для стандартных эмодзи)
    2. Telethon (для кастомных стикеров)
    """
    # Попытка через Bot API
    if bot and emoji in STANDARD_EMOJIS:
        try:
            await bot.request(
                "editForumTopic",
                {
                    "chat_id": chat_id,
                    "message_thread_id": topic_id,
                    "icon_emoji_id": emoji
                }
            )
            logger.info(f"Иконка {emoji} установлена через Bot API")
            return True
        except Exception as e:
            logger.error(f"Ошибка Bot API: {str(e)}")

    # Fallback на Telethon (для кастомных эмодзи)
    if telethon_client and emoji not in STANDARD_EMOJIS:
        try:
            # Получаем ID кастомного эмодзи
            emoji_id = await _get_custom_emoji_id(emoji, telethon_client)
            if not emoji_id:
                return False

            # Используем raw API-вызов
            await telethon_client(EditForumTopicRequest(
                channel=chat_id,
                topic_id=topic_id,
                icon_emoji_id=emoji_id
            ))
            logger.info(f"Иконка {emoji} (ID: {emoji_id}) установлена через Telethon")
            return True
        except Exception as e:
            logger.error(f"Ошибка Telethon: {str(e)}")

    return False

async def _get_custom_emoji_id(emoji: str, client: TelegramClient) -> Optional[int]:
    """Получает ID кастомного эмодзи через Telethon"""
    try:
        icons = await client.get_forum_topic_icons()
        return next((icon.id for icon in icons if icon.emoticon == emoji), None)
    except Exception as e:
        logger.error(f"Ошибка получения эмодзи: {str(e)}")
        return None

async def generate_invite_link(
    client: TelegramClient,
    chat_id: Union[int, str]
) -> Optional[str]:
    """Создаёт одноразовую инвайт-ссылку через Telethon"""
    try:
        result = await client(
            functions.messages.ExportChatInviteRequest(
                peer=chat_id,
                legacy_revoke_permanent=True
            )
        )
        return result.link
    except Exception as e:
        logger.error(f"Ошибка генерации ссылки: {str(e)}")
        return None 