from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.forum_handlers import load_working_emojis
import json
import logging

router = Router()

class BotForumTopicStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_emoji = State()

@router.message(Command("create_topic_bot"))
async def cmd_create_topic_bot(message: types.Message, state: FSMContext):
    await state.set_state(BotForumTopicStates.waiting_for_name)
    await message.answer("Введите название для нового топика (Bot API):")

@router.message(BotForumTopicStates.waiting_for_name)
async def process_topic_name_bot(message: types.Message, state: FSMContext):
    await state.update_data(topic_name=message.text)
    await state.set_state(BotForumTopicStates.waiting_for_description)
    await message.answer("Введите описание топика:")

@router.message(BotForumTopicStates.waiting_for_description)
async def process_topic_description_bot(message: types.Message, state: FSMContext):
    await state.update_data(topic_description=message.text)
    await state.set_state(BotForumTopicStates.waiting_for_emoji)
    emoji_map = load_working_emojis()
    if not emoji_map:
        await message.answer("❌ Рабочий список значков не найден. Пожалуйста, обновите его командой /refresh_topic_emojis")
        await state.clear()
        return
    
    # Разделяем эмодзи на две части
    emoji_list = list(emoji_map.keys())
    mid = len(emoji_list) // 2
    
    # Первая клавиатура
    builder1 = InlineKeyboardBuilder()
    for emoji in emoji_list[:mid]:
        builder1.button(text=emoji, callback_data=f"select_bot_emoji:{emoji}")
    builder1.adjust(5)
    await message.answer("Выберите иконку для топика (часть 1):", reply_markup=builder1.as_markup())
    
    # Вторая клавиатура
    builder2 = InlineKeyboardBuilder()
    for emoji in emoji_list[mid:]:
        builder2.button(text=emoji, callback_data=f"select_bot_emoji:{emoji}")
    builder2.adjust(5)
    await message.answer("Выберите иконку для топика (часть 2):", reply_markup=builder2.as_markup())
    
    await state.update_data(emoji_map=emoji_map)

@router.callback_query(F.data.startswith("select_bot_emoji:"))
async def process_emoji_selection_bot(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    emoji = callback.data.split(":")[1]
    data = await state.get_data()
    topic_name = data.get("topic_name")
    topic_description = data.get("topic_description")
    chat_id = callback.message.chat.id
    
    try:
        # Загружаем рабочий список эмодзи
        with open("working_topic_emojis.json", "r", encoding="utf-8") as f:
            working_emoji_map = json.load(f)
        
        # Получаем emoji_id из рабочего списка
        emoji_id = working_emoji_map.get(emoji)
        if not emoji_id:
            logger.warning(f"Эмодзи {emoji} не найден в рабочем списке")
            await callback.message.edit_text("❌ Ошибка: выбранный значок не поддерживается для топиков. Выберите другой из списка.")
            return

        topic = await bot.create_forum_topic(
            chat_id=chat_id,
            name=topic_name,
            icon_custom_emoji_id=emoji_id
        )
        await callback.message.edit_text(f"✅ Топик '{topic_name}' создан с иконкой {emoji}!")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при создании топика: {e}")
        await callback.message.edit_text(f"❌ Ошибка при создании топика: {str(e)}")
        await state.clear() 