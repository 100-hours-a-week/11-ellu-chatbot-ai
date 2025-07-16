from datetime import datetime
from typing import Optional
from core.chat_graph import chat_graph
from core.database import chat_history_service 
import logging
from core.utils import safe_convert
import os
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self):
        self.chat_history = chat_history_service

    async def stream_schedule(self, user_id: str, user_input: str, date: Optional[str] = None):
        logger.info(f"[stream_schedule] 진입, user_id={user_id}, user_input={user_input}, date={date}")
        try:
            context = await self.chat_history.get_conversation_context(user_id)
            conversation_id = context["conversation_id"]
            msg_to_save = str(user_input) if not isinstance(user_input, str) else user_input
            await self.chat_history.save_message(
                conversation_id, user_id, "USER", msg_to_save
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
                "user_id": user_id,
                "has_fetched_schedule": False
            }

            last_state = None
            subtask_chunks = []

            async for mode, chunk in chat_graph.astream(state, stream_mode=["custom", "values"]):
                if mode == "custom" and chunk.get("type") == "schedule_start":
                    yield mode, chunk
                elif mode == "custom" and chunk.get("type") == "subtask":
                    subtask_chunks.append(chunk)
                    yield mode, safe_convert(chunk)
                elif mode == "values" and "response" in chunk:
                    state = dict(chunk)
                    last_state = state
                    yield mode, safe_convert(chunk)
                else:
                    yield mode, safe_convert(chunk)
                    if mode == "values":
                        state = dict(chunk)
                        last_state = state

            # 마지막 응답 저장
            if last_state or subtask_chunks:
                metadata = dict(last_state) if last_state else {}
                if subtask_chunks:
                    metadata["subtasks"] = subtask_chunks
                content = last_state.get("response", "") if last_state else str([c.get("message", "") for c in subtask_chunks])
                await self.chat_history.save_message(
                    conversation_id,
                    user_id,
                    "ASSISTANT",
                    content,
                    metadata
                )
            logger.info(f"Successfully streamed conversation for user {user_id}")
        except Exception as e:
            logger.error(f"Error in stream_schedule for user {user_id}: {e}")
            yield "error", {
                "response": "죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요.",
                "intent": "general",
                "slots": {}
            }

    # 일정 데이터 조회
    async def fetch_schedules(self, user_id, start, end, task_title_keyword, category):
        backend_url = os.getenv("SCHEDULE_BACKEND_URL", "http://localhost:8080/chat/query")
        payload = {
            "user_id": user_id,
            "start": start,
            "end": end,
            "task_title_keyword": task_title_keyword,
            "category": category
        }
        logger.info(f"[fetch_schedules] 쿼리 생성 결과: {payload}")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(backend_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                logger.info("[fetch_schedule] 백엔드 통신 성공")
                return data.get("data", [])
        except Exception as e:
            logger.error(f"[fetch_schedules] 백엔드 통신 오류: {e}")
            return []

conversation_service = ConversationService()
