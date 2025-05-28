from telethon.sync import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, SetDiscussionGroupRequest, InviteToChannelRequest, CreateForumTopicRequest
from telethon.tl.functions.messages import CreateChatRequest, MigrateChatRequest, ExportChatInviteRequest
from telethon.tl.types import InputChannel, InputPeerUser, InputPeerChannel
from telethon.tl.functions.channels import EditTitleRequest, EditAdminRequest, EditCreatorRequest
from telethon.tl.types import ChatAdminRights, ChannelParticipantsAdmins
from typing import List, Dict, Optional, Any
import logging
import json
import os
from datetime import datetime
import asyncio
import aiofiles
import shutil
import sys
from loguru import logger

from telethon.tl.types import ChatAdminRights
from telethon.tl.functions.channels import EditAdminRequest

from models.schemas import ChatCreate, Topic, Template, ChatTemplate

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Хардкодим emoji_id для популярных эмодзи Telegram (примерные значения, их можно расширить)
EMOJI_ID_MAP = {
    "📄": 5305467150676382066,
    "📑": 5305467150676382067,
    "📝": 5305467150676382068,
    "💬": 5305467150676382069,
    "📚": 5305467150676382070,
    "📌": 5305467150676382071,
    "📋": 5305467150676382072,
    "📅": 5305467150676382073,
    "📦": 5305467150676382074,
    "📊": 5305467150676382075,
    "📈": 5305467150676382076,
    "📉": 5305467150676382077,
    "📁": 5305467150676382078,
    "📂": 5305467150676382079,
    "📒": 5305467150676382080,
    "📕": 5305467150676382081,
    "📗": 5305467150676382082,
    "📘": 5305467150676382083,
    "📙": 5305467150676382084,
    "📔": 5305467150676382085,
    "📓": 5305467150676382086,
    "📃": 5305467150676382087,
    "📜": 5305467150676382088,
    "📎": 5305467150676382089,
    "📏": 5305467150676382090,
    "📐": 5305467150676382091,
    "🗂": 5305467150676382092,
    "🗃": 5305467150676382093,
    "🗄": 5305467150676382094,
    "🗒": 5305467150676382095,
    "🗓": 5305467150676382096,
    "🗞": 5305467150676382097,
    "📰": 5305467150676382098,
    "🏷": 5305467150676382099,
    "🏷️": 5305467150676382100
}

# --- Bot API сервис для топиков с эмодзи ---
from aiogram import Bot
from aiogram.methods import GetForumTopicIconStickers, CreateForumTopic

class BotApiService:
    @staticmethod
    async def get_forum_topic_icon_stickers(bot: Bot):
        """Получить список emoji_id для топиков через Bot API"""
        result = await bot(GetForumTopicIconStickers())
        # Вернёт список объектов ForumTopicIconSticker
        return result.stickers if hasattr(result, 'stickers') else []

    @staticmethod
    async def create_forum_topic(bot: Bot, chat_id: int, name: str, emoji_id: str):
        """Создать топик с эмодзи через Bot API"""
        try:
            # Загружаем рабочий список эмодзи
            with open("working_topic_emojis.json", "r", encoding="utf-8") as f:
                emoji_map = json.load(f)
            
            # Получаем emoji_id из рабочего списка
            if emoji_id in emoji_map:
                emoji_id = emoji_map[emoji_id]
            else:
                logger.info(f"Эмодзи {emoji_id} не найден в рабочем списке — топик будет без иконки")
                return None

            # Создаем топик через Bot API
            return await bot.create_forum_topic(
                chat_id=chat_id,
                name=name,
                icon_custom_emoji_id=emoji_id
            )
        except Exception as e:
            logger.error(f"Ошибка при создании топика: {e}")
            return None

class TelethonService:
    def __init__(self, api_id: int, api_hash: str, session_name: str = "bot_session"):
        """
        Инициализация сервиса Telethon
        :param api_id: API ID from Telegram
        :param api_hash: API Hash from Telegram
        :param session_name: Имя сессии
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client = None
        self._templates: Dict[int, List[ChatTemplate]] = {}
        
        # Используем абсолютный путь и создаем директорию, если её нет
        self.templates_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "templates.json")
        os.makedirs(os.path.dirname(self.templates_file), exist_ok=True)
        
        logger.info(f"Путь к файлу шаблонов: {self.templates_file}")
        self._load_templates()

    def _load_templates(self):
        """Загружает шаблоны из файла"""
        try:
            logger.info("Начало загрузки шаблонов")
            self._templates = {}  # Очищаем словарь перед загрузкой
            
            if not os.path.exists(self.templates_file):
                logger.info(f"Файл шаблонов {self.templates_file} не существует, создаем новый")
                self._save_templates()  # Создаем пустой файл
                return
                
            # Проверяем размер файла
            file_size = os.path.getsize(self.templates_file)
            if file_size == 0:
                logger.warning("Файл шаблонов пуст")
                return
                
            logger.info(f"Чтение файла шаблонов (размер: {file_size} байт)")
            
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                if not file_content.strip():
                    logger.warning("Файл шаблонов пуст")
                    return
                    
                try:
                    data = json.loads(file_content)
                except json.JSONDecodeError as e:
                    logger.error(f"Ошибка при разборе JSON: {e}")
                    logger.error(f"Содержимое файла: {file_content[:200]}...")  # Логируем начало файла
                    return
                
            if not isinstance(data, dict):
                logger.error(f"Некорректный формат файла шаблонов: {type(data)}")
                return
                
            logger.info(f"Найдено пользователей в файле: {len(data)}")
            
            for user_id_str, templates in data.items():
                try:
                    user_id = int(user_id_str)
                    if not isinstance(templates, list):
                        logger.error(f"Некорректный формат шаблонов для пользователя {user_id}: {type(templates)}")
                        continue
                        
                    self._templates[user_id] = []
                    logger.info(f"Загрузка {len(templates)} шаблонов для пользователя {user_id}")
                    
                    for t in templates:
                        try:
                            if not isinstance(t, dict):
                                logger.error(f"Некорректный формат шаблона: {type(t)}")
                                continue
                                
                            if 'name' not in t or 'chat_name' not in t:
                                logger.error(f"Отсутствуют обязательные поля в шаблоне: {t}")
                                continue
                                
                            # Преобразуем строку даты в объект datetime
                            created_at = None
                            if 'created_at' in t and t['created_at']:
                                try:
                                    created_at = datetime.fromisoformat(t['created_at'])
                                except ValueError as e:
                                    logger.warning(f"Не удалось преобразовать дату создания: {e}")
                            
                            topics = []
                            for tt in t.get('topics', []):
                                topic = Topic(
                                    title=tt['title'],
                                    description=tt.get('description', ''),
                                    icon_emoji=tt.get('icon_emoji'),
                                    icon_color=tt.get('icon_color', 0),
                                    is_closed=tt.get('is_closed', False),
                                    is_hidden=tt.get('is_hidden', False)
                                )
                                if topic.title:
                                    topics.append(topic)
                            if topics:
                                self._templates[user_id].append(ChatTemplate(
                                    name=t['name'],
                                    chat_name=t['chat_name'],
                                    description=t.get('description', ''),
                                    topics=topics,
                                    user_id=user_id,
                                    created_at=created_at
                                ))
                                logger.info(f"Загружен шаблон '{t['name']}' с {len(topics)} топиками")
                            else:
                                logger.warning(f"Шаблон '{t['name']}' не содержит топиков, пропускаем")
                            
                        except Exception as template_error:
                            logger.error(f"Ошибка при загрузке шаблона: {template_error}")
                            continue
                            
                except Exception as user_error:
                    logger.error(f"Ошибка при загрузке шаблонов пользователя {user_id_str}: {user_error}")
                    continue
                    
            total_templates = sum(len(templates) for templates in self._templates.values())
            logger.info(f"Загрузка завершена. Всего загружено {total_templates} шаблонов для {len(self._templates)} пользователей")
            
            # Выводим статистику по каждому пользователю
            for user_id, templates in self._templates.items():
                logger.info(f"Пользователь {user_id}: {len(templates)} шаблонов")
                for template in templates:
                    logger.info(f"  - Шаблон '{template.name}': {len(template.topics)} топиков")
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке шаблонов: {e}")
            logger.exception(e)
            self._templates = {}

    async def _save_templates(self):
        """Сохраняет шаблоны в файл"""
        try:
            logger.info("=== Начало сохранения шаблонов ===")
            logger.info(f"Путь к файлу: {self.templates_file}")
            
            # Проверяем данные перед сохранением
            if not self._templates:
                logger.warning("Нет шаблонов для сохранения!")
                return False
            
            # Подготавливаем данные для сохранения
            data = {}
            total_templates = 0
            
            for user_id, templates in self._templates.items():
                if not templates:
                    logger.warning(f"Пустой список шаблонов для пользователя {user_id}")
                    continue
                
                valid_templates = []
                for t in templates:
                    if not t.name or not t.chat_name:
                        logger.warning(f"Пропускаем шаблон с пустым именем или названием чата")
                        continue
                        
                    if not t.topics:
                        logger.warning(f"Пропускаем шаблон '{t.name}' без топиков")
                        continue
                        
                    template_data = {
                        'name': t.name,
                        'chat_name': t.chat_name,
                        'description': t.description,
                        'topics': [
                            {
                                'title': topic.title,
                                'description': topic.description or '',
                                'icon_emoji': getattr(topic, 'icon_emoji', None),
                                'icon_color': topic.icon_color if topic.icon_color is not None else 0,
                                'is_closed': topic.is_closed,
                                'is_hidden': topic.is_hidden
                            }
                            for topic in t.topics
                            if topic.title
                        ]
                    }
                    
                    if template_data['topics']:
                        valid_templates.append(template_data)
                        logger.info(f"Подготовлен шаблон '{t.name}' с {len(template_data['topics'])} топиками")
                    else:
                        logger.warning(f"Пропускаем шаблон '{t.name}' - все топики оказались невалидными")
                
                if valid_templates:
                    data[str(user_id)] = valid_templates
                    total_templates += len(valid_templates)
            
            if not data:
                logger.error("Нет валидных данных для сохранения!")
                return False
                
            # Создаем резервную копию текущего файла, если он существует
            if os.path.exists(self.templates_file):
                backup_file = f"{self.templates_file}.bak"
                logger.info(f"Создаем резервную копию: {backup_file}")
                try:
                    shutil.copy2(self.templates_file, backup_file)
                except Exception as e:
                    logger.error(f"Ошибка при создании резервной копии: {e}")
            
            # Сохраняем данные
            logger.info(f"Сохраняем {total_templates} шаблонов для {len(data)} пользователей")
            
            # Используем aiofiles для асинхронной записи
            async with aiofiles.open(self.templates_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            
            # Проверяем сохраненные данные
            try:
                async with aiofiles.open(self.templates_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    saved_data = json.loads(content)
                
                saved_templates = sum(len(templates) for templates in saved_data.values())
                if saved_templates == total_templates:
                    logger.info("=== Шаблоны успешно сохранены ===")
                    logger.info(f"Сохранено {saved_templates} шаблонов для {len(saved_data)} пользователей")
                    
                    # Удаляем резервную копию
                    if os.path.exists(f"{self.templates_file}.bak"):
                        os.remove(f"{self.templates_file}.bak")
                    return True
                else:
                    raise ValueError(f"Количество сохраненных шаблонов не совпадает: {saved_templates} != {total_templates}")
                    
            except Exception as e:
                logger.error(f"Ошибка при проверке сохраненных данных: {e}")
                # Восстанавливаем из резервной копии
                if os.path.exists(f"{self.templates_file}.bak"):
                    logger.info("Восстанавливаем данные из резервной копии")
                    os.replace(f"{self.templates_file}.bak", self.templates_file)
                return False
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении шаблонов: {e}")
            # Восстанавливаем из резервной копии
            if os.path.exists(f"{self.templates_file}.bak"):
                logger.info("Восстанавливаем данные из резервной копии")
                os.replace(f"{self.templates_file}.bak", self.templates_file)
            return False

    async def save_chat_template(self, user_id: int, template: ChatTemplate, old_name: str = None) -> bool:
        """Сохраняет шаблон чата для пользователя"""
        try:
            # Проверяем входные данные
            if not template.name or not template.chat_name or not template.topics:
                logger.error(f"Invalid template data: {template}")
                return False

            # Инициализируем список шаблонов пользователя, если его нет
            if user_id not in self._templates:
                self._templates[user_id] = []
            
            templates = self._templates[user_id]
            logger.info(f"Current templates for user {user_id}: {len(templates)}")
            
            # Если это обновление существующего шаблона
            if old_name:
                logger.info(f"Updating template '{old_name}' to '{template.name}'")
                # Находим индекс старого шаблона
                old_template_idx = next((i for i, t in enumerate(templates) if t.name == old_name), -1)
                if old_template_idx != -1:
                    # Проверяем, не конфликтует ли новое имя с другими шаблонами
                    if any(t.name == template.name and t.name != old_name for t in templates):
                        logger.error(f"Template with name '{template.name}' already exists")
                        return False
                    # Обновляем шаблон
                    template.created_at = templates[old_template_idx].created_at
                    templates[old_template_idx] = template
                    logger.info(f"Template '{old_name}' updated to '{template.name}'")
                else:
                    logger.error(f"Template '{old_name}' not found")
                    return False
            else:
                # Проверяем, нет ли шаблона с таким именем для нового шаблона
                if any(t.name == template.name for t in templates):
                    logger.error(f"Template with name '{template.name}' already exists")
                    return False
                # Добавляем новый шаблон
                template.created_at = datetime.now()
                templates.append(template)
                logger.info(f"New template '{template.name}' added")
            
            # Подготавливаем данные для сохранения
            data = {}
            for uid, user_templates in self._templates.items():
                if user_templates:  # Сохраняем только непустые списки шаблонов
                    templates_data = []
                    for t in user_templates:
                        template_dict = {
                            'name': t.name,
                            'chat_name': t.chat_name,
                            'description': t.description or '',
                            'topics': [
                                {
                                    'title': topic.title,
                                    'description': topic.description or '',
                                    'icon_emoji': getattr(topic, 'icon_emoji', None),
                                    'icon_color': topic.icon_color if topic.icon_color is not None else 0,
                                    'is_closed': topic.is_closed,
                                    'is_hidden': topic.is_hidden
                                }
                                for topic in t.topics
                                if topic.title
                            ],
                            'user_id': t.user_id,
                            'created_at': t.created_at.isoformat() if t.created_at else None
                        }
                        templates_data.append(template_dict)
                    data[str(uid)] = templates_data
            
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(self.templates_file), exist_ok=True)
            
            # Создаем временный файл рядом с основным
            temp_file = f"{self.templates_file}.tmp"
            backup_file = f"{self.templates_file}.bak"
            
            try:
                # Сохраняем во временный файл
                async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))
                
                # Создаем бэкап текущего файла, если он существует
                if os.path.exists(self.templates_file):
                    shutil.copy2(self.templates_file, backup_file)
                
                # Атомарно заменяем основной файл временным
                os.replace(temp_file, self.templates_file)
                
                # Проверяем сохраненные данные
                async with aiofiles.open(self.templates_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    saved_data = json.loads(content)
                
                # Проверяем корректность сохранения
                saved_templates = sum(len(templates) for templates in saved_data.values())
                expected_templates = sum(len(templates) for templates in self._templates.values())
                
                if saved_templates == expected_templates:
                    logger.info(f"Successfully saved {saved_templates} templates")
                    # Удаляем бэкап файл после успешного сохранения
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    return True
                else:
                    raise ValueError(f"Template count mismatch: saved {saved_templates}, expected {expected_templates}")
                    
            except Exception as save_error:
                logger.error(f"Error during save operation: {save_error}")
                # Восстанавливаем из бэкапа при ошибке
                if os.path.exists(backup_file):
                    os.replace(backup_file, self.templates_file)
                # Очищаем временные файлы
                for file in [temp_file, backup_file]:
                    if os.path.exists(file):
                        os.remove(file)
                raise
            
        except Exception as e:
            logger.error(f"Error saving template: {e}")
            return False

    async def get_user_templates(self, user_id: int) -> List[ChatTemplate]:
        """
        Получает список шаблонов пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[ChatTemplate]: Список шаблонов пользователя
        """
        logger.info(f"Получение шаблонов для пользователя {user_id}")
        templates = self._templates.get(user_id, [])
        logger.info(f"Найдено {len(templates)} шаблонов")
        for template in templates:
            logger.info(f"Шаблон: {template.name}, топиков: {len(template.topics)}")
        return templates

    async def delete_template(self, user_id: int, template_name: str, chat_name: str = None) -> bool:
        """
        Удаляет шаблон пользователя
        
        Args:
            user_id: ID пользователя
            template_name: Название шаблона
            chat_name: Название чата (опционально)
            
        Returns:
            bool: True если шаблон успешно удален
        """
        try:
            logger.info(f"[+] Удаление шаблона '{template_name}' для пользователя {user_id}")
            
            if user_id not in self._templates:
                logger.warning(f"[!] Нет шаблонов для пользователя {user_id}")
                return False
                
            templates = self._templates[user_id]
            initial_count = len(templates)
            logger.info(f"[*] Текущее количество шаблонов: {initial_count}")
            
            # Удаляем все шаблоны с совпадающим именем или названием чата
            self._templates[user_id] = [
                t for t in templates 
                if not (t.name == template_name or (chat_name and t.chat_name == chat_name))
            ]
            
            # Если список шаблонов пользователя стал пустым, удаляем и его
            if not self._templates[user_id]:
                logger.info(f"[*] Удаляем пустой список шаблонов пользователя {user_id}")
                del self._templates[user_id]
            
            # Сохраняем изменения
            logger.info("[*] Сохраняем изменения в файл...")
            
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(self.templates_file), exist_ok=True)
            
            # Подготавливаем данные для сохранения
            data = {}
            for uid, user_templates in self._templates.items():
                if user_templates:  # Сохраняем только непустые списки шаблонов
                    data[str(uid)] = [
                        {
                            'name': t.name,
                            'chat_name': t.chat_name,
                            'description': t.description or '',
                            'topics': [
                                {
                                    'title': topic.title,
                                    'description': topic.description or '',
                                    'icon_emoji': getattr(topic, 'icon_emoji', None),
                                    'icon_color': topic.icon_color if topic.icon_color is not None else 0,
                                    'is_closed': topic.is_closed,
                                    'is_hidden': topic.is_hidden
                                }
                                for topic in t.topics
                                if topic.title
                            ],
                            'user_id': t.user_id,
                            'created_at': t.created_at.isoformat() if t.created_at else None
                        }
                        for t in user_templates
                    ]
            
            # Сохраняем во временный файл
            temp_file = f"{self.templates_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Если данные корректны, заменяем основной файл
            if os.path.exists(self.templates_file):
                os.replace(self.templates_file, f"{self.templates_file}.bak")
            os.replace(temp_file, self.templates_file)
            
            final_count = len(self._templates.get(user_id, []))
            logger.info(f"[+] Шаблоны обновлены. Было: {initial_count}, стало: {final_count}")
            return True
            
        except Exception as e:
            logger.error(f"[x] Ошибка при удалении шаблона: {e}")
            logger.exception(e)
            return False

    async def create_forum_chat(self, chat_name: str, topics: List[Dict[str, str]]) -> Optional[int]:
        """
        Создает форум-чат с заданными топиками
        :param chat_name: Название чата
        :param topics: Список топиков с их названиями и описаниями
        :return: ID созданного чата или None в случае ошибки
        """
        try:
            # Создаем канал (форум-чат)
            result = await self.client(CreateChannelRequest(
                title=chat_name,
                about="Forum chat created by bot",
                megagroup=True  # Это создаст супергруппу
            ))
            
            channel_id = result.chats[0].id
            
            # Здесь должна быть логика для создания топиков
            # К сожалению, прямого метода для создания топиков через Telethon нет
            # Нужно использовать Bot API или другие методы
            
            logger.info(f"Successfully created forum chat: {chat_name} with ID: {channel_id}")
            return channel_id
            
        except Exception as e:
            logger.error(f"Error creating forum chat: {str(e)}")
            return None

    def close(self):
        """Закрывает клиент Telethon"""
        self.client.disconnect()

    async def create_forum(self, chat_data: ChatCreate, user_id: int = None, notify_func=None) -> Optional[dict]:
        """Создание форум-чата с топиками и повторными попытками установки иконок"""
        try:
            # Создаем чат через Telethon (userbot — владелец)
            result = await self.client(CreateChannelRequest(
                title=chat_data.title,
                about=chat_data.description,
                megagroup=True,
                forum=True
            ))
            channel = result.chats[0]

            # Добавляем бота в канал через InviteToChannelRequest
            bot_username = os.getenv("BOT_USERNAME")
            if bot_username:
                try:
                    await self.client(InviteToChannelRequest(channel=channel.id, users=[bot_username]))
                except Exception as e:
                    logger.warning(f"Не удалось добавить бота в канал через InviteToChannelRequest: {e}")
            else:
                logger.warning("Не указан BOT_USERNAME в .env, InviteToChannelRequest пропущен")

            # Назначаем бота админом
            bot_entity = await self.client.get_entity(bot_username)
            admin_rights = ChatAdminRights(
                add_admins=True,
                change_info=True,
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                manage_call=True,
                manage_topics=True,
                anonymous=False
            )
            await self.client(EditAdminRequest(
                channel=channel.id,
                user_id=bot_entity.id,
                admin_rights=admin_rights,
                rank="admin"
            ))

            # Получаем инвайт-ссылку через Telethon сразу после создания чата
            invite_link = None
            user_added = False
            try:
                from telethon.tl.functions.messages import ExportChatInviteRequest
                invite = await self.client(ExportChatInviteRequest(channel.id))
                invite_link = invite.link
                logger.info(f"[INVITE] Ссылка на чат: {invite_link}")
            except Exception as e:
                logger.warning(f"[INVITE] Не удалось получить инвайт-ссылку: {e}")

            # Добавляем пользователя в группу через Telethon сразу после создания чата
            if user_id:
                user_added = False
                add_error = None
                try:
                    user_entity = await self.client.get_entity(user_id)
                    await self.client(InviteToChannelRequest(channel=channel.id, users=[user_entity]))
                    user_added = True
                    logger.info(f"[ADD USER] Пользователь {user_id} добавлен в группу по user_id")
                    # Делаем пользователя админом
                    admin_result = await self.make_chat_admin(channel.id, user_id)
                    if admin_result:
                        logger.info(f"[ADMIN] Пользователь {user_id} назначен администратором группы")
                    else:
                        logger.warning(f"[ADMIN] Не удалось назначить пользователя {user_id} администратором группы")
                    if notify_func:
                        await notify_func(f"👤 Вы были добавлены в группу автоматически!")
                except Exception as e:
                    add_error = str(e)
                    logger.warning(f"[ADD USER] Не удалось добавить пользователя {user_id} по user_id: {e}")
                    # Пробуем по username, если есть
                    try:
                        from telethon.tl.types import User
                        if isinstance(user_entity, User) and user_entity.username:
                            username = user_entity.username
                            await self.client(InviteToChannelRequest(channel=channel.id, users=[username]))
                            user_added = True
                            logger.info(f"[ADD USER] Пользователь {username} добавлен в группу по username")
                            if notify_func:
                                await notify_func(f"👤 Вы были добавлены в группу автоматически!")
                        else:
                            logger.warning(f"[ADD USER] У пользователя нет username для повторной попытки")
                    except Exception as e2:
                        add_error += f" | Повторная попытка по username: {e2}"
                        logger.warning(f"[ADD USER] Не удалось добавить пользователя по username: {e2}")
                if not user_added and notify_func and invite_link:
                    await notify_func(f"❗ Не удалось добавить вас в группу автоматически. Вот ссылка для вступления: {invite_link}\nПричина: {add_error if add_error else 'Неизвестная ошибка'}\nПроверьте настройки приватности Telegram: разрешите приглашения в группы.")
            # Если пользователь не был добавлен, но есть инвайт-ссылка — отправить её (только один раз)
            elif notify_func and invite_link:
                await notify_func(f"🔗 Ссылка для вступления в группу: {invite_link}")

            # --- Создаём топики через Bot API ---
            bot_instance = Bot(token=os.getenv("BOT_TOKEN"))
            with open("working_topic_emojis.json", "r", encoding="utf-8") as f:
                emoji_map = json.load(f)
            created_topics = []
            botapi_chat_id = channel.id
            if botapi_chat_id > 0:
                botapi_chat_id = int(f'-100{botapi_chat_id}')
            
            # Функция для создания топика с повторными попытками
            async def create_topic_with_retry(topic, max_retries=3):
                for attempt in range(max_retries):
                    try:
                        # Получаем emoji_id из рабочего списка
                        emoji_id = None
                        if topic.icon_emoji:
                            with open("working_topic_emojis.json", "r", encoding="utf-8") as f:
                                emoji_map = json.load(f)
                                emoji_id = emoji_map.get(topic.icon_emoji)
                                logger.info(f"[TOPIC] Для топика '{topic.title}' иконка {topic.icon_emoji} -> emoji_id: {emoji_id}")

                        if emoji_id:
                            topic_obj = await bot_instance.create_forum_topic(
                                chat_id=botapi_chat_id,
                                name=topic.title,
                                icon_custom_emoji_id=emoji_id
                            )
                            logger.info(f"[TOPIC] Топик '{topic.title}' создан с иконкой {topic.icon_emoji}")
                        else:
                            topic_obj = await bot_instance.create_forum_topic(
                                chat_id=botapi_chat_id,
                                name=topic.title
                            )
                            logger.info(f"[TOPIC] Топик '{topic.title}' создан без иконки")
                        
                        # Сразу отправляем описание первым сообщением в топик
                        desc = topic.description if topic.description else "."
                        try:
                            await bot_instance.send_message(
                                chat_id=botapi_chat_id,
                                message_thread_id=topic_obj.message_thread_id,
                                text=desc
                            )
                        except Exception as e:
                            logger.warning(f"[TOPIC DESC] Не удалось отправить описание для топика '{topic.title}': {e}")
                        
                        return {
                            "title": topic.title,
                            "thread_id": getattr(topic_obj, 'message_thread_id', None),
                            "icon_emoji": topic.icon_emoji
                        }
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"[TOPIC] Попытка {attempt + 1} создания топика '{topic.title}' не удалась: {e}")
                            await asyncio.sleep(2)  # Ждем 2 секунды перед следующей попыткой
                        else:
                            logger.error(f"[TOPIC] Все попытки создания топика '{topic.title}' не удались: {e}")
                            return None

            # Создаем топики с повторными попытками
            for topic in chat_data.topics:
                topic_result = await create_topic_with_retry(topic)
                if topic_result:
                    created_topics.append(topic_result)
                await asyncio.sleep(1)  # Пауза между созданием топиков

            # --- После создания топиков ---
            # Проверяем, есть ли пользователь в участниках чата
            user_in_chat = False
            if user_id:
                try:
                    participants = await self.client.get_participants(channel.id)
                    user_in_chat = any(p.id == user_id for p in participants)
                    logger.info(f"[CHECK USER] Пользователь {user_id} {'есть' if user_in_chat else 'нет'} в участниках чата после создания")
                    
                    # Если пользователь в чате — делаем админом
                    if user_in_chat:
                        try:
                            admin_result = await self.make_chat_admin(channel.id, user_id)
                            if admin_result:
                                logger.info(f"[ADMIN] Пользователь {user_id} назначен админом после проверки участников")
                            else:
                                logger.warning(f"[ADMIN] Не удалось назначить пользователя {user_id} админом после проверки участников")
                        except Exception as e:
                            logger.error(f"[ADMIN] Ошибка при назначении админа: {e}")
                except Exception as e:
                    logger.warning(f"[CHECK USER] Не удалось получить участников чата: {e}")

            # Сохраняем шаблон, если это создание из шаблона
            if hasattr(chat_data, 'template_name') and chat_data.template_name:
                try:
                    template = ChatTemplate(
                        name=chat_data.template_name,
                        chat_name=chat_data.title,
                        description=chat_data.description,
                        topics=chat_data.topics,
                        user_id=user_id
                    )
                    await self.save_chat_template(user_id, template)
                    logger.info(f"[TEMPLATE] Шаблон '{chat_data.template_name}' сохранен")
                except Exception as e:
                    logger.error(f"[TEMPLATE] Ошибка при сохранении шаблона: {e}")

            # Возвращаем результат
            return {
                "chat_id": channel.id,
                "chat_name": chat_data.title,
                "description": chat_data.description,
                "user_added": user_in_chat,
                "invite_link": invite_link if not user_in_chat else None
            }

        except Exception as e:
            logger.error(f"Ошибка при создании форум-чата: {e}")
            if notify_func:
                await notify_func(f"❌ Ошибка при создании чата: {e}")
            return None
    
    async def add_user_to_chat(self, chat_id: int, user_id: int) -> bool:
        """
        Добавление пользователя в чат
        
        Args:
            chat_id: ID чата
            user_id: ID пользователя
            
        Returns:
            bool: Успешно ли добавлен пользователь
        """
        try:
            # Получаем информацию о пользователе
            user = await self.client.get_entity(user_id)
            
            # Добавляем пользователя
            await self.client.add_chat_user(chat_id, user)
            return True
            
        except Exception as e:
            logger.error(f"Error adding user to chat: {e}")
            return False
    
    async def disconnect(self):
        """Отключение клиента"""
        await self.client.disconnect()
        logger.info("Telethon client disconnected")

    async def ensure_client(self) -> bool:
        """Проверяет и устанавливает подключение клиента"""
        try:
            if self.client is None:
                logger.info("[+] Создаем новый клиент Telegram...")
                self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            
            if not self.client.is_connected():
                logger.info("[+] Подключаемся к Telegram...")
                await self.client.connect()
                
            # Ждем немного для установки соединения
            await asyncio.sleep(1)
            
            if not self.client.is_connected():
                logger.error("[x] Не удалось установить соединение")
                return False
            
            if not await self.client.is_user_authorized():
                logger.info("[!] Клиент не авторизован, начинаем авторизацию...")
                try:
                    # Если это бот, пробуем использовать токен
                    if self.session_name.endswith('_bot'):
                        await self.client.start(bot_token=os.getenv("BOT_TOKEN"))
                    else:
                        # Для пользовательской сессии используем номер телефона
                        phone = os.getenv("PHONE")
                        if not phone:
                            logger.error("[x] Не указан номер телефона в .env файле")
                            return False
                            
                        logger.info(f"[+] Отправляем код на номер {phone}")
                        await self.client.start(phone=phone)
                        
                    await asyncio.sleep(1)  # Ждем завершения авторизации
                    
                    if not await self.client.is_user_authorized():
                        logger.error("[x] Не удалось авторизоваться")
                        return False
                        
                    logger.info("[+] Авторизация успешно завершена")
                except Exception as e:
                    logger.error(f"[x] Ошибка при авторизации: {str(e)}")
                    logger.debug(f"Детали ошибки:", exc_info=True)
                    return False
            
            # Проверяем, что все в порядке
            me = await self.client.get_me()
            if not me:
                logger.error("[x] Не удалось получить информацию о пользователе")
                return False
            
            logger.info(f"[+] Клиент Telethon готов к работе (ID: {me.id}, {'бот' if me.bot else 'пользователь'})")
            
            # Принудительно загружаем шаблоны
            await self._load_templates_async()
            
            return True
            
        except Exception as e:
            logger.error(f"[x] Ошибка при проверке клиента: {str(e)}")
            logger.debug("Детали ошибки:", exc_info=True)
            return False

    async def _load_templates_async(self):
        """Асинхронно загружает шаблоны из файла"""
        try:
            logger.info("[+] Начало загрузки шаблонов")
            self._templates = {}  # Очищаем словарь перед загрузкой
            
            # Проверяем существование файла и директории
            if not os.path.exists(os.path.dirname(self.templates_file)):
                logger.info(f"[+] Создаем директорию для шаблонов: {os.path.dirname(self.templates_file)}")
                os.makedirs(os.path.dirname(self.templates_file), exist_ok=True)
            
            if not os.path.exists(self.templates_file):
                logger.info(f"[!] Файл шаблонов {self.templates_file} не существует, создаем новый")
                async with aiofiles.open(self.templates_file, 'w', encoding='utf-8') as f:
                    await f.write('{}')
                return
            
            # Читаем файл
            try:
                async with aiofiles.open(self.templates_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    
                if not content.strip():
                    logger.warning("[!] Файл шаблонов пуст")
                    return
                
                data = json.loads(content)
                
                if not isinstance(data, dict):
                    logger.error(f"[x] Некорректный формат файла шаблонов: {type(data)}")
                    return
                
                # Загружаем шаблоны
                for user_id_str, templates in data.items():
                    try:
                        user_id = int(user_id_str)
                        self._templates[user_id] = []
                        
                        for t in templates:
                            try:
                                # Преобразуем строку даты в объект datetime
                                created_at = None
                                if 'created_at' in t and t['created_at']:
                                    try:
                                        created_at = datetime.fromisoformat(t['created_at'])
                                    except ValueError as e:
                                        logger.warning(f"[!] Не удалось преобразовать дату создания: {e}")
                                
                                topics = []
                                for tt in t.get('topics', []):
                                    topic = Topic(
                                        title=tt['title'],
                                        description=tt.get('description', ''),
                                        icon_emoji=tt.get('icon_emoji'),
                                        icon_color=tt.get('icon_color', 0),
                                        is_closed=tt.get('is_closed', False),
                                        is_hidden=tt.get('is_hidden', False)
                                    )
                                    if topic.title:
                                        topics.append(topic)
                                if topics:
                                    self._templates[user_id].append(ChatTemplate(
                                        name=t['name'],
                                        chat_name=t['chat_name'],
                                        description=t.get('description', ''),
                                        topics=topics,
                                        user_id=user_id,
                                        created_at=created_at
                                    ))
                                    logger.info(f"[+] Загружен шаблон '{t['name']}' с {len(topics)} топиками")
                                else:
                                    logger.warning(f"[!] Пропущен шаблон '{t['name']}' без топиков")
                                    
                            except Exception as template_error:
                                logger.error(f"[x] Ошибка при загрузке шаблона: {template_error}")
                                continue
                                
                    except Exception as user_error:
                        logger.error(f"[x] Ошибка при загрузке шаблонов пользователя {user_id_str}: {user_error}")
                        continue
                
                # Выводим статистику
                total_templates = sum(len(templates) for templates in self._templates.values())
                logger.info(f"[+] Загрузка завершена. Всего загружено {total_templates} шаблонов для {len(self._templates)} пользователей")
                
            except json.JSONDecodeError as e:
                logger.error(f"[x] Ошибка при разборе JSON: {e}")
                logger.error(f"[x] Содержимое файла: {content[:200]}...")
                return
                
        except Exception as e:
            logger.error(f"[x] Ошибка при загрузке шаблонов: {e}")
            logger.exception(e)
            self._templates = {} 

    async def make_chat_admin(self, chat_id: int, user_id: int) -> bool:
        """Make user an admin in the chat, with retries if user not found immediately."""
        import asyncio
        chat = await self.client.get_entity(chat_id)
        user = None
        for attempt in range(3):
            try:
                participants = await self.client.get_participants(chat)
                user = next((p for p in participants if p.id == user_id), None)
                if user:
                    break
                logger.warning(f'[make_chat_admin] Attempt {attempt+1}: User {user_id} not found, waiting 5 seconds...')
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error getting user from participants: {e}")
                return False
        if not user:
            logger.error(f"User {user_id} not found in chat participants after 3 attempts")
            return False

        admin_rights = ChatAdminRights(
            add_admins=True,
            change_info=True,
            post_messages=True,
            edit_messages=True,
            delete_messages=True,
            ban_users=True,
            invite_users=True,
            pin_messages=True,
            manage_call=True,
            manage_topics=True,
            anonymous=False
        )
        try:
            await self.client(EditAdminRequest(
                chat,
                user,
                admin_rights,
                "Admin"
            ))
            return True
        except Exception as e:
            logger.error(f"Error making user admin: {str(e)}", exc_info=True)
            return False

    async def transfer_chat_ownership(self, chat_id: int, user_id: int) -> bool:
        """
        Передача прав владельца чата другому пользователю
        
        Args:
            chat_id: ID чата
            user_id: ID нового владельца
            
        Returns:
            bool: Успешно ли переданы права
        """
        try:
            logger.info(f"Transferring chat {chat_id} ownership to user {user_id}")
            
            # Получаем сущность чата
            channel = await self.client.get_entity(chat_id)
            if not channel:
                logger.error(f"Channel {chat_id} not found")
                return False
            
            # Получаем сущность пользователя
            user = await self.client.get_entity(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            # Передаем права владельца
            await self.client(EditCreatorRequest(
                channel=channel,
                user_id=user
            ))
            
            logger.info(f"Successfully transferred chat {chat_id} ownership to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error transferring chat ownership: {e}", exc_info=True)
            return False 

    async def get_forum_topic_icons(self):
        """Заглушка: возвращает список из EMOJI_ID_MAP (emoji, id)"""
        return list(EMOJI_ID_MAP.items())

    async def edit_forum_topic_icon(self, chat_id: int, topic_id: int, icon_emoji_id: int) -> bool:
        """Сменить иконку топика (emoji) через Telethon (raw TL)"""
        await self.ensure_client()
        try:
            from telethon.tl.functions.channels import EditForumTopicRequest
            await self.client(EditForumTopicRequest(
                channel=chat_id,
                topic_id=topic_id,
                icon_emoji_id=icon_emoji_id
            ))
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Ошибка смены иконки топика (EditForumTopicRequest): {e}")
            return False 

    async def is_user_in_chat(self, chat_id: int, user_id: int) -> bool:
        """Проверяет, состоит ли пользователь с user_id в чате chat_id"""
        try:
            participants = await self.client.get_participants(chat_id)
            return any(p.id == user_id for p in participants)
        except Exception as e:
            # Можно залогировать ошибку
            return False 