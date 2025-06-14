import asyncio
from typing import Optional
from services.conversation import conversation_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 스트리밍 응답
# ────────────────────────────────────────────────────────

async def stream_conversation(user_id: str, user_input: str, date: Optional[str] = None):    # 1) 결과 호출
    result = conversation_service.run(user_id, user_input, date=date)
    resp = result.get("response")

    # 스케줄 생성 응답인지 판별
    is_schedule = isinstance(resp, dict) and resp.get("detail")
    detail_list = resp.get("detail", []) if is_schedule else []

    # 스케줄 생성 안내 (스케줄일 때만)
    if is_schedule:
        logger.info("일정 생성 응답 Streaming 시작")
        yield {
            "message": "chatbot_message",
            "data": {
                "text": "⏳ 일정 생성 중입니다...",
                "done": False
            }
        }
        await asyncio.sleep(0.3)

        # 서브태스크별 스트리밍
        task_title = resp.get("task_title", "")
        category   = resp.get("category", "")
        for i, sub in enumerate(detail_list):
            logger.debug(f"Subtask {i+1}: {sub}")
            yield {
                "message": "task_response",
                "data": {
                    "task_title": task_title,
                    "category": category,
                    "detail": sub,
                    "done": False
                }
            }
            await asyncio.sleep(0.1)

        # 완료 메시지
        logger.info("일정 생성 완료 메시지 전송")
        yield {
            "message": "chatbot_message",
            "data": {
                "text": "🗓️ 일정 생성이 완료되었습니다. 캘린더를 확인해주세요.",
                "done": True
            }
        }

    # 일반 텍스트 응답 스트리밍
    else:
        logger.info("일반 텍스트 응답 Streaming 시작")
        full_text = resp if isinstance(resp, str) else str(resp)
        tokens = full_text.split()
        for i, token in enumerate(tokens):
            yield {
                "message": "chatbot_response",
                "data": {
                    "token": token,
                    "done": i == len(tokens) - 1
                }
            }
            await asyncio.sleep(0.05)
        logger.info("일반 텍스트 응답 스트리밍 완료")


