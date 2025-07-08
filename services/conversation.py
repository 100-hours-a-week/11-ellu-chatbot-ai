import json
from datetime import datetime
from typing import Dict, Any, Optional
from core.chat_graph import chat_graph
from core.database import chat_history_service 
import logging
from core.utils import convert_datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self):
        self.chat_history = chat_history_service

    async def stream_schedule(self, user_id: str, user_input: str, date: Optional[str] = None):
        try:
            context = await self.chat_history.get_conversation_context(user_id)
            conversation_id = context["conversation_id"]

            # Save user message
            await self.chat_history.save_message(
                conversation_id, user_id, "USER", user_input
            )

            slots = context["slots"]
            if context.get("task_title"):
                slots["task_title"] = context["task_title"]

            state = {
                "user_input": user_input,
                "history": context["history"],
                "date": date or datetime.now().isoformat(),
                "slots": slots,
                "conversation_context": context.get("conversation_context"),
                "awaiting_slot": context.get("awaiting_slot"),
                "task_title": context.get("task_title"),
                "intent": context.get("intent"),
            }

            async for mode, chunk in chat_graph.astream(state, stream_mode=["custom", "values"]):
                if mode == "custom" and chunk.get("type") == "schedule_start":
                    await self.chat_history.save_message(
                        conversation_id, user_id, "ASSISTANT", chunk["message"], metadata=convert_datetime(state)
                    )
                    yield mode, chunk
                elif mode == "custom" and chunk.get("type") == "subtask":
                    yield mode, chunk
                elif mode == "values" and "response" in chunk:
                    response = chunk["response"]
                    response_text = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
                    await self.chat_history.save_message(
                        conversation_id,
                        user_id,
                        "ASSISTANT",
                        response_text,
                        convert_datetime(state)
                    )
                    yield mode, chunk
                else:
                    yield mode, chunk
            logger.info(f"Successfully streamed conversation for user {user_id}")
        except Exception as e:
            logger.error(f"Error in stream_schedule for user {user_id}: {e}")
            yield "error", {
                "response": "죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요.",
                "intent": "general",
                "slots": {}
            }

conversation_service = ConversationService()
