def get_edit_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру для редактирования данных"""
    keyboard = [
        ["✏️ Изменить название"],
        ["📝 Изменить описание"],
        ["📑 Изменить топики"],
        ["✅ Готово", "❌ Отменить"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def get_topic_edit_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру для редактирования топиков"""
    keyboard = [
        ["➕ Добавить топик"],
        ["❌ Отменить"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой отмены"""
    keyboard = [["❌ Отменить"]]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def get_edit_chat_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для редактирования данных чата"""
    keyboard = [
        ["✏️ Изменить название"],
        ["📝 Изменить описание"],
        ["📑 Изменить топики"],
        ["✅ Завершить", "❌ Отменить"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def get_edit_topics_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для редактирования топиков"""
    keyboard = [
        ["➕ Добавить топик"],
        ["✅ Завершить", "❌ Отменить"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )

def get_confirm_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для подтверждения действия"""
    keyboard = [
        ["✅ Подтвердить", "❌ Отменить"]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    ) 