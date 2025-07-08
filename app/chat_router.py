from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from schemas.chat_schema import ChatRequest
from app.chat_controller import stream_chat
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 챗봇 라우터 설정
# ────────────────────────────────────────────────────────

router = APIRouter()

# 챗봇 API 엔드포인트
@router.post(
    "/chats",
    summary="챗봇과 대화 시작",
    description="메시지를 보내면 토큰 단위로 스트리밍 응답을 돌려줍니다.",
    response_class=StreamingResponse
)
async def chat_endpoint(req: ChatRequest):
    user_id = req.user_id
    logger.info("챗봇 요청 수신하여 StreamingResponse 시작")
    return StreamingResponse(
        stream_chat(user_id=user_id, user_input=req.message, date=req.date),
        media_type="text/event-stream"
    )


