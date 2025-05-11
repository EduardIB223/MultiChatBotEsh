import aiosqlite
import os
from typing import Optional, List, Tuple

class Database:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path

    async def init(self):
        """Initialize the database and create necessary tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Create table for main chat
            await db.execute('''
                CREATE TABLE IF NOT EXISTS main_chat (
                    id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    chat_title TEXT
                )
            ''')
            
            # Create table for user topics with unique constraint on user_id
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_topics (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE,
                    user_name TEXT,
                    topic_id INTEGER NOT NULL,
                    topic_title TEXT
                )
            ''')
            
            await db.commit()

    async def set_main_chat(self, chat_id: int, chat_title: str) -> bool:
        """Set the main chat for the bot."""
        async with aiosqlite.connect(self.db_path) as db:
            # Clear existing main chat
            await db.execute("DELETE FROM main_chat")
            
            # Insert new main chat
            await db.execute(
                "INSERT INTO main_chat (chat_id, chat_title) VALUES (?, ?)",
                (chat_id, chat_title)
            )
            await db.commit()
            return True

    async def get_main_chat(self) -> Optional[Tuple[int, str]]:
        """Get the main chat information."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT chat_id, chat_title FROM main_chat LIMIT 1") as cursor:
                row = await cursor.fetchone()
                return row if row else None

    async def remove_main_chat(self) -> bool:
        """Remove the main chat."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM main_chat")
            await db.commit()
            return True

    async def add_user_topic(self, user_id: int, user_name: str, topic_id: int, topic_title: str) -> bool:
        """Add or update a user topic mapping."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO user_topics 
                (user_id, user_name, topic_id, topic_title) 
                VALUES (?, ?, ?, ?)
                """,
                (user_id, user_name, topic_id, topic_title)
            )
            await db.commit()
            return True

    async def get_user_topic(self, user_id: int) -> Optional[Tuple[int, str]]:
        """Get the topic ID and title for a user."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT topic_id, topic_title FROM user_topics WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row if row else None

    async def get_topic_user(self, topic_id: int) -> Optional[Tuple[int, str]]:
        """Get the user ID and name for a topic."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT user_id, user_name FROM user_topics WHERE topic_id = ?",
                (topic_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row if row else None 