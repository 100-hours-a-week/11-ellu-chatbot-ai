import asyncpg
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.pool = None
        self.db_url = os.getenv("DATABASE_URL","postgresql://user:password@localhost:5432/looperdb_main_dev")
    
    async def init_pool(self):
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(
                    self.db_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=30
                )
                logger.info("Database pool initialized")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise
    
    async def close_pool(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")

class ChatHistoryService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def get_or_create_conversation(self, user_id: str) -> int:
        await self.db.init_pool()
        async with self.db.pool.acquire() as conn:
            conversation_id = await conn.fetchval("""
                SELECT id FROM chat_conversations 
                WHERE user_id = $1 AND deleted_at IS NULL 
                ORDER BY updated_at DESC 
                LIMIT 1
            """, user_id)
            
            if not conversation_id:
                conversation_id = await conn.fetchval("""
                    INSERT INTO chat_conversations (user_id, created_at, updated_at)
                    VALUES ($1, NOW(), NOW()) 
                    RETURNING id
                """, user_id)
                logger.info(f"Created new conversation {conversation_id} for user {user_id}")
            
            return conversation_id
    
    async def get_conversation_context(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        await self.db.init_pool()
        conversation_id = await self.get_or_create_conversation(user_id)
        
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT message_type, content, metadata, created_at
                FROM chat_messages 
                WHERE conversation_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2
            """, conversation_id, limit)
            
            history = []
            last_state = {}
            
            for row in reversed(rows):  
                history.append(row['content'])
                
                if row['message_type'] == 'ASSISTANT' and row['metadata'] and not last_state:
                    try:
                        last_state = json.loads(row['metadata'])
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in metadata for conversation {conversation_id}")
            
            return {
                "conversation_id": conversation_id,
                "history": history,
                "slots": last_state.get("slots", {}),
                "conversation_context": last_state.get("conversation_context"),
                "awaiting_slot": last_state.get("awaiting_slot"),
                "intent": last_state.get("intent")
            }
    
    async def save_message(
        self, 
        conversation_id: int,
        user_id: str, 
        message_type: str,  
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):

        await self.db.init_pool()
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO chat_messages 
                    (conversation_id, user_id, message_type, content, metadata, created_at)
                    VALUES ($1, $2, $3, $4, $5, NOW())
                """, 
                conversation_id,
                user_id,
                message_type,
                content,
                json.dumps(metadata) if metadata else None
                )
                
                await conn.execute("""
                    UPDATE chat_conversations 
                    SET updated_at = NOW() 
                    WHERE id = $1
                """, conversation_id)

db_manager = DatabaseManager()
chat_history_service = ChatHistoryService(db_manager)