from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from services.telethon import TelethonService
from keyboards.reply import get_main_keyboard
import logging

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.text == "🔑 Сделать меня админом")
async def handle_make_admin(message: Message, state: FSMContext, telethon: TelethonService):
    """Обработчик кнопки назначения админом"""
    try:
        # Получаем chat_id из состояния
        data = await state.get_data()
        chat_id = data.get("created_chat_id")
        
        if not chat_id:
            await message.answer(
                "❌ Не удалось найти информацию о созданном чате.",
                reply_markup=get_main_keyboard()
            )
            await state.clear()
            return
            
        logger.info(f"Attempting to make user {message.from_user.id} admin in chat {chat_id}")
        
        # Пытаемся назначить пользователя админом
        success = await telethon.make_chat_admin(chat_id, message.from_user.id)
        
        if success:
            await message.answer(
                "✅ Вы успешно назначены администратором чата!",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "❌ Не удалось назначить вас администратором. Возможно, у бота недостаточно прав.",
                reply_markup=get_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error in handle_make_admin: {e}")
        await message.answer(
            "❌ Произошла ошибка при назначении администратором.",
            reply_markup=get_main_keyboard()
        )
    finally:
        await state.clear()

@router.message(F.text == "↩️ Пропустить")
async def handle_skip_admin(message: Message, state: FSMContext):
    """Обработчик кнопки пропуска назначения админом"""
    await message.answer(
        "👌 Вы можете вернуться к управлению чатом позже.",
        reply_markup=get_main_keyboard()
    )
    await state.clear() 