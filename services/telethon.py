from telethon import TelegramClient
from telethon.tl.functions.channels import EditAdminRequest, CreateChannelRequest
from telethon.tl.functions.messages import CreateChatRequest
from telethon.tl.types import ChatAdminRights, InputChannel, InputUser
from typing import List, Optional, Dict, Any
import logging
import os
import json
import asyncio
import datetime

logger = logging.getLogger(__name__)

class TelethonService:
    def __init__(self, api_id: int, api_hash: str, bot_token: str):
        self.client = TelegramClient('bot', api_id, api_hash)
        self.bot_token = bot_token
        self.templates_dir = 'templates'
        
        # Создаем директорию для шаблонов, если её нет
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
    
    async def start(self):
        """Запускает клиент"""
        await self.client.start(bot_token=self.bot_token)
        logger.info("Telethon client started")
    
    async def create_forum(self, chat_data: dict, user_id: int) -> Optional[Dict[str, Any]]:
        """Создает форум-чат и добавляет пользователя"""
        try:
            logger.info(f"Starting forum creation for user {user_id}")
            
            # Создаем канал (который автоматически станет супергруппой)
            result = await self.client(CreateChannelRequest(
                title=chat_data['title'],
                about=chat_data.get('description', ''),
                megagroup=True  # Это создаст супергруппу
            ))

            channel = result.chats[0]
            logger.info(f"Channel created with ID: {channel.id}")
            
            # Даем боту права администратора
            bot_admin_rights = ChatAdminRights(
                change_info=True,
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=True,  # Важно: даем боту право добавлять админов
                anonymous=False,
                manage_call=True,
                other=True
            )
            
            # Получаем ID бота
            bot_me = await self.client.get_me()
            logger.info(f"Bot ID: {bot_me.id}")
            
            # Назначаем бота администратором
            await self.client(EditAdminRequest(
                channel=channel.id,
                user_id=bot_me.id,
                admin_rights=bot_admin_rights,
                rank="Bot Admin"
            ))
            logger.info("Bot promoted to admin")
            
            # Небольшая задержка для уверенности
            await asyncio.sleep(2)
            
            # Добавляем пользователя в чат
            await self.client.add_chat_user(channel.id, user_id)
            logger.info(f"User {user_id} added to chat")
            
            # Еще небольшая задержка
            await asyncio.sleep(2)
            
            # Теперь делаем пользователя администратором
            user_admin_rights = ChatAdminRights(
                change_info=True,
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                add_admins=True,
                anonymous=False,
                manage_call=True,
                other=True
            )
            
            await self.client(EditAdminRequest(
                channel=channel.id,
                user_id=user_id,
                admin_rights=user_admin_rights,
                rank="Admin"
            ))
            logger.info(f"User {user_id} promoted to admin")
            
            # Получаем ссылку-приглашение
            invite_link = await self.client.export_chat_invite_link(channel.id)
            logger.info(f"Invite link generated: {invite_link}")

            return {
                'chat_id': channel.id,
                'title': channel.title,
                'invite_link': invite_link
            }

        except Exception as e:
            logger.error(f"Error creating forum: {e}", exc_info=True)
            return None
    
    async def add_user_to_forum(self, forum_id: int, user_id: int) -> bool:
        """
        Add a user to the forum
        
        Args:
            forum_id: ID of the forum
            user_id: ID of the user to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            await self.client.add_chat_user(forum_id, user_id)
            return True
        except Exception as e:
            logger.error(f"Error adding user to forum: {e}")
            return False
    
    async def disconnect(self):
        """Отключает клиент"""
        await self.client.disconnect()
        logger.info("Telethon client disconnected")

    async def save_chat_template(self, user_id: int, template: ChatTemplate, old_name: str = None) -> bool:
        """Сохраняет шаблон чата для пользователя"""
        try:
            # Загружаем существующие шаблоны
            templates = await self.load_chat_templates(user_id)
            
            # Если передано старое имя, обновляем существующий шаблон
            if old_name:
                for i, t in enumerate(templates):
                    if t.name == old_name:
                        # Сохраняем дату создания из старого шаблона
                        template.created_at = t.created_at
                        templates[i] = template
                        break
            else:
                # Проверяем, существует ли шаблон с таким именем
                if any(t.name == template.name for t in templates):
                    logger.error(f"Template with name '{template.name}' already exists")
                    return False
                # Добавляем новый шаблон
                templates.append(template)
            
            # Создаем директорию, если она не существует
            os.makedirs(self.templates_dir, exist_ok=True)
            
            # Путь к файлу шаблонов
            file_path = os.path.join(self.templates_dir, f"{user_id}.json")
            
            # Сохраняем в файл
            templates_data = [t.to_dict() for t in templates]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(templates_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Successfully saved template '{template.name}' for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False

    async def make_chat_admin(self, chat_id: int, user_id: int) -> bool:
        """Делает пользователя администратором чата с определенными правами"""
        try:
            # Показываем действие
            async with self.client.action(user_id, 'typing'):
                # Создаем права администратора с конкретными разрешениями
                admin_rights = ChatAdminRights(
                    change_info=True,      # Может изменять информацию о чате
                    post_messages=True,    # Может отправлять сообщения
                    edit_messages=True,    # Может редактировать сообщения
                    delete_messages=True,  # Может удалять сообщения
                    ban_users=True,        # Может банить пользователей
                    invite_users=True,     # Может приглашать пользователей
                    pin_messages=True,     # Может закреплять сообщения
                    add_admins=False,      # Не может добавлять других админов
                    anonymous=True,        # Может писать анонимно
                    manage_call=True,      # Может управлять звонками
                    other=True            # Другие права
                )

                # Выполняем запрос на назначение админа
                await self.client(EditAdminRequest(
                    channel=chat_id,  # ID канала/супергруппы
                    user_id=user_id,  # ID пользователя
                    admin_rights=admin_rights,
                    rank="Admin"      # Ранг администратора
                ))

                logger.info(f"Successfully made user {user_id} admin in chat {chat_id}")
                return True

        except Exception as e:
            logger.error(f"Error making user {user_id} admin in chat {chat_id}: {e}")
            return False