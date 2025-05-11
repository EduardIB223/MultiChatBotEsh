from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass

class ForumCreate(BaseModel):
    """Schema for forum creation request"""
    title: str = Field(..., max_length=255, description="Forum title")
    description: str = Field("", max_length=255, description="Forum description")
    topics: List[str] = Field(..., max_items=20, description="List of topic names")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "My Forum",
                "description": "A forum for discussions",
                "topics": ["General", "News", "Support"]
            }
        }

class Topic(BaseModel):
    """Модель топика форума"""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    icon_emoji: Optional[str] = None  # Эмодзи-значок топика
    icon_color: Optional[int] = None
    is_closed: bool = False
    is_hidden: bool = False
    created_at: datetime = Field(default_factory=datetime.now)

class Template(BaseModel):
    """Базовая модель шаблона"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.now)

class ChatTemplate(Template):
    """Модель шаблона чата"""
    chat_name: str = Field(..., max_length=255)
    topics: List[Topic] = Field(..., max_items=20)
    user_id: int

class ChatCreate(BaseModel):
    """Модель для создания форум-чата"""
    title: str = Field(..., max_length=255)
    description: str = Field("", max_length=255)
    topics: List[Topic] = Field(..., max_items=20)
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Мой форум",
                "description": "Описание форума",
                "topics": [
                    {
                        "title": "Общее",
                        "icon_color": 0
                    },
                    {
                        "title": "Новости",
                        "icon_color": 1
                    }
                ]
            }
        }

@dataclass
class ForumChat:
    """Data model for a forum chat"""
    name: str
    topics: list[Topic]
    created_at: datetime = datetime.now()
    is_forum: bool = True 