import asyncio
from typing import Optional
from services.conversation import conversation_service
import logging
from core.utils import convert_datetime, make_payload, yield_tokens

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 스트리밍 응답
# ────────────────────────────────────────────────────────

async def stream_conversation(user_id: str, user_input: str, date: Optional[str] = None):
    from services.conversation import conversation_service
    async for mode, chunk in conversation_service.stream_schedule(user_id, user_input, date=date):
        # subtask가 하나라도 yield되었는지 추적
        if 'subtask_yielded' not in locals():
            subtask_yielded = False
        # 일정 생성 시작 문구
        if mode == "custom" and chunk.get("type") == "schedule_start":
            for payload in yield_tokens(chunk["message"], "chatbot_message", data_key="text"):
                yield convert_datetime(payload)
        elif mode == "custom" and chunk.get("type") == "subtask":
            payload = make_payload(
                "task_response",
                {
                    "task_title": chunk.get("task_title", ""),
                    "category": chunk.get("category", ""),
                    "detail": chunk["message"],
                    "done": False
                }
            )
            yield convert_datetime(payload)
            subtask_yielded = True
        elif mode == "custom" and chunk.get("type") == "subtask_end":
            end_text = "🗓️ 일정 생성이 완료되었습니다. 캘린더를 확인해주세요."
            for payload in yield_tokens(end_text, "chatbot_message", data_key="text"):
                if payload["data"]["text"] == end_text.split()[-1]:
                    payload["data"]["done"] = True
                yield convert_datetime(payload)
        elif mode == "values" and "response" in chunk:
            resp = chunk["response"]
            full_text = resp if isinstance(resp, str) else str(resp)
            for payload in yield_tokens(full_text, "chatbot_response", data_key="token"):
                yield convert_datetime(payload)
                await asyncio.sleep(0.1)



