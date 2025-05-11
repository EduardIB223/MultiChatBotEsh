from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.forum_utils import change_topic_icon, generate_invite_link, smart_change_icon, STANDARD_EMOJIS
from services.telethon_service import TelethonService
import logging
import json
import os

router = Router()
logger = logging.getLogger(__name__)

WORKING_EMOJI_FILE = "working_topic_emojis.json"

def save_working_emojis(emoji_map):
    with open(WORKING_EMOJI_FILE, "w", encoding="utf-8") as f:
        json.dump(emoji_map, f, ensure_ascii=False)

def load_working_emojis():
    if os.path.exists(WORKING_EMOJI_FILE):
        with open(WORKING_EMOJI_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

class ForumTopicStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_emoji = State()

@router.message(Command("create_topic"))
async def cmd_create_topic(message: types.Message, state: FSMContext):
    """Начало создания топика"""
    await state.set_state(ForumTopicStates.waiting_for_name)
    await message.answer("Введите название для нового топика:")

@router.message(ForumTopicStates.waiting_for_name)
async def process_topic_name(message: types.Message, state: FSMContext):
    """Обработка названия топика"""
    await state.update_data(topic_name=message.text)
    await state.set_state(ForumTopicStates.waiting_for_description)
    await message.answer("Введите описание топика:")

@router.message(ForumTopicStates.waiting_for_description)
async def process_topic_description(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка описания топика"""
    await state.update_data(topic_description=message.text)
    await state.set_state(ForumTopicStates.waiting_for_emoji)
    try:
        emoji_map = load_working_emojis()
        if not emoji_map:
            await message.answer("❌ Рабочий список значков не найден. Пожалуйста, обновите его командой /refresh_topic_emojis")
            await state.clear()
            return
        logger.info(f"[EMOJI MAP - FINAL] {emoji_map}")
        # Популярные эмодзи (можно расширить или изменить порядок)
        popular_emojis = ["📄", "🏆", "❤️", "👑", "💬", "📚", "📦", "📊", "📈", "📉", "📁", "📂", "📒", "📕", "📗"]
        # Оставляем только те, что реально есть в emoji_map
        popular_emojis = [e for e in popular_emojis if e in emoji_map]
        # Инлайн-клавиатура только с популярными
        builder = InlineKeyboardBuilder()
        for emoji in popular_emojis:
            builder.button(text=emoji, callback_data=f"select_emoji:{emoji}")
        builder.adjust(5)
        await message.answer("Выберите значок для топика:", reply_markup=builder.as_markup())
        # Полный список эмодзи текстом
        all_emojis = list(emoji_map.keys())
        all_emojis_text = ' '.join(all_emojis)
        await message.answer(f"Если нужного значка нет на кнопках выше, скопируйте его из списка ниже и отправьте сообщением:\n{all_emojis_text}")
        await state.update_data(emoji_map=emoji_map)
    except Exception as e:
        await message.answer(f"Ошибка при получении списка эмодзи для топиков: {e}")
        await state.clear()

@router.message(Command("show_topic_emojis"))
async def show_topic_emojis(message: types.Message, bot: Bot):
    """Показывает список разрешённых эмодзи и их ID для топиков (Bot API)"""
    try:
        stickers = await bot.get_forum_topic_icon_stickers()
        emoji_map = {s.emoji: s.custom_emoji_id for s in stickers}
        text = '\n'.join([f"{emoji} — <code>{emoji_id}</code>" for emoji, emoji_id in emoji_map.items()])
        await message.answer(f"<b>Разрешённые эмодзи для топиков:</b>\n{text}", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@router.callback_query(F.data.startswith("select_emoji:"))
async def process_emoji_selection(
    callback: types.CallbackQuery,
    state: FSMContext,
    telethon_service: TelethonService,
    bot: Bot
):
    """Обработка выбора эмодзи"""
    emoji = callback.data.split(":")[1]
    data = await state.get_data()
    chat_id = data.get("chat_id") or callback.message.chat.id
    topic_name = data["topic_name"]
    topic_description = data["topic_description"]
    emoji_map = data.get("emoji_map")
    
    try:
        # Загружаем рабочий список эмодзи
        with open("working_topic_emojis.json", "r", encoding="utf-8") as f:
            working_emoji_map = json.load(f)
        
        # Получаем emoji_id из рабочего списка
        emoji_id = working_emoji_map.get(emoji)
        if not emoji_id:
            logger.warning(f"Эмодзи {emoji} не найден в рабочем списке")
            await callback.message.answer("❌ Ошибка: выбранный значок не поддерживается для топиков. Выберите другой из списка.")
            return

        logger.info(f"[TOPIC CREATE] chat_id={chat_id} title={topic_name} emoji={emoji} emoji_id={emoji_id}")
        topic = await bot.create_forum_topic(
            chat_id=chat_id,
            name=topic_name,
            icon_custom_emoji_id=emoji_id
        )
        await callback.message.edit_text(
            f"✅ Топик '{topic_name}' создан с иконкой {emoji}!"
        )
        await state.clear()
        return
    except Exception as e:
        logger.error(f"[TOPIC CREATE ERROR] chat_id={chat_id} title={topic_name} emoji={emoji} error={e}")
        await callback.message.edit_text(
            f"❌ Ошибка при создании топика: {str(e)}"
        )
        await state.clear()

@router.callback_query(F.data.startswith("retry_icon:"))
async def handle_retry_icon(
    callback: types.CallbackQuery,
    state: FSMContext,
    telethon_service: TelethonService,
    bot: Bot
):
    """Повторная попытка установки иконки"""
    _, chat_id, topic_id = callback.data.split(":")
    chat_id = int(chat_id)
    topic_id = int(topic_id)
    data = await state.get_data()
    emoji = data.get("selected_emoji")
    if not emoji:
        await callback.answer("Не удалось определить emoji для топика.", show_alert=True)
        return
    success = await smart_change_icon(
        chat_id=chat_id,
        topic_id=topic_id,
        emoji=emoji,
        bot=bot
    )
    if success:
        await callback.message.delete()
        await callback.answer("✅ Иконка успешно установлена!")
        await state.clear()
    else:
        invite_link = await generate_invite_link(telethon_service.client, chat_id)
        await callback.message.edit_text(
            f"❌ Не удалось установить иконку.\n"
            f"1. Убедитесь, что бот уже добавлен в чат и обладает правом 'Управление темами'.\n"
            f"2. Если бот уже в чате, просто напишите любое сообщение в этот чат (или попросите кого-то это сделать).\n"
            f"3. Затем нажмите кнопку ниже для повторной попытки.\n"
            f"\nСсылка для чата: {invite_link}",
            reply_markup=callback.message.reply_markup
        )

@router.message(ForumTopicStates.waiting_for_emoji)
async def process_emoji_text(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    emoji = message.text.strip()
    
    try:
        # Загружаем рабочий список эмодзи
        with open("working_topic_emojis.json", "r", encoding="utf-8") as f:
            working_emoji_map = json.load(f)
        
        # Получаем emoji_id из рабочего списка
        emoji_id = working_emoji_map.get(emoji)
        if not emoji_id:
            await message.answer("❌ Такой эмодзи нельзя использовать для иконки топика. Выберите из разрешённых (можно нажать на кнопку или скопировать из списка выше).")
            return

        topic_name = data["topic_name"]
        chat_id = message.chat.id
        
        logger.info(f"[TOPIC CREATE] chat_id={chat_id} title={topic_name} emoji={emoji} emoji_id={emoji_id}")
        await bot.create_forum_topic(
            chat_id=chat_id,
            name=topic_name,
            icon_custom_emoji_id=emoji_id
        )
        await message.answer(f"✅ Топик '{topic_name}' создан с иконкой {emoji}!")
        await state.clear()
    except Exception as e:
        logger.error(f"[TOPIC CREATE ERROR] chat_id={chat_id} title={topic_name} emoji={emoji} error={e}")
        await message.answer(f"❌ Ошибка при создании топика: {str(e)}")
        await state.clear()

@router.message(Command("test_topic_emojis"))
async def test_topic_emojis(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    try:
        stickers = await bot.get_forum_topic_icon_stickers()
        emoji_map = {s.emoji: s.custom_emoji_id for s in stickers if s.custom_emoji_id}
        working = {}
        failed = []
        await message.answer("⏳ Начинаю тест значков. Это может занять несколько минут из-за лимитов Telegram.")
        import asyncio
        for i, (emoji, emoji_id) in enumerate(emoji_map.items()):
            try:
                topic = await bot.create_forum_topic(
                    chat_id=chat_id,
                    name=f"test_{emoji}",
                    icon_custom_emoji_id=emoji_id
                )
                working[emoji] = emoji_id
                await asyncio.sleep(1.5)
                await bot.delete_forum_topic(chat_id=chat_id, message_thread_id=topic.message_thread_id)
            except Exception as e:
                failed.append((emoji, str(e)))
                await asyncio.sleep(1.5)
        if working:
            save_working_emojis(working)
            text = '\n'.join([f"{emoji} — <code>{emoji_id}</code>" for emoji, emoji_id in working.items()])
            await message.answer(f"<b>Рабочие значки для топиков в этом чате сохранены:</b>\n{text}", parse_mode="HTML")
        else:
            await message.answer("❌ Не удалось создать ни одного топика с этими значками. Telegram ограничил доступ.")
        if failed:
            await message.answer(f"<b>Не сработали:</b>\n" + '\n'.join([f"{emoji}: {err}" for emoji, err in failed]), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка теста: {e}")

@router.message(Command("refresh_topic_emojis"))
async def refresh_topic_emojis(message: types.Message, bot: Bot):
    """Принудительно обновляет рабочий список emoji_id для топиков (перезапускает тест)."""
    chat_id = message.chat.id
    try:
        stickers = await bot.get_forum_topic_icon_stickers()
        emoji_map = {s.emoji: s.custom_emoji_id for s in stickers if s.custom_emoji_id}
        working = {}
        failed = []
        await message.answer("⏳ Обновляю рабочий список значков. Это может занять несколько минут из-за лимитов Telegram.")
        import asyncio
        for i, (emoji, emoji_id) in enumerate(emoji_map.items()):
            try:
                topic = await bot.create_forum_topic(
                    chat_id=chat_id,
                    name=f"test_{emoji}",
                    icon_custom_emoji_id=emoji_id
                )
                working[emoji] = emoji_id
                await asyncio.sleep(1.5)
                await bot.delete_forum_topic(chat_id=chat_id, message_thread_id=topic.message_thread_id)
            except Exception as e:
                failed.append((emoji, str(e)))
                await asyncio.sleep(1.5)
        if working:
            save_working_emojis(working)
            text = '\n'.join([f"{emoji} — <code>{emoji_id}</code>" for emoji, emoji_id in working.items()])
            await message.answer(f"<b>Рабочие значки для топиков обновлены и сохранены:</b>\n{text}", parse_mode="HTML")
        else:
            await message.answer("❌ Не удалось создать ни одного топика с этими значками. Telegram ограничил доступ.")
        if failed:
            await message.answer(f"<b>Не сработали:</b>\n" + '\n'.join([f"{emoji}: {err}" for emoji, err in failed]), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка обновления: {e}") 