import json
from datetime import datetime
from typing import Dict, Any, Optional
from core.chat_graph import chat_graph
from core.database import chat_history_service 
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self):
        self.chat_history = chat_history_service

    async def preview(self, user_id: str, user_input: str, date: Optional[str] = None) -> Dict[str, Any]:
        """Preview intent & slot detection without saving to database"""
        context = await self.chat_history.get_conversation_context(user_id)
        
        state: Dict[str, Any] = {
            "user_input": user_input,
            "history": context["history"],
            "date": date or datetime.now().isoformat(),
            "slots": context["slots"],
            "conversation_context": context.get("conversation_context"),
            "awaiting_slot": context.get("awaiting_slot")
        }

        from core.chat_node import DetectedIntent, MissingSlotAsker
        
        state = DetectedIntent()(state)
        state = MissingSlotAsker()(state)
        return state

    async def run(self, user_id: str, user_input: str, date: Optional[str] = None) -> Dict[str, Any]:
        try:
            context = await self.chat_history.get_conversation_context(user_id)
            conversation_id = context["conversation_id"]
            
            await self.chat_history.save_message(
                conversation_id, user_id, "USER", user_input
            )
            
            state: Dict[str, Any] = {
                "user_input": user_input,
                "history": context["history"],
                "date": date or datetime.now().isoformat(),
                "slots": context["slots"],
                "conversation_context": context.get("conversation_context"),
                "awaiting_slot": context.get("awaiting_slot")
            }

            result = chat_graph.invoke(state)
            
            response = result.get("response")
            response_text = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
            
            await self.chat_history.save_message(
                conversation_id,
                user_id, 
                "ASSISTANT", 
                response_text,
                {
                    "slots": result.get("slots", {}),
                    "intent": result.get("intent"),
                    "conversation_context": result.get("conversation_context"),
                    "awaiting_slot": result.get("awaiting_slot")
                }
            )
            
            logger.info(f"Successfully processed conversation for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in conversation service for user {user_id}: {e}")
            return {
                "response": "죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요.",
                "intent": "general",
                "slots": {}
            }

conversation_service = ConversationService()