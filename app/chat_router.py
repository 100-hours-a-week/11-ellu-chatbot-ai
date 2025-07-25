from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from schemas.chat_schema import ChatRequest, CalendarQueryRequest, CalendarQueryResponse
import logging
import datetime
from services.conversation import conversation_service
from app.chat_controller import stream_chat, chat_query_calendar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 챗봇 라우터 설정
# ────────────────────────────────────────────────────────

router = APIRouter()
router_query = APIRouter()

# 챗봇 API 엔드포인트
@router.post(
    "/chats",
    summary="챗봇과 대화 시작",
    description="메시지를 보내면 토큰 단위로 스트리밍 응답을 돌려줍니다.",
    response_class=StreamingResponse
)
async def chat_endpoint(req: ChatRequest):
    date = req.date.isoformat() if isinstance(req.date, datetime.datetime) else (req.date or "")
    user_id = req.user_id or "unknown"
    user_input = req.message or ""
    return StreamingResponse(stream_chat(user_input, user_id, date), media_type="text/event-stream")

# 쿼리 API 엔드포인트
@router_query.post(
    "/chat/query",
    summary="일정 쿼리",
    description="쿼리 파라미터(JSON)를 받아서 일정 데이터를 조회하고, CalendarQueryResponse로 반환"
)
async def query_endpoint(req: CalendarQueryRequest) -> CalendarQueryResponse:
    user_id = req.user_id
    user_input = req.task_title_keyword or "캘린더 조회"
    date = req.start  

    async for mode, chunk in conversation_service.stream_schedule(user_id, user_input, date):
        if mode == "values" and "response" in chunk:
            return await chat_query_calendar({"message": "calendar_query_result", "data": chunk["response"]})
    # 예외 상황
    return await chat_query_calendar({"message": "calendar_query_result", "data": []})


