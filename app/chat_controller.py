# app/controllers/chat_controller.py
import asyncio
import json
from typing import AsyncGenerator, Optional
from datetime import datetime
from services.streaming import stream_conversation
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 챗봇 스트리밍 컨트롤러
# ────────────────────────────────────────────────────────

async def stream_chat(
    user_input: str,
    user_id: str,
    date: Optional[datetime] = None
) -> AsyncGenerator[str, None]:
    try:
        async for chunk in stream_conversation(user_id, user_input, date):
            payload = {
                "message": chunk.get("message", "chatbot_response"),
                "data": chunk.get("data", {})
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            # 클라이언트 버퍼 방지용 슬립
            await asyncio.sleep(0.05)

    except Exception as e:
        logger.error("stream_chat 오류가 발생했습니다.:", exc_info=True)
        err_payload = {
            "message": "chatbot_response",
            "data": {"text": "오류가 발생했습니다.", "done": True}
        }
        yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
