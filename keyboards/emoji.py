from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Список бесплатных эмодзи (можно расширить по желанию)
FREE_EMOJIS = [
    "📄", "📑", "📝", "💬", "📚", "📌", "📋", "📅", "📦", "📊", "📈", "📉",
    "📁", "📂", "📒", "📕", "📗", "📘", "📙", "📔", "📓", "📃", "📜", "📎", "📏", "📐",
    "🗂", "🗃", "🗄", "🗒", "🗓", "🗞", "📰", "🏷", "🏷️"
]

# Функция генерации инлайн-клавиатуры с эмодзи (по 6 в ряд)
def get_emoji_keyboard():
    keyboard = []
    row = []
    for i, emoji in enumerate(FREE_EMOJIS, 1):
        row.append(InlineKeyboardButton(text=emoji, callback_data=f"emoji_{emoji}"))
        if i % 6 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 