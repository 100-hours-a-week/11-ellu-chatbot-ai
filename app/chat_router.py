from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from schemas.chat_schema import ChatRequest
from app.chat_controller import stream_chat

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
    return StreamingResponse(
        stream_chat(user_id=user_id, user_input=req.message, date=req.date),
        media_type="text/event-stream"
    )


