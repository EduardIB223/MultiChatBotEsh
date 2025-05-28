from aiogram import Router, F, Dispatcher
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
from typing import List, Union
import logging
import os
import io
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

from models.schemas import ChatCreate, ChatTemplate, Topic
from services.telethon_service import TelethonService, BotApiService
from services.database import DatabaseService
from states import ChatStates, TemplateCreation, TemplateManagement, ChatCreation
from middlewares import TelethonMiddleware
from keyboards.emoji import get_emoji_keyboard
from aiogram import Bot
from telethon.tl.functions.channels import InviteToChannelRequest, EditAdminRequest
from telethon.tl.types import ChatAdminRights

logger = logging.getLogger(__name__)

# Configure logging
logger.setLevel(logging.DEBUG)

# Константы для валидации
MAX_CHAT_NAME_LENGTH = 128
MAX_DESCRIPTION_LENGTH = 255
MAX_TOPIC_NAME_LENGTH = 128

def format_template_preview(template_name: str, chat_name: str, topics: list, chat_description: str = None) -> str:
    """Форматирует предпросмотр шаблона"""
    preview = f"Название шаблона: {template_name}\n"
    preview += f"Название чата: {chat_name}\n"
    if chat_description and chat_description.strip() and chat_description != ".":
        preview += f"Описание: {chat_description}\n"
    preview += f"\nТопики ({len(topics)}):\n"
    for i, topic in enumerate(topics, 1):
        if isinstance(topic, dict):
            emoji = topic.get('icon_emoji') or ''
            title = topic.get('title', '')
            description = topic.get('description', '')
        else:
            emoji = getattr(topic, 'icon_emoji', '') or ''
            title = getattr(topic, 'title', '')
            description = getattr(topic, 'description', '')
        # Формат: 1. <emoji> Название топика: <название>\n   Описание топика: <описание>
        line = f"{i}. "
        if emoji:
            line += f"{emoji} "
        line += f"Название топика: {title}"
        preview += line
        if description and description != '.':
            preview += f"\n   Описание топика: {description}"
        preview += "\n"
    return preview

def get_template_completion_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру для завершения создания шаблона"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡️ Создать чат")],
            [KeyboardButton(text="💾 Сохранить шаблон")],
            [KeyboardButton(text="🚀 Сохранить и создать")],
            [KeyboardButton(text="✏️ Редактировать")],
            [KeyboardButton(text="❌ Отменить")]
        ],
        resize_keyboard=True
    )

def get_edit_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру для редактирования шаблона"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Изменить название шаблона")],
            [KeyboardButton(text="💬 Изменить название чата")],
            [KeyboardButton(text="📄 Изменить описание чата")],
            [KeyboardButton(text="📑 Изменить топики")],
            [KeyboardButton(text="💾 Сохранить изменения")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

def get_topic_edit_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру для редактирования топиков"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Изменить топик")],
            [KeyboardButton(text="🗑 Удалить топик")],
            [KeyboardButton(text="➕ Добавить топик")],
            [KeyboardButton(text="✅ Завершить изменения")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def validate_chat_name(name: str) -> tuple[bool, str]:
    """Проверяет название чата на соответствие ограничениям"""
    if not name:
        return False, "Название чата не может быть пустым"
    if len(name) > MAX_CHAT_NAME_LENGTH:
        return False, f"Название чата не может быть длиннее {MAX_CHAT_NAME_LENGTH} символов"
    return True, ""

def validate_description(description: str) -> tuple[bool, str]:
    """Проверяет описание на соответствие ограничениям"""
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return False, f"Описание не может быть длиннее {MAX_DESCRIPTION_LENGTH} символов"
    return True, ""

def validate_topic_name(name: str) -> tuple[bool, str]:
    """Проверяет название топика на соответствие ограничениям"""
    if not name:
        return False, "Название топика не может быть пустым"
    if len(name) > MAX_TOPIC_NAME_LENGTH:
        return False, f"Название топика не может быть длиннее {MAX_TOPIC_NAME_LENGTH} символов"
    return True, ""

# Создаем роутер на уровне модуля
router = Router(name=__name__)

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает основную клавиатуру бота"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚡️ Создать форум-чат/шаблон")],
            [KeyboardButton(text="📁 Мои шаблоны")]
        ],
        resize_keyboard=True
    )

def get_template_actions_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру действий с шаблоном"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Редактировать")],
            [KeyboardButton(text="🚀 Создать чат"), KeyboardButton(text="❌ Удалить")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()  # Clear any previous state
    await message.answer(
        "👋 Привет! Я бот для создания и управления форум-чатами.\n\n"
        "С моей помощью вы можете:\n"
        "• Создавать форум-чаты с топиками\n"
        "• Сохранять шаблоны чатов\n"
        "• Использовать готовые шаблоны\n\n"
        "Выберите действие в меню ниже:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(TemplateCreation.waiting_topic_emoji)
async def process_topic_emoji_selection(callback: CallbackQuery, state: FSMContext):
    if not callback.data or not callback.data.startswith("emoji_"):
        await callback.answer("Пожалуйста, выберите эмодзи с клавиатуры.", show_alert=True)
        return
    emoji = callback.data.replace("emoji_", "")
    data = await state.get_data()
    topics = data.get("topics", [])
    description = data.get("current_topic_description", "")
    # Если описание пустое, ставим точку
    if not description:
        description = "."
    new_topic = {
        "title": data["current_topic_name"],
        "description": description,
        "icon_emoji": emoji,
        "icon_color": None,
        "is_closed": False,
        "is_hidden": False
    }
    topics.append(new_topic)
    await state.update_data(topics=topics)
    preview = format_template_preview(data["template_name"], data["chat_name"], topics, data.get("chat_description", ""))
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        f"{preview}\n\nВыберите действие:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить топик"), KeyboardButton(text="✅ Завершить")],
                [KeyboardButton(text="❌ Отменить")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateCreation.topics)
    return

@router.message(TemplateCreation.waiting_topic_emoji, F.text == ".")
async def skip_topic_emoji_creation(message: Message, state: FSMContext):
    data = await state.get_data()
    topics = data.get("topics", [])
    new_topic = {
        "title": data["current_topic_name"],
        "description": data.get("current_topic_description", ""),
        "icon_emoji": None,
        "icon_color": None,
        "is_closed": False,
        "is_hidden": False
    }
    topics.append(new_topic)
    await state.update_data(topics=topics)
    preview = format_template_preview(data["template_name"], data["chat_name"], topics, data.get("chat_description", ""))
    await message.answer(
        f"{preview}\n\nВыберите действие:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить топик"), KeyboardButton(text="✅ Завершить")],
                [KeyboardButton(text="❌ Отменить")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateCreation.topics)

@router.message(F.text == "📁 Мои шаблоны")
async def show_templates(message: Message, state: FSMContext, telethon: TelethonService):
    templates = await telethon.get_user_templates(message.from_user.id)
    # Фильтруем по уникальному имени шаблона (или паре name+chat_name)
    unique = {}
    for t in templates:
        key = (t.name, t.chat_name)
        if key not in unique:
            unique[key] = t
    templates = list(unique.values())
    if not templates:
        await message.answer(
            "У вас пока нет сохраненных шаблонов.\nСоздайте новый шаблон с помощью кнопки '🛠 Создать шаблон'",
            reply_markup=get_main_keyboard()
        )
        return
    templates_text = "Ваши шаблоны:\n\n"
    for template in templates:
        templates_text += f"{format_template_preview(template.name, template.chat_name, template.topics, template.description)}\n"
    await message.answer(
        templates_text + "\nВыберите шаблон для управления, отправив его название.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=template.name)] for template in templates
            ] + [[KeyboardButton(text="🔙 В главное меню")]],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateManagement.viewing_templates)

@router.message(TemplateManagement.viewing_templates)
async def handle_template_selection(message: Message, state: FSMContext, telethon: TelethonService):
    if message.text == "🔙 В главное меню":
        await state.clear()
        await message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return

    templates = await telethon.get_user_templates(message.from_user.id)
    selected_template = next((t for t in templates if t.name == message.text), None)
    if not selected_template:
        await message.answer(
            "❌ Шаблон не найден. Пожалуйста, выберите шаблон из списка.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=template.name)] for template in templates
                ] + [[KeyboardButton(text="🔙 В главное меню")]],
                resize_keyboard=True
            )
        )
        return
    await state.update_data(selected_template=selected_template.dict(), original_template_name=selected_template.name)
    # Вместо цикла по топикам выводим предпросмотр всего шаблона
    topics_text = format_template_preview(
        selected_template.name,
        selected_template.chat_name,
        selected_template.topics,
        selected_template.description
    )
    await message.answer(
        f"{topics_text}\nВыберите действие для шаблона «{selected_template.name}»:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚀 Создать чат")],
                [KeyboardButton(text="✏️ Редактировать"), KeyboardButton(text="❌ Удалить")],
                [KeyboardButton(text="🔙 Назад к списку")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateManagement.selected_template)

@router.message(TemplateManagement.selected_template)
async def handle_template_actions(message: Message, state: FSMContext, telethon: TelethonService):
    """Обработчик действий с выбранным шаблоном"""
    if message.text == "🔙 Назад к списку":
        # Возвращаемся к списку шаблонов
        await show_templates(message, state, telethon)
        return

    if message.text == "❌ Удалить":
        # Получаем данные шаблона из состояния
        data = await state.get_data()
        template = data.get("selected_template")
        if not template:
            await message.answer("❌ Ошибка: шаблон не найден", reply_markup=get_main_keyboard())
            await state.clear()
            return
            
        # Удаляем шаблон
        if await telethon.delete_template(message.from_user.id, template["name"]):
            await message.answer(
                f"✅ Шаблон '{template['name']}' успешно удален!",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "❌ Не удалось удалить шаблон. Попробуйте позже.",
                reply_markup=get_main_keyboard()
            )
        await state.clear()
        return

    elif message.text == "🚀 Создать чат":
        # Получаем данные шаблона из состояния
        data = await state.get_data()
        template = data.get("selected_template")
        if not template:
            await message.answer("❌ Ошибка: шаблон не найден", reply_markup=get_main_keyboard())
            await state.clear()
            return

        # Создаем чат из шаблона
        try:
            chat_data = ChatCreate(
                title=template["chat_name"],
                description=template["description"],
                topics=[Topic(**t) for t in template["topics"]]
            )
            
            # Отправляем сообщение о начале создания
            status_msg = await message.answer("⏳ Создаю чат из шаблона...")
            
            # Создаем форум-чат через Telethon
            result = await telethon.create_forum(chat_data, message.from_user.id)
            if result:
                if result.get('user_added'):
                    await status_msg.edit_text(
                        f"✅ Чат успешно создан! Вы уже добавлены и назначены админом. (подождите 1 минуту до создания всех топиков)\n\n"
                        f"Название: {result['chat_name']}"
                    )
                    await state.clear()
                    await cmd_start(message, state)
                    return
                else:
                    invite_link = result.get('invite_link')
                    await status_msg.edit_text(
                        f"✅ Чат успешно создан!\n\n"
                        f"🔗 <b>Ссылка для входа:</b> {invite_link}\n\n"
                        f"<b>Внимание:</b> Вы не были автоматически добавлены в чат (лимит Telegram или настройки приватности).\n"
                        f"1. Перейдите по ссылке выше и войдите в чат.\n"
                        f"2. После входа нажмите кнопку ниже, чтобы стать админом.",
                        reply_markup=InlineKeyboardMarkup(
                            inline_keyboard=[
                                [InlineKeyboardButton(text="🔑 Сделать меня админом", callback_data="make_admin")]
                            ]
                        ),
                        parse_mode="HTML"
                    )
                    await state.update_data(created_chat_id=result['chat_id'], invite_link=invite_link)
                    return
            else:
                await status_msg.edit_text(
                    "❌ Не удалось создать чат. Попробуйте позже.",
                    reply_markup=None
                )
                await state.clear()
        except Exception as e:
            logger.error(f"Error creating chat from template: {e}")
            await message.answer(
                "❌ Произошла ошибка при создании чата.",
                reply_markup=get_main_keyboard()
            )
            await state.clear()
        return

    elif message.text == "✏️ Редактировать":
        # Логика редактирования шаблона
        data = await state.get_data()
        template = data.get("selected_template")
        if not template:
            await message.answer("❌ Ошибка: шаблон не найден", reply_markup=get_main_keyboard())
            await state.clear()
            return
            
        await message.answer(
            "Выберите, что хотите отредактировать:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="📝 Изменить название шаблона")],
                    [KeyboardButton(text="💬 Изменить название чата")],
                    [KeyboardButton(text="📄 Изменить описание чата")],
                    [KeyboardButton(text="📑 Изменить топики")],
                    [KeyboardButton(text="🔙 Назад")]
                ],
                resize_keyboard=True
            )
        )
        await state.set_state(TemplateManagement.editing)
        return

    # Если пришло неизвестное действие
    await message.answer(
        "❌ Неизвестное действие. Пожалуйста, используйте кнопки меню.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🚀 Создать чат")],
                [KeyboardButton(text="✏️ Редактировать"), KeyboardButton(text="❌ Удалить")],
                [KeyboardButton(text="🔙 Назад к списку")]
            ],
            resize_keyboard=True
        )
    )

@router.message(F.text == "🛠 Создать шаблон")
async def create_template_start(message: Message, state: FSMContext):
    """Начинает процесс создания шаблона"""
    await state.set_state(TemplateCreation.waiting_template_name)
    await message.answer(
        "Введите название шаблона:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❌ Отменить")]
            ],
            resize_keyboard=True
        )
    )

@router.message(TemplateCreation.waiting_template_name)
async def process_template_name(message: Message, state: FSMContext):
    """Обработка названия шаблона"""
    logger.info(f"Обработка названия шаблона: {message.text}")
    
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "Создание шаблона отменено.",
            reply_markup=get_main_keyboard()
        )
        return

    await state.update_data(template_name=message.text)
    await state.set_state(TemplateCreation.waiting_name)
    await message.answer(
        "Отлично! Теперь введите название чата, который будет создан по этому шаблону:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❌ Отменить")]
            ],
            resize_keyboard=True
        )
    )

@router.message(TemplateCreation.waiting_name)
async def process_chat_name_for_template(message: Message, state: FSMContext):
    """Обработка названия чата для шаблона"""
    logger.info(f"Обработка названия чата для шаблона: {message.text}")
    
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "Создание шаблона отменено.",
            reply_markup=get_main_keyboard()
        )
        return

    await state.update_data(chat_name=message.text)
    await state.set_state(TemplateCreation.waiting_description)
    await message.answer(
        "Введите описание чата (или нажмите «⏩ Пропустить»):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="⏩ Пропустить")],
                [KeyboardButton(text="❌ Отменить")]
            ],
            resize_keyboard=True
        )
    )

@router.message(TemplateCreation.waiting_description)
async def process_template_description(message: Message, state: FSMContext):
    """Обработка описания чата для шаблона"""
    logger.info(f"Обработка описания чата для шаблона: {message.text}")
    
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "Создание шаблона отменено.",
            reply_markup=get_main_keyboard()
        )
        return

    description = "" if message.text == "⏩ Пропустить" else message.text
    await state.update_data(chat_description=description, topics=[])
    await state.set_state(TemplateCreation.waiting_topic_name)
    
    await message.answer(
        "Введите название для первого топика:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❌ Отменить")]
            ],
            resize_keyboard=True
        )
    )

@router.message(TemplateCreation.waiting_topic_name)
async def process_template_topic(message: Message, state: FSMContext):
    """Обработчик создания топика для шаблона"""
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "Создание шаблона отменено.",
            reply_markup=get_main_keyboard()
        )
        return

    # Проверяем название топика
    is_valid, error_message = validate_topic_name(message.text)
    if not is_valid:
        await message.answer(
            f"❌ {error_message}\n\nПожалуйста, введите другое название:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="❌ Отменить")]],
                resize_keyboard=True
            )
        )
        return

    # Сохраняем название топика
    await state.update_data(current_topic_name=message.text)
    
    # Запрашиваем описание топика
    await message.answer(
        "Введите описание топика (или отправьте точку для пропуска):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=".")], [KeyboardButton(text="❌ Отменить")]],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateCreation.waiting_topic_description)

@router.message(TemplateCreation.waiting_topic_description)
async def process_template_topic_description(message: Message, state: FSMContext):
    """Обработчик описания топика для шаблона"""
    if message.text == "❌ Отменить":
        await state.clear()
        await message.answer(
            "Создание шаблона отменено.",
            reply_markup=get_main_keyboard()
        )
        return
    await state.update_data(current_topic_description=("" if message.text == "." else message.text))
    from handlers.forum_handlers import load_working_emojis
    emoji_map = load_working_emojis()
    if not emoji_map:
        await message.answer("❌ Рабочий список значков не найден. Пожалуйста, обновите его командой /refresh_topic_emojis")
        await state.clear()
        return
    all_emojis = list(emoji_map.keys())
    # Ограничиваем максимум 80 emoji (5 сообщений по 16)
    max_emojis = 80
    all_emojis = all_emojis[:max_emojis]
    chunk_size = 16
    row_size = 8
    for i in range(0, len(all_emojis), chunk_size):
        builder = InlineKeyboardBuilder()
        chunk = all_emojis[i:i+chunk_size]
        for j in range(0, len(chunk), row_size):
            row = chunk[j:j+row_size]
            for emoji in row:
                builder.button(text=emoji, callback_data=f"emoji_{emoji}")
            builder.adjust(row_size)
        await message.answer(f"Выберите значок (эмодзи) для топика (часть {i//chunk_size+1}):", reply_markup=builder.as_markup())
    await state.set_state(TemplateCreation.waiting_topic_emoji)

@router.message(TemplateCreation.topics, F.text == "➕ Добавить топик")
async def add_new_topic(message: Message, state: FSMContext):
    await message.answer(
        "Введите название для нового топика:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отменить")]],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateCreation.waiting_topic_name)

@router.message(TemplateCreation.topics, F.text == "✅ Завершить")
async def finish_topics(message: Message, state: FSMContext):
    data = await state.get_data()
    preview = format_template_preview(data["template_name"], data["chat_name"], data["topics"])
    await message.answer(
        f"✅ Шаблон создан!\n\n{preview}\n\nВыберите действие:",
        reply_markup=get_template_completion_keyboard()
    )
    await state.set_state(TemplateManagement.completed)

@router.message(TemplateManagement.completed, F.text.func(lambda t: t and t.strip() == "⚡️ Создать чат"))
async def create_chat_from_template(message: Message, state: FSMContext, telethon: TelethonService, bot: Bot):
    data = await state.get_data()
    try:
        template_name = data.get("template_name")
        chat_name = data.get("chat_name")
        chat_description = data.get("chat_description", "")
        topics = data.get("topics", [])
        if not chat_name or not topics:
            await message.answer("❌ Ошибка: не хватает данных для создания чата.", reply_markup=get_main_keyboard())
            await state.clear()
            return
        clean_topics = []
        for t in topics:
            t = dict(t) if isinstance(t, dict) else t.dict()
            if t.get("description", "") == ".":
                t["description"] = ""
            clean_topics.append(Topic(**t))
        chat_data = ChatCreate(
            title=chat_name,
            description=chat_description,
            topics=clean_topics
        )
        status_msg = await message.answer("⏳ Создаю чат из шаблона...")
        result = await telethon.create_forum(chat_data, message.from_user.id)
        if result:
            if result.get('user_added'):
                await status_msg.edit_text(
                    f"✅ Чат успешно создан! Вы уже добавлены и назначены админом. (подождите 1 минуту до создания всех топиков)\n\n"
                    f"Название: {result['chat_name']}"
                )
                await state.clear()
                await cmd_start(message, state)
                return
            else:
                invite_link = result.get('invite_link')
                await status_msg.edit_text(
                    f"✅ Чат успешно создан!\n\n"
                    f"🔗 <b>Ссылка для входа:</b> {invite_link}\n\n"
                    f"<b>Внимание:</b> Вы не были автоматически добавлены в чат (лимит Telegram или настройки приватности).\n"
                    f"1. Перейдите по ссылке выше и войдите в чат.\n"
                    f"2. После входа нажмите кнопку ниже, чтобы стать админом.",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔑 Сделать меня админом", callback_data="make_admin")]
                        ]
                    ),
                    parse_mode="HTML"
                )
                await state.update_data(created_chat_id=result['chat_id'], invite_link=invite_link)
                return
        else:
            await status_msg.edit_text(
                "❌ Не удалось создать чат. Попробуйте позже.",
                reply_markup=None
            )
            await state.clear()
    except Exception as e:
        logger.error(f"Error creating chat from template (completed menu): {e}")
        await message.answer(
            "❌ Произошла ошибка при создании чата.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()

@router.message(TemplateManagement.completed, F.text.func(lambda t: t and t.strip() == "💾 Сохранить шаблон"))
async def save_template(message: Message, state: FSMContext, telethon: TelethonService):
    data = await state.get_data()
    template = data.get("selected_template") or data
    template_name = template.get("template_name") or template.get("name")
    chat_name = template.get("chat_name")
    chat_description = template.get("chat_description") or template.get("description")
    topics = template.get("topics")
    if not template_name or not chat_name or not topics or not isinstance(topics, list) or len(topics) == 0:
        await message.answer("❌ Не хватает данных для сохранения шаблона. Похоже, шаблон повреждён.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    try:
        chat_template = ChatTemplate(
            name=template_name,
            chat_name=chat_name,
            description=chat_description,
            topics=[Topic(**t) if isinstance(t, dict) else t for t in topics],
            user_id=message.from_user.id
        )
        # Если редактируется существующий шаблон, передаём original_template_name
        if "selected_template" in data:
            old_name = data.get("original_template_name") or data["selected_template"].get("name") or data["selected_template"].get("template_name")
            result = await telethon.save_chat_template(
                user_id=message.from_user.id,
                template=chat_template,
                old_name=old_name
            )
        else:
            result = await telethon.save_chat_template(
                user_id=message.from_user.id,
                template=chat_template
            )
        if result:
            await message.answer("Шаблон сохранён!", reply_markup=get_main_keyboard())
        else:
            await message.answer("❌ Не удалось сохранить шаблон.", reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Error saving template: {e}")
        await message.answer("❌ Произошла ошибка при сохранении шаблона.", reply_markup=get_main_keyboard())
    await state.clear()

@router.message(TemplateManagement.completed, F.text.func(lambda t: t and t.strip() == "🚀 Сохранить и создать"))
async def save_and_create(message: Message, state: FSMContext, telethon: TelethonService):
    import logging
    logger = logging.getLogger(__name__)
    data = await state.get_data()
    template = data.get("selected_template") or data
    template_name = template.get("template_name") or template.get("name")
    chat_name = template.get("chat_name")
    chat_description = template.get("chat_description") or template.get("description")
    topics = template.get("topics")
    if not template_name or not chat_name or not topics or not isinstance(topics, list) or len(topics) == 0:
        await message.answer("❌ Не хватает данных для сохранения шаблона. Похоже, шаблон повреждён.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    # Сохраняем шаблон
    try:
        chat_template = ChatTemplate(
            name=template_name,
            chat_name=chat_name,
            description=chat_description,
            topics=[Topic(**t) if isinstance(t, dict) else t for t in topics],
            user_id=message.from_user.id
        )
        if "selected_template" in data:
            old_name = data["selected_template"].get("name") or data["selected_template"].get("template_name")
            save_result = await telethon.save_chat_template(
                user_id=message.from_user.id,
                template=chat_template,
                old_name=old_name
            )
        else:
            save_result = await telethon.save_chat_template(
                user_id=message.from_user.id,
                template=chat_template
            )
        if not save_result:
            logger.error(f"[save_and_create] Не удалось сохранить шаблон '{template_name}' для пользователя {message.from_user.id}")
            await message.answer("❌ Не удалось сохранить шаблон. Возможно, шаблон с таким именем уже существует или произошла ошибка.", reply_markup=get_main_keyboard())
            await state.clear()
            return
    except Exception as e:
        logger.error(f"[save_and_create] Ошибка при сохранении шаблона: {e}")
        await message.answer(f"❌ Произошла ошибка при сохранении шаблона: {e}", reply_markup=get_main_keyboard())
        await state.clear()
        return
    # Создаём чат
    try:
        clean_topics = []
        for t in topics:
            t = dict(t) if isinstance(t, dict) else t.dict()
            if t.get("description", "") == ".":
                t["description"] = ""
            clean_topics.append(Topic(**t))
        chat_data = ChatCreate(
            title=chat_name,
            description=chat_description,
            topics=clean_topics
        )
        status_msg = await message.answer("⏳ Создаю чат из шаблона...")
        result = await telethon.create_forum(chat_data, message.from_user.id)
        if result:
            if result.get('user_added'):
                await status_msg.edit_text(
                    f"✅ Чат успешно создан! Вы уже добавлены и назначены админом. (подождите 1 минуту до создания всех топиков)\n\n"
                    f"Название: {result['chat_name']}"
                )
                await state.clear()
                await cmd_start(message, state)
                return
            else:
                invite_link = result.get('invite_link')
                await status_msg.edit_text(
                    f"✅ Чат успешно создан!\n\n"
                    f"🔗 <b>Ссылка для входа:</b> {invite_link}\n\n"
                    f"<b>Внимание:</b> Вы не были автоматически добавлены в чат (лимит Telegram или настройки приватности).\n"
                    f"1. Перейдите по ссылке выше и войдите в чат.\n"
                    f"2. После входа нажмите кнопку ниже, чтобы стать админом.",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="🔑 Сделать меня админом", callback_data="make_admin")]
                        ]
                    ),
                    parse_mode="HTML"
                )
                await state.update_data(created_chat_id=result['chat_id'], invite_link=invite_link)
                return
        else:
            logger.error(f"[save_and_create] Не удалось создать чат для шаблона '{template_name}' пользователя {message.from_user.id}")
            await status_msg.edit_text(
                "❌ Не удалось создать чат. Попробуйте позже.",
                reply_markup=None
            )
            await state.clear()
    except Exception as e:
        logger.error(f"[save_and_create] Ошибка при создании чата: {e}")
        await message.answer(f"❌ Произошла ошибка при создании чата: {e}", reply_markup=get_main_keyboard())
        await state.clear()

@router.message(TemplateManagement.completed, F.text.func(lambda t: t and t.strip() == "✏️ Редактировать"))
async def edit_template_completed(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(
        "Выберите, что хотите отредактировать:",
        reply_markup=get_edit_keyboard()
    )
    await state.set_state(TemplateManagement.editing)

@router.message(TemplateManagement.completed, F.text.func(lambda t: t and t.strip() == "❌ Отменить"))
async def cancel_template_completed(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=get_main_keyboard())

# --- Редактирование топиков в TemplateManagement.editing_topics ---

@router.message(TemplateManagement.editing_topics, F.text == "➕ Добавить топик")
async def add_topic_in_edit(message: Message, state: FSMContext):
    await state.set_state(TemplateManagement.adding_topic_name)
    await message.answer(
        "Введите название для нового топика:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отменить добавление")]],
            resize_keyboard=True
        )
    )

@router.message(TemplateManagement.adding_topic_name)
async def process_new_topic_name_in_edit(message: Message, state: FSMContext):
    if message.text == "❌ Отменить добавление":
        await handle_edit_topics(message, state)
        return
    is_valid, error_message = validate_topic_name(message.text)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите другое название:")
        return
    await state.update_data(current_topic_name=message.text)
    await state.set_state(TemplateManagement.adding_topic_description)
    await message.answer(
        "Введите описание топика (или отправьте точку для пропуска):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=".")], [KeyboardButton(text="❌ Отменить добавление")]],
            resize_keyboard=True
        )
    )

@router.message(TemplateManagement.adding_topic_description)
async def process_new_topic_description_in_edit(message: Message, state: FSMContext):
    if message.text == "❌ Отменить добавление":
        await handle_edit_topics(message, state)
        return
    await state.update_data(current_topic_description=(message.text if message.text != "." else ""))
    from handlers.forum_handlers import load_working_emojis
    emoji_map = load_working_emojis()
    if not emoji_map:
        await message.answer("❌ Рабочий список значков не найден. Пожалуйста, обновите его командой /refresh_topic_emojis")
        await state.clear()
        return
    all_emojis = list(emoji_map.keys())
    max_emojis = 80
    all_emojis = all_emojis[:max_emojis]
    chunk_size = 16
    row_size = 8
    for i in range(0, len(all_emojis), chunk_size):
        builder = InlineKeyboardBuilder()
        chunk = all_emojis[i:i+chunk_size]
        for j in range(0, len(chunk), row_size):
            row = chunk[j:j+row_size]
            for emoji in row:
                builder.button(text=emoji, callback_data=f"add_emoji_{emoji}")
            builder.adjust(row_size)
        await message.answer(f"Выберите значок (эмодзи) для топика (часть {i//chunk_size+1}):", reply_markup=builder.as_markup())
    await state.set_state(TemplateManagement.adding_topic_emoji)

@router.message(TemplateManagement.adding_topic_emoji, F.text.in_([".", "Пропустить", "Очистить эмодзи"]))
async def skip_edit_topic_emoji(message: Message, state: FSMContext):
    data = await state.get_data()
    topics = data.get("topics", [])
    idx = data.get("editing_topic_index")
    if idx is not None and 0 <= idx < len(topics):
        topics[idx]["icon_emoji"] = None
        await state.update_data(topics=topics)
        # Синхронизируем с selected_template
        if "selected_template" in data:
            selected = data["selected_template"]
            selected["topics"] = topics
            await state.update_data(selected_template=selected)
    await message.answer("Эмодзи топика очищено!")
    await handle_edit_topics(message, state)

@router.message(TemplateManagement.adding_topic_emoji, F.text == "❌ Отменить добавление")
async def cancel_add_topic_emoji(message: Message, state: FSMContext):
    await handle_edit_topics(message, state)

@router.callback_query(TemplateManagement.adding_topic_emoji)
async def process_add_topic_emoji(callback: CallbackQuery, state: FSMContext):
    if not callback.data or not callback.data.startswith("add_emoji_"):
        await callback.answer("Пожалуйста, выберите эмодзи с клавиатуры.", show_alert=True)
        return
    emoji = callback.data.replace("add_emoji_", "")
    data = await state.get_data()
    topics = data.get("topics", [])
    new_topic = {
        "title": data["current_topic_name"],
        "description": data.get("current_topic_description", ""),
        "icon_emoji": emoji,
        "icon_color": None,
        "is_closed": False,
        "is_hidden": False
    }
    topics.append(new_topic)
    await state.update_data(topics=topics)
    # Синхронизируем с selected_template, если есть
    if "selected_template" in data:
        selected = data["selected_template"]
        selected["topics"] = topics
        await state.update_data(selected_template=selected)
    await callback.message.edit_reply_markup()
    await callback.message.answer("Топик добавлен!")
    await handle_edit_topics(callback.message, state)

@router.message(TemplateManagement.editing_topics, F.text == "✅ Завершить изменения")
async def finish_editing_topics(message: Message, state: FSMContext):
    data = await state.get_data()
    template = data.get("selected_template", data)
    preview = format_template_preview(
        template.get("template_name") or template.get("name"),
        template.get("chat_name"),
        template.get("topics", [])
    )
    await message.answer(
        f"✅ Шаблон обновлён!\n\n{preview}\n\nВыберите действие:",
        reply_markup=get_template_completion_keyboard()
    )
    await state.set_state(TemplateManagement.completed)

@router.message(TemplateManagement.editing_topics, F.text == "❌ Отмена")
async def cancel_editing_topics(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Редактирование отменено.",
        reply_markup=get_main_keyboard()
    )

# --- Исправленные фильтры для кнопок ---
@router.message(TemplateManagement.editing_topics, F.text.func(lambda t: t and t.strip() == "✏️ Изменить топик"))
async def handle_edit_topic_select(message: Message, state: FSMContext):
    data = await state.get_data()
    topics = data.get("topics", [])
    if not topics:
        await message.answer("Нет топиков для изменения.")
        return
    topic_list = "Выберите топик для изменения:\n\n"
    keyboard = []
    for i, topic in enumerate(topics, 1):
        title = topic.get('title', '') if isinstance(topic, dict) else getattr(topic, 'title', '')
        topic_list += f"{i}. {title}\n"
        keyboard.append([KeyboardButton(text=f"{i}. {title}")])
    keyboard.append([KeyboardButton(text="❌ Отмена")])
    await message.answer(topic_list, reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True))
    await state.set_state(TemplateManagement.editing_topic_select)

@router.message(TemplateManagement.editing_topics, F.text == "🗑 Удалить топик")
async def handle_delete_topic_select(message: Message, state: FSMContext):
    data = await state.get_data()
    topics = data.get("topics", [])
    if not topics:
        await message.answer("Нет топиков для удаления.")
        return
    topic_list = "Выберите топик для удаления:\n\n"
    keyboard = []
    for i, topic in enumerate(topics, 1):
        title = topic.get('title', '') if isinstance(topic, dict) else getattr(topic, 'title', '')
        topic_list += f"{i}. {title}\n"
        keyboard.append([KeyboardButton(text=f"{i}. {title}")])
    keyboard.append([KeyboardButton(text="❌ Отмена")])
    await message.answer(topic_list, reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True))
    await state.set_state(TemplateManagement.deleting_topic_select)

@router.message(TemplateManagement.deleting_topic_select)
async def handle_delete_topic(message: Message, state: FSMContext):
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[DEBUG] handle_delete_topic: message.text={message.text}, state={await state.get_state()}")
    data = await state.get_data()
    topics = data.get("topics", [])
    text = message.text.strip()
    if text == "❌ Отмена":
        await handle_edit_topics(message, state)
        return
    try:
        if text[0].isdigit() and "." in text:
            topic_index = int(text.split(".")[0]) - 1
        else:
            topic_index = next((i for i, t in enumerate(topics) if (t.get('title') if isinstance(t, dict) else getattr(t, 'title', '')) == text), None)
        if topic_index is None or topic_index < 0 or topic_index >= len(topics):
            raise ValueError
    except Exception:
        logger.warning(f"[DEBUG] handle_delete_topic: failed to find topic_index for text={text}")
        await message.answer("❌ Ошибка: не удалось найти выбранный топик", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    logger.warning(f"[DEBUG] handle_delete_topic: deleting topic_index={topic_index}")
    topics.pop(topic_index)
    await state.update_data(topics=topics)
    # Синхронизируем с selected_template
    if "selected_template" in data:
        selected = data["selected_template"]
        selected["topics"] = topics
        await state.update_data(selected_template=selected)
    await handle_edit_topics(message, state)

# --- Блокировка ручного ввода ---
@router.message(TemplateManagement.editing_topics)
async def block_manual_input_in_editing_topics(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, используйте только кнопки для управления топиками.", reply_markup=get_topic_edit_keyboard())

@router.message(F.text == "🔙 В главное меню")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await cmd_start(message, state)

@router.message(F.text == "🔙 Назад")
async def back_generic(message: Message, state: FSMContext):
    current_state = await state.get_state()
    # Назад из выбора топика для редактирования/удаления — к списку топиков
    if current_state in ["TemplateManagement:editing_topic_select", "TemplateManagement:deleting_topic_select"]:
        await handle_edit_topics(message, state)
    # Назад из добавления топика — к списку топиков
    elif current_state in ["TemplateManagement.adding_topic_name", "TemplateManagement.adding_topic_description"]:
        await handle_edit_topics(message, state)
    # Назад из меню редактирования — к завершённому шаблону
    elif current_state == "TemplateManagement.editing":
        data = await state.get_data()
        template = data.get("selected_template", data)
        preview = format_template_preview(
            template.get("template_name") or template.get("name"),
            template.get("chat_name"),
            template.get("topics", [])
        )
        await message.answer(
            f"Текущий шаблон:\n\n{preview}\n\nВыберите, что хотите отредактировать:",
            reply_markup=get_edit_keyboard()
        )
        await state.set_state(TemplateManagement.editing)
    else:
        await state.clear()
        await cmd_start(message, state)

@router.message(TemplateManagement.editing, F.text == "📝 Изменить название шаблона")
async def edit_template_name_emoji(message: Message, state: FSMContext):
    await message.answer("Введите новое название шаблона:")
    await state.set_state(TemplateManagement.editing_template_name)

@router.message(TemplateManagement.editing, F.text == "💬 Изменить название чата")
async def edit_chat_name_emoji(message: Message, state: FSMContext):
    await message.answer("Введите новое название чата:")
    await state.set_state(TemplateManagement.editing_chat_name)

@router.message(TemplateManagement.editing, F.text == "📄 Изменить описание чата")
async def edit_chat_description_emoji(message: Message, state: FSMContext):
    await message.answer("Введите новое описание чата:")
    await state.set_state(TemplateManagement.editing_chat_description)

@router.message(TemplateManagement.editing, F.text == "📑 Изменить топики")
async def edit_topics_emoji(message: Message, state: FSMContext):
    await handle_edit_topics(message, state)

@router.message(TemplateManagement.editing_topic_select)
async def handle_edit_topic_field_select(message: Message, state: FSMContext):
    data = await state.get_data()
    topics = data.get("topics", [])
    text = message.text.strip()
    if text == "❌ Отмена":
        await handle_edit_topics(message, state)
        return
    try:
        if text[0].isdigit() and "." in text:
            topic_index = int(text.split(".")[0]) - 1
        else:
            topic_index = next((i for i, t in enumerate(topics) if (t.get('title') if isinstance(t, dict) else getattr(t, 'title', '')) == text), None)
        if topic_index is None or topic_index < 0 or topic_index >= len(topics):
            raise ValueError
    except Exception:
        await message.answer("❌ Ошибка: не удалось найти выбранный топик", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))
        return
    await state.update_data(editing_topic_index=topic_index)
    # Показываем меню выбора поля для редактирования
    await message.answer(
        "Что вы хотите изменить в топике?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✏️ Изменить название")],
                [KeyboardButton(text="📝 Изменить описание")],
                [KeyboardButton(text="🎨 Изменить эмодзи")],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateManagement.editing_topic_field_select)

@router.message(TemplateManagement.editing_topic_field_select, F.text == "✏️ Изменить название")
async def process_edit_topic_name(message: Message, state: FSMContext):
    await message.answer(
        "Введите новое название топика:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateManagement.editing_topic_name)

@router.message(TemplateManagement.editing_topic_name)
async def process_edit_topic_name_input(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await handle_edit_topics(message, state)
        return
    is_valid, error_message = validate_topic_name(message.text)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите другое название:")
        return
    data = await state.get_data()
    topics = data.get("topics", [])
    idx = data.get("editing_topic_index")
    if idx is not None and 0 <= idx < len(topics):
        topics[idx]["title"] = message.text
        await state.update_data(topics=topics)
        # Синхронизируем с selected_template
        if "selected_template" in data:
            selected = data["selected_template"]
            selected["topics"] = topics
            await state.update_data(selected_template=selected)
    await message.answer("Название топика обновлено!")
    await handle_edit_topics(message, state)

@router.message(TemplateManagement.editing_topic_field_select, F.text == "📝 Изменить описание")
async def process_edit_topic_description(message: Message, state: FSMContext):
    await message.answer(
        "Введите новое описание топика (или отправьте точку для пропуска):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=".")], [KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateManagement.editing_topic_description)

@router.message(TemplateManagement.editing_topic_description)
async def process_edit_topic_description_input(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await handle_edit_topics(message, state)
        return
    data = await state.get_data()
    topics = data.get("topics", [])
    idx = data.get("editing_topic_index")
    if idx is not None and 0 <= idx < len(topics):
        topics[idx]["description"] = message.text if message.text != "." else ""
        await state.update_data(topics=topics)
        # Синхронизируем с selected_template
        if "selected_template" in data:
            selected = data["selected_template"]
            selected["topics"] = topics
            await state.update_data(selected_template=selected)
    await message.answer("Описание топика обновлено!")
    await handle_edit_topics(message, state)

@router.message(TemplateManagement.editing_topic_field_select, F.text == "🎨 Изменить эмодзи")
async def select_edit_topic_emoji(message: Message, state: FSMContext):
    from handlers.forum_handlers import load_working_emojis
    emoji_map = load_working_emojis()
    if not emoji_map:
        await message.answer("❌ Рабочий список значков не найден. Пожалуйста, обновите его командой /refresh_topic_emojis")
        await state.clear()
        return
    all_emojis = list(emoji_map.keys())
    max_emojis = 80
    all_emojis = all_emojis[:max_emojis]
    chunk_size = 16
    row_size = 8
    for i in range(0, len(all_emojis), chunk_size):
        builder = InlineKeyboardBuilder()
        chunk = all_emojis[i:i+chunk_size]
        for j in range(0, len(chunk), row_size):
            row = chunk[j:j+row_size]
            for emoji in row:
                builder.button(text=emoji, callback_data=f"edit_emoji_{emoji}")
            builder.adjust(row_size)
        await message.answer(f"Выберите новый значок (эмодзи) для топика (часть {i//chunk_size+1}):", reply_markup=builder.as_markup())
    # Обычная клавиатура для пропуска
    await message.answer(
        "Или нажмите 'Пропустить', чтобы очистить эмодзи:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Пропустить")], [KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(TemplateManagement.editing_topic_emoji)

@router.callback_query(TemplateManagement.editing_topic_emoji)
async def process_edit_topic_emoji(callback: CallbackQuery, state: FSMContext):
    if not callback.data or not callback.data.startswith("edit_emoji_"):
        await callback.answer("Пожалуйста, выберите эмодзи с клавиатуры.", show_alert=True)
        return
    emoji = callback.data.replace("edit_emoji_", "")
    data = await state.get_data()
    topics = data.get("topics", [])
    idx = data.get("editing_topic_index")
    if idx is not None and 0 <= idx < len(topics):
        topics[idx]["icon_emoji"] = emoji
        await state.update_data(topics=topics)
        # Синхронизируем с selected_template
        if "selected_template" in data:
            selected = data["selected_template"]
            selected["topics"] = topics
            await state.update_data(selected_template=selected)
    await callback.message.edit_reply_markup()
    await callback.message.answer("Эмодзи топика обновлено!")
    await handle_edit_topics(callback.message, state)

@router.message(F.text == "⚡️ Создать форум-чат/шаблон")
async def handle_create_forum_chat(message: Message, state: FSMContext):
    await state.clear()
    await create_template_start(message, state)

@router.message(TemplateManagement.editing_template_name)
async def save_template_name(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(template_name=message.text)
    # Синхронизируем selected_template, если есть
    if "selected_template" in data:
        selected = data["selected_template"]
        selected["template_name"] = message.text
        selected["name"] = message.text
        await state.update_data(selected_template=selected)
        template = selected
    else:
        template = data
        template["template_name"] = message.text
        template["name"] = message.text
    preview = format_template_preview(
        template.get("template_name") or template.get("name"),
        template.get("chat_name"),
        template.get("topics", [])
    )
    await message.answer(f"Название шаблона обновлено!\n\n{preview}", reply_markup=get_edit_keyboard())
    await state.set_state(TemplateManagement.editing)

@router.message(TemplateManagement.editing_chat_name)
async def save_chat_name(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(chat_name=message.text)
    if "selected_template" in data:
        selected = data["selected_template"]
        selected["chat_name"] = message.text
        await state.update_data(selected_template=selected)
        template = selected
    else:
        template = data
        template["chat_name"] = message.text
    preview = format_template_preview(
        template.get("template_name") or template.get("name"),
        template.get("chat_name"),
        template.get("topics", [])
    )
    await message.answer(f"Название чата обновлено!\n\n{preview}", reply_markup=get_edit_keyboard())
    await state.set_state(TemplateManagement.editing)

@router.message(TemplateManagement.editing_chat_description)
async def save_chat_description(message: Message, state: FSMContext):
    data = await state.get_data()
    # Всегда обновляем и chat_description, и description везде
    await state.update_data(chat_description=message.text, description=message.text)
    if "selected_template" in data:
        selected = data["selected_template"]
        selected["chat_description"] = message.text
        selected["description"] = message.text
        await state.update_data(selected_template=selected)
        template = selected
    else:
        template = data
        template["chat_description"] = message.text
        template["description"] = message.text
    preview = format_template_preview(
        template.get("template_name") or template.get("name"),
        template.get("chat_name"),
        template.get("topics", []),
        template.get("chat_description") or template.get("description")
    )
    await message.answer(f"Описание чата обновлено!\n\n{preview}", reply_markup=get_edit_keyboard())
    await state.set_state(TemplateManagement.editing)

@router.message(F.text == "📁 Мои шаблоны")
async def handle_my_templates(message: Message, state: FSMContext, telethon: TelethonService):
    await state.clear()
    await show_templates(message, state, telethon)

@router.message(F.text == "❌ Отменить создание")
async def cancel_template_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Создание шаблона отменено.",
        reply_markup=get_main_keyboard()
    )

# Универсальный обработчик отмены для всех этапов TemplateCreation
@router.message(F.text == "❌ Отменить")
async def cancel_any_template_creation(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state and str(current_state).startswith("TemplateCreation"):
        logger.info(f"[CANCEL] Universal cancel handler called, state: {current_state}")
        await state.clear()
        await message.answer("Создание шаблона отменено.", reply_markup=get_main_keyboard())

@router.message(TemplateCreation.topics, F.text == "❌ Отменить")
async def cancel_template_topics(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание шаблона отменено.", reply_markup=get_main_keyboard())

@router.message(TemplateManagement.editing, F.text == "💾 Сохранить изменения")
async def save_template_editing(message: Message, state: FSMContext, telethon: TelethonService):
    data = await state.get_data()
    template = data.get("selected_template", data)
    template_name = template.get("template_name") or template.get("name")
    chat_name = template.get("chat_name")
    chat_description = template.get("chat_description") or template.get("description")
    topics = template.get("topics", [])
    if not template_name or not chat_name or not topics:
        await message.answer("❌ Не хватает данных для сохранения шаблона.", reply_markup=get_main_keyboard())
        await state.clear()
        return
    try:
        chat_template = ChatTemplate(
            name=template_name,
            chat_name=chat_name,
            description=chat_description,
            topics=[Topic(**t) if isinstance(t, dict) else t for t in topics],
            user_id=message.from_user.id
        )
        # Используем оригинальное имя для поиска
        old_name = data.get("original_template_name") or template.get("name")
        result = await telethon.save_chat_template(
            user_id=message.from_user.id,
            template=chat_template,
            old_name=old_name
        )
        if result:
            await message.answer("✅ Изменения сохранены!", reply_markup=get_main_keyboard())
        else:
            await message.answer("❌ Не удалось сохранить изменения.", reply_markup=get_main_keyboard())
    except Exception as e:
        logger.error(f"Error saving template (editing): {e}")
        await message.answer("❌ Произошла ошибка при сохранении изменений.", reply_markup=get_main_keyboard())
    await state.clear()

# --- Обработчик редактирования топиков ---
async def handle_edit_topics(message, state):
    """Обработчик редактирования топиков"""
    data = await state.get_data()
    template = data.get("selected_template", data)
    template_name = template.get("template_name") or template.get("name")
    chat_name = template.get("chat_name")
    topics = template.get("topics", [])
    chat_description = template.get("chat_description") or template.get("description")
    # Явно обновляем все ключевые поля
    await state.update_data(
        template_name=template_name,
        chat_name=chat_name,
        chat_description=chat_description,
        topics=topics
    )
    preview = format_template_preview(template_name, chat_name, topics, chat_description)
    await message.answer(
        f"📑 Текущие топики:\n\n{preview}\n\nВыберите действие:",
        reply_markup=get_topic_edit_keyboard()
    )
    await state.set_state(TemplateManagement.editing_topics)

@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("Вы вернулись в главное меню.")
    except Exception:
        pass
    await callback.message.answer("Выберите действие:", reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "make_admin")
async def make_me_admin_callback(callback: CallbackQuery, state: FSMContext, telethon: TelethonService):
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[DEBUG] make_admin_callback: callback={callback.data}, user={callback.from_user.id}, state={await state.get_state()}")
    state_data = await state.get_data()
    chat_id = state_data.get("created_chat_id")
    invite_link = state_data.get("invite_link")
    # Если invite_link отсутствует, пробуем получить его через Telethon
    if chat_id and not invite_link:
        try:
            invite_link = await telethon.get_invite_link(chat_id)
            if invite_link:
                await state.update_data(invite_link=invite_link)
        except Exception as e:
            logger.error(f"[make_admin] Не удалось получить invite_link для чата {chat_id}: {e}")
    if not chat_id:
        logger.warning(f"[make_admin] Нет chat_id в состоянии для пользователя {callback.from_user.id}, кидаю в главное меню")
        await callback.message.edit_text(
            "❌ Ошибка: ID чата не найден. Возвращаю вас в главное меню.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        await callback.answer()
        return
    logger.info(f"[make_admin] Есть chat_id={chat_id} для пользователя {callback.from_user.id}, пробую сделать админом")
    # Проверяем, состоит ли пользователь в чате
    is_member = await telethon.is_user_in_chat(chat_id, callback.from_user.id)
    if not is_member:
        logger.info(f"[make_admin] Пользователь {callback.from_user.id} не состоит в чате {chat_id}, просим зайти в чат")
        text = ""
        if invite_link:
            text += f"🔗 <b>Ссылка для входа:</b> {invite_link}\n\n"
        text += "❗️ Я не вижу вас в участниках чата.\nВойдите в чат по ссылке выше, затем нажмите 'Повторить' или 'Сделать меня админом'."
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Повторить", callback_data="make_admin")],
                    [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_admin")],
                    [InlineKeyboardButton(text="🔑 Сделать меня админом", callback_data="make_admin")]
                ]
            ),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    logger.info(f"[make_admin] Пользователь {callback.from_user.id} состоит в чате {chat_id}, назначаю админом...")
    status_msg = await callback.message.edit_text("⏳ Назначаю вас администратором...")
    success = await telethon.make_chat_admin(chat_id, callback.from_user.id)
    if success:
        logger.info(f"[make_admin] Успешно назначен админом: {callback.from_user.id} в чате {chat_id}")
        await callback.message.edit_text(
            "✅ Вы успешно назначены администратором чата!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]]
            )
        )
        await state.clear()
    else:
        logger.error(f"[make_admin] Не удалось назначить админом: {callback.from_user.id} в чате {chat_id}")
        error_text = ""
        if invite_link:
            error_text += f"🔗 <b>Ссылка для входа:</b> {invite_link}\n\n"
        error_text += "❌ Не удалось назначить вас администратором. Попробуйте позже или обратитесь к владельцу бота.\n\nВойдите в чат, чтобы я мог сделать вас админом. После этого нажмите 'Повторить' или 'Сделать меня админом'."
        await callback.message.edit_text(
            error_text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Повторить", callback_data="make_admin")],
                    [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip_admin")],
                    [InlineKeyboardButton(text="🔑 Сделать меня админом", callback_data="make_admin")]
                ]
            ),
            parse_mode="HTML"
        )

def register_commands(dp: Dispatcher, telethon: TelethonService):
    """
    Регистрирует все обработчики команд и middlewares
    Args:
        dp: Диспетчер
        telethon: Сервис Telethon
    """
    # Middleware для Telethon
    dp.message.middleware(TelethonMiddleware(telethon))
    dp.callback_query.middleware(TelethonMiddleware(telethon))
    # Только приватные чаты
    router.message.filter(F.chat.type == "private")
    # Регистрируем все обработчики из этого файла
    dp.include_router(router)