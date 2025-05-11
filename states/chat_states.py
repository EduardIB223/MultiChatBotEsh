from aiogram.fsm.state import State, StatesGroup

class ChatCreation(StatesGroup):
    """Состояния для создания чата"""
    waiting_name = State()            # Ожидание названия чата
    waiting_description = State()     # Ожидание описания чата
    waiting_topic_name = State()      # Ожидание названия топика
    editing = State()                 # Режим редактирования
    editing_name = State()            # Редактирование названия
    editing_description = State()     # Редактирование описания
    editing_topics = State()          # Редактирование списка топиков
    editing_topic_name = State()      # Редактирование названия топика
    confirm_creation = State()        # Подтверждение создания
    waiting_template_name = State()   # Ожидание названия шаблона

class TemplateCreation(StatesGroup):
    """Состояния для создания шаблона"""
    waiting_template_name = State()    # Ожидание названия шаблона
    waiting_name = State()            # Ожидание названия чата
    waiting_description = State()      # Ожидание описания чата
    waiting_topic_name = State()      # Ожидание названия топика
    editing = State()                 # Режим редактирования
    editing_template_name = State()   # Редактирование названия шаблона
    editing_name = State()            # Редактирование названия чата
    editing_description = State()      # Редактирование описания
    editing_topics = State()          # Редактирование списка топиков
    editing_topic_name = State()      # Редактирование названия топика
    confirm_template = State()        # Подтверждение шаблона

class TemplateManagement(StatesGroup):
    """Состояния для управления шаблонами"""
    viewing_templates = State()       # Просмотр списка шаблонов
    viewing_template = State()        # Просмотр шаблона
    selected_template = State()       # Выбранный шаблон для действий
    editing = State()                # Режим редактирования
    editing_template_name = State()  # Редактирование названия шаблона
    editing_chat_name = State()      # Редактирование названия чата
    editing_chat_description = State() # Редактирование описания чата
    editing_topics = State()         # Редактирование списка топиков
    editing_topic = State()          # Редактирование конкретного топика
    editing_topic_name = State()     # Редактирование названия топика
    adding_topic = State()           # Добавление нового топика
    confirm_changes = State()        # Подтверждение изменений
    confirming_deletion = State()    # Подтверждение удаления шаблона

class ChatStates(StatesGroup):
    """Состояния для управления чатом"""
    waiting_chat_name = State()
    waiting_description = State()
    waiting_topics = State()
    waiting_admin_action = State()
    waiting_template_name = State()
    waiting_template_chat_name = State()
    editing_topics = State()
    waiting_topic_name = State()
    waiting_topic_description = State()
    waiting_owner_transfer = State()  # Ожидание подтверждения передачи прав владельца 