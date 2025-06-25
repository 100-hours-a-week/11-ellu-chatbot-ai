import asyncio
from typing import Optional
from services.conversation import conversation_service
import logging
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 스트리밍 응답
# ────────────────────────────────────────────────────────

# datetime 문자열로 변환
def convert_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: convert_datetime(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_datetime(i) for i in obj]
    return obj

async def stream_conversation(user_id: str, user_input: str, date: Optional[str] = None):
    from services.conversation import conversation_service
    async for mode, chunk in conversation_service.stream_schedule(user_id, user_input, date=date):
        # 일정 생성 시작 문구
        if mode == "custom" and chunk.get("type") == "schedule_start":
            tokens = chunk["message"].split()
            for i, tok in enumerate(tokens):
                payload = {
                    "message": "chatbot_message",
                    "data": {
                        "text": tok,
                        "done": i == len(tokens) - 1
                    }
                }
                yield convert_datetime(payload)
        elif mode == "values" and "response" in chunk:
            resp = chunk["response"]
            if isinstance(resp, dict) and resp.get("detail"):
                detail_list = resp.get("detail", [])
                task_title = resp.get("task_title", "")
                category = resp.get("category", "")
                for i, sub in enumerate(detail_list):
                    payload = {
                        "message": "task_response",
                        "data": {
                            "task_title": task_title,
                            "category": category,
                            "detail": sub,
                            "done": False
                        }
                    }
                    yield convert_datetime(payload)
                    await asyncio.sleep(0.1)
                end_text = "🗓️ 일정 생성이 완료되었습니다. 캘린더를 확인해주세요."
                tokens = end_text.split()
                for i, tok in enumerate(tokens):
                    payload = {
                        "message": "chatbot_message",
                        "data": {
                            "text": tok,
                            "done": i == len(tokens) - 1
                        }
                    }
                    yield convert_datetime(payload)
            else:
                full_text = resp if isinstance(resp, str) else str(resp)
                tokens = full_text.split()
                for i, token in enumerate(tokens):
                    payload = {
                        "message": "chatbot_response",
                        "data": {
                            "token": token,
                            "done": i == len(tokens) - 1
                        }
                    }
                    yield convert_datetime(payload)
                    await asyncio.sleep(0.1)



