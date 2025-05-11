from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from typing import List, Optional
import json
import logging
from datetime import datetime

from config import DATABASE_URL
from models.schemas import ChatTemplate, Topic

logger = logging.getLogger(__name__)

Base = declarative_base()

class Template(Base):
    """Модель шаблона в БД"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    chat_name = Column(String(128), nullable=False)
    description = Column(String(255), nullable=True, default="")
    topics = Column(JSON, nullable=False)  # Хранит список топиков в JSON
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, nullable=False)

class DatabaseService:
    def __init__(self):
        """Инициализация сервиса БД"""
        self.engine = create_async_engine(DATABASE_URL)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_db(self):
        """Инициализация базы данных"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def save_template(self, template: ChatTemplate) -> bool:
        """
        Сохранение шаблона
        
        Args:
            template: Шаблон для сохранения
            
        Returns:
            bool: Успешно ли сохранен шаблон
        """
        async with self.async_session() as session:
            try:
                db_template = Template(
                    name=template.name,
                    chat_name=template.chat_name,
                    description=template.description,
                    topics=json.dumps([t.dict() for t in template.topics]),
                    user_id=template.user_id
                )
                session.add(db_template)
                await session.commit()
                logger.info(f"Шаблон '{template.name}' успешно сохранен для пользователя {template.user_id}")
                return True
            except Exception as e:
                logger.error(f"Ошибка при сохранении шаблона '{template.name}': {str(e)}")
                await session.rollback()
                return False
    
    async def get_templates(self, user_id: int) -> List[ChatTemplate]:
        """
        Получение всех шаблонов пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            List[ChatTemplate]: Список шаблонов
        """
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    Template.__table__.select().where(Template.user_id == user_id)
                )
                templates = []
                for row in result:
                    topics = [Topic(**t) for t in json.loads(row.topics)]
                    templates.append(ChatTemplate(
                        name=row.name,
                        chat_name=row.chat_name,
                        description=row.description,
                        topics=topics,
                        created_at=row.created_at,
                        user_id=row.user_id
                    ))
                return templates
            except Exception as e:
                logger.error(f"Ошибка при получении шаблонов пользователя {user_id}: {str(e)}")
                return []
    
    async def get_template(self, user_id: int, template_name: str) -> Optional[ChatTemplate]:
        """
        Получение конкретного шаблона
        
        Args:
            user_id: ID пользователя
            template_name: Название шаблона
            
        Returns:
            Optional[ChatTemplate]: Шаблон или None
        """
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    Template.__table__.select().where(
                        (Template.user_id == user_id) & 
                        (Template.name == template_name)
                    )
                )
                row = result.first()
                if row:
                    topics = [Topic(**t) for t in json.loads(row.topics)]
                    return ChatTemplate(
                        name=row.name,
                        chat_name=row.chat_name,
                        description=row.description,
                        topics=topics,
                        created_at=row.created_at,
                        user_id=row.user_id
                    )
                return None
            except Exception as e:
                logger.error(f"Ошибка при получении шаблона '{template_name}' пользователя {user_id}: {str(e)}")
                return None
    
    async def delete_template(self, user_id: int, template_name: str) -> bool:
        """
        Удаление шаблона
        
        Args:
            user_id: ID пользователя
            template_name: Название шаблона
            
        Returns:
            bool: Успешно ли удален шаблон
        """
        async with self.async_session() as session:
            try:
                await session.execute(
                    Template.__table__.delete().where(
                        (Template.user_id == user_id) & 
                        (Template.name == template_name)
                    )
                )
                await session.commit()
                logger.info(f"Шаблон '{template_name}' пользователя {user_id} успешно удален")
                return True
            except Exception as e:
                logger.error(f"Ошибка при удалении шаблона '{template_name}' пользователя {user_id}: {str(e)}")
                await session.rollback()
                return False 