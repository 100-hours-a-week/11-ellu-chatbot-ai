import asyncio
from typing import Optional
from services.conversation import conversation_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 스트리밍 응답
# ────────────────────────────────────────────────────────

async def stream_conversation(user_id: str, user_input: str, date: Optional[str] = None):
    intent = preview_state.get("intent")
    ask    = preview_state.get("ask")
    slots  = preview_state.get("slots", {})

    category_cfg = {
        "learning":  ["period", "duration_minutes", "preferred_time"],
        "exercise":  ["period", "duration_minutes", "preferred_time"],
        "project":   ["deadline", "work_hours"],
        "recurring": ["start_end_time", "frequency"],
        "personal":  ["start_end_time"],
    }
    required = category_cfg.get(slots.get("category"), [])

    all_filled = intent == "schedule" and not ask and all(slots.get(k) for k in required)

    # 슬롯이 전부 채워졌다면 로딩 메시지
    if all_filled:
        logger.info("모든 슬롯 충족 → 일정 생성 시작 알림 전송")
        loading_text = "⏳ 일정 생성 중입니다..."
        for i, tok in enumerate(loading_text.split()):
            yield {
                "message": "chatbot_message",      
                "data": {
                    "text": tok,    
                    "done": False
                }
            }
            await asyncio.sleep(0.1) 


    result = await conversation_service.run(user_id, user_input, date=date)
    resp = result.get("response")

    # 스케줄 생성 응답인지 판별
    is_schedule = isinstance(resp, dict) and resp.get("detail")
    detail_list = resp.get("detail", []) if is_schedule else []

    # 스케줄일 때 응답 스트리밍
    if is_schedule:
        logger.info("일정 생성 응답 Streaming 시작")
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
        end_text = "🗓️ 일정 생성이 완료되었습니다. 캘린더를 확인해주세요."
        tokens = end_text.split()
        for i, tok in enumerate(tokens):
            yield {
                "message": "chatbot_message",
                "data": {
                    "text": tok,
                    "done": i == len(tokens) - 1
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
            await asyncio.sleep(0.1)
        logger.info("일반 텍스트 응답 스트리밍 완료")


