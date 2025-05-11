from typing import List, Dict, Optional
import aiohttp
import logging
import json
from models.schemas import Topic

logger = logging.getLogger(__name__)

class BotAPIService:
    def __init__(self, bot_token: str, base_url: str = "https://api.telegram.org"):
        """
        Инициализация сервиса Bot API
        :param bot_token: Токен бота
        :param base_url: Базовый URL API Telegram
        """
        self.bot_token = bot_token
        self.base_url = base_url
        
    async def _make_request(self, method: str, params: Dict = None) -> Optional[Dict]:
        """
        Выполняет запрос к Bot API
        :param method: Метод API
        :param params: Параметры запроса
        :return: Ответ от API или None в случае ошибки
        """
        url = f"{self.base_url}/bot{self.bot_token}/{method}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=params) as response:
                    result = await response.json()
                    if result.get("ok"):
                        return result.get("result")
                    else:
                        logger.error(f"Ошибка запроса к API: {result.get('description')}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при выполнении запроса к API: {str(e)}")
            return None

    async def create_forum_topics(self, chat_id: int, topics: List[Topic]) -> bool:
        """
        Создание топиков в форуме
        
        Args:
            chat_id: ID чата
            topics: Список топиков для создания
            
        Returns:
            bool: True если все топики созданы успешно
        """
        try:
            async with aiohttp.ClientSession() as session:
                for topic in topics:
                    url = f"{self.base_url}/createForumTopic"
                    data = {
                        "chat_id": chat_id,
                        "name": topic.name,
                        "icon_color": 7322096  # Синий цвет по умолчанию
                    }
                    
                    async with session.post(url, json=data) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("ok"):
                                logger.info(f"Топик '{topic.name}' создан успешно")
                            else:
                                logger.error(f"Ошибка при создании топика '{topic.name}': {result.get('description')}")
                                return False
                        else:
                            logger.error(f"Ошибка HTTP {response.status} при создании топика '{topic.name}'")
                            return False
                
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при создании топиков: {str(e)}")
            return False

    async def create_topics_batch(self, chat_id: int, topics: List[Dict[str, str]]) -> List[Optional[Dict]]:
        """
        Создает несколько топиков в форум-чате
        :param chat_id: ID чата
        :param topics: Список топиков с их названиями и описаниями
        :return: Список результатов создания топиков
        """
        results = []
        for topic in topics:
            result = await self.create_forum_topics(
                chat_id=chat_id,
                topics=[Topic(name=topic.get("name", "Без названия"))]
            )
            results.append(result)
        return results

    async def delete_forum_topic(self, chat_id: int, topic_id: int) -> bool:
        """
        Удаляет топик из форум-чата
        :param chat_id: ID чата
        :param topic_id: ID топика
        :return: True если успешно, False в случае ошибки
        """
        result = await self._make_request("deleteForumTopic", {
            "chat_id": chat_id,
            "message_thread_id": topic_id
        })
        return result is not None

    async def edit_forum_topic(self, chat_id: int, topic_id: int, name: str) -> bool:
        """
        Редактирует название топика
        :param chat_id: ID чата
        :param topic_id: ID топика
        :param name: Новое название топика
        :return: True если успешно, False в случае ошибки
        """
        result = await self._make_request("editForumTopic", {
            "chat_id": chat_id,
            "message_thread_id": topic_id,
            "name": name
        })
        return result is not None 