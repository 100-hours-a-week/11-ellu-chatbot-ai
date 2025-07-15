from typing import AsyncGenerator, Optional, Union
from datetime import datetime
from services.streaming import handle_chat_request
import logging
from schemas.chat_schema import CalendarQueryResponse
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 챗봇 스트리밍 컨트롤러
# ────────────────────────────────────────────────────────

async def stream_chat(user_input: str, user_id: str, date: Optional[datetime] = None):
    try:
        # 커넥션 초기 dummy 메시지
        yield "data: connected\n\n"
        date_str = date.isoformat() if isinstance(date, datetime) else date
        result = await handle_chat_request(user_id, user_input, date_str)
        if callable(result): 
            async for chunk in result():
                yield chunk
        else:
            import json
            yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error("stream_chat 오류가 발생했습니다.:", exc_info=True)
        err_payload = {
            "message": "chatbot_response",
            "data": {"text": "오류가 발생했습니다.", "done": True}
        }
        yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"

async def chat_query_calendar(req: Union[dict, CalendarQueryResponse]):
    if isinstance(req, CalendarQueryResponse):
        data = req.data
    elif isinstance(req, dict) and 'message' in req and 'data' in req:
        data = req['data']
    else:
        raise HTTPException(status_code=400, detail="올바르지 않은 쿼리 응답 데이터입니다.")
    # 예외처리: None이거나 리스트가 아니면 400 에러
    if data is None or not isinstance(data, list):
        raise HTTPException(status_code=400, detail="올바르지 않은 쿼리 응답 데이터입니다.")
    return CalendarQueryResponse(message="calendar_query_result", data=data)
