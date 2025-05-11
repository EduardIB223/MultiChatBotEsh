from aiogram.fsm.state import State, StatesGroup

class TemplateManagement(StatesGroup):
    """Состояния для управления шаблонами"""
    viewing = State()  # Просмотр шаблона
    viewing_templates = State()  # Просмотр списка шаблонов
    editing = State()  # Редактирование шаблона
    completed = State()  # Завершение создания шаблона
    selected_template = State()  # Выбранный шаблон
    editing_topics = State()  # Редактирование топиков
    editing_topic_select = State()  # Выбор топика для редактирования
    editing_topic_field_select = State()  # Выбор поля топика для редактирования
    editing_topic_name = State()  # Изменение названия топика
    editing_topic_description = State()  # Изменение описания топика
    deleting_topic_select = State()  # Выбор топика для удаления
    editing_template_name = State()  # Редактирование названия шаблона
    editing_chat_name = State()  # Редактирование названия чата
    editing_chat_description = State()  # Редактирование описания чата
    adding_topic_name = State()         # Ввод названия нового топика в режиме редактирования
    adding_topic_description = State()  # Ввод описания нового топика в режиме редактирования
    adding_topic_emoji = State()  # Выбор эмодзи для нового топика в режиме редактирования
    editing_topic_emoji = State()  # Выбор эмодзи для топика при редактировании
    editing_topic_emoji_select = State()  # Выбор топика для смены эмодзи
    editing_topic_emoji_pick = State()    # Выбор эмодзи для топика

class TemplateCreation(StatesGroup):
    """Состояния для создания шаблона"""
    waiting_template_name = State()  # Ожидание названия шаблона
    waiting_name = State()  # Ожидание названия чата (используется в обработчиках)
    waiting_description = State()  # Ожидание описания чата
    waiting_topic_name = State()  # Ожидание названия топика
    waiting_topic_description = State()  # Ожидание описания топика
    waiting_topic_emoji = State()  # Ожидание выбора эмодзи для топика
    topics = State()  # Работа с топиками
    confirm_template = State()  # Подтверждение шаблона
    editing = State()  # Режим редактирования
    editing_template_name = State()  # Редактирование названия шаблона
    editing_name = State()  # Редактирование названия чата
    editing_description = State()  # Редактирование описания
    editing_topics = State()  # Редактирование топиков
    editing_topic = State()  # Редактирование конкретного топика
    adding_topic = State()  # Добавление нового топика
    editing_topic_name = State()  # Редактирование названия топика
    editing_topic_description = State()  # Редактирование описания топика

class ChatCreation(StatesGroup):
    """Состояния для создания чата"""
    waiting_name = State()
    waiting_description = State()
    waiting_topic_name = State()
    confirm_creation = State()
    editing = State()
    editing_name = State()
    editing_description = State()
    editing_topics = State()
    editing_topic_name = State()
    waiting_admin_action = State()
    waiting_owner_transfer = State()

class ChatStates(StatesGroup):
    """Состояния для управления чатом"""
    waiting_name = State()
    waiting_description = State()
    waiting_topic_name = State()
    confirm_creation = State()
    editing = State()
    editing_name = State()
    editing_description = State()
    editing_topics = State()
    editing_topic_name = State()
    waiting_admin_action = State()
    waiting_owner_transfer = State()  # Ожидание подтверждения передачи прав владельца 