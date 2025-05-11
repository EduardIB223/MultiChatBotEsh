import logging
from typing import Optional, Union
from aiogram import Bot

logger = logging.getLogger(__name__)

async def change_topic_icon(
    chat_id: Union[int, str],
    topic_id: int,
    emoji: str,
    telethon_client: Optional[object] = None,
    bot: Optional[Bot] = None
) -> bool:
    """
    Универсальная функция смены иконки топика
    Возвращает True при успехе, False при ошибке
    """
    # Сначала пробуем через Bot API
    if bot:
        try:
            await bot.request(
                "editForumTopic",
                {
                    "chat_id": chat_id,
                    "message_thread_id": topic_id,
                    "icon_emoji_id": emoji  # Для стандартных эмодзи
                }
            )
            logger.info(f"Иконка изменена через Bot API: {emoji}")
            return True
        except Exception as e:
            logger.error(f"Bot API error: {e}")

    # Если не получилось, пробуем через Telethon (для кастомных эмодзи)
    if telethon_client:
        try:
            emoji_id = await _get_custom_emoji_id(emoji, telethon_client)
            if not emoji_id:
                return False
            from telethon.tl.functions.channels import EditForumTopicRequest
            await telethon_client(EditForumTopicRequest(
                channel=chat_id,
                topic_id=topic_id,
                icon_emoji_id=emoji_id
            ))
            logger.info(f"Иконка изменена через Telethon: {emoji}")
            return True
        except Exception as e:
            logger.error(f"Telethon error: {e}")
    return False

async def _get_custom_emoji_id(emoji: str, client) -> Optional[int]:
    """Получаем ID кастомного эмодзи через Telethon"""
    try:
        icons = await client.get_forum_topic_icons()
        for icon in icons:
            if getattr(icon, 'emoticon', None) == emoji:
                return getattr(icon, 'id', None)
        return None
    except Exception as e:
        logger.error(f"Emoji fetch error: {e}")
        return None

async def create_invite_link(chat_id: int, telethon_client) -> str:
    """Создаем одноразовую invite-ссылку через Telethon"""
    try:
        from telethon.tl.functions.messages import ExportChatInviteRequest
        result = await telethon_client(
            ExportChatInviteRequest(
                peer=chat_id,
                legacy_revoke_permanent=True
            )
        )
        return getattr(result, 'link', '')
    except Exception as e:
        logger.error(f"Invite link error: {e}")
        return '' 