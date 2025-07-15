import asyncio
from typing import Optional
from services.conversation import conversation_service
import logging
from core.utils import convert_datetime, make_payload, yield_tokens, extract_llm_content
import json

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
        if mode == "custom" and isinstance(chunk, dict) and chunk.get("type") == "schedule_start":
            message = extract_llm_content(chunk.get("message", ""))
            if message:
                for payload in yield_tokens(message, "chatbot_message", data_key="text"):
                    yield f"data: {json.dumps(convert_datetime(payload), ensure_ascii=False)}\n\n"
        elif mode == "custom" and isinstance(chunk, dict) and chunk.get("type") == "subtask":
            detail = chunk.get("message", "")
            payload = make_payload(
                "task_response",
                {
                    "task_title": extract_llm_content(chunk.get("task_title", "")) if isinstance(chunk, dict) else "",
                    "category": extract_llm_content(chunk.get("category", "")) if isinstance(chunk, dict) else "",
                    "detail": detail if detail else "",
                    "done": False
                }
            )
            yield f"data: {json.dumps(convert_datetime(payload), ensure_ascii=False)}\n\n"
            subtask_yielded = True
        elif mode == "custom" and isinstance(chunk, dict) and chunk.get("type") == "subtask_end":
            end_text = "🗓️ 일정 생성이 완료되었습니다. 캘린더를 확인해주세요."
            for payload in yield_tokens(end_text, "chatbot_message", data_key="text"):
                if payload["data"]["text"] == end_text.split()[-1]:
                    payload["data"]["done"] = True
                yield f"data: {json.dumps(convert_datetime(payload), ensure_ascii=False)}\n\n"
        elif mode == "values" and isinstance(chunk, dict) and "response" in chunk:
            resp = extract_llm_content(chunk["response"])
            if resp:
                for payload in yield_tokens(resp, "chatbot_response", data_key="token"):
                    yield f"data: {json.dumps(convert_datetime(payload), ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.1)

async def handle_chat_request(user_id: str, user_input: str, date: str):
    stream = stream_conversation(user_id=user_id, user_input=user_input, date=date)
    first_chunk = None
    async for chunk in stream:
        if not chunk or (isinstance(chunk, str) and not chunk.strip()):
            continue
        try:
            if isinstance(chunk, (bytes, str)):
                chunk_str = chunk.decode() if isinstance(chunk, bytes) else chunk
                if chunk_str.startswith("data: "):
                    chunk_str = chunk_str[len("data: "):]
                chunk_data = json.loads(chunk_str)
            else:
                chunk_data = chunk
            first_chunk = chunk_data
            break
        except Exception as e:
            logger.warning(f"Invalid chunk received: {chunk} ({e})")
            continue

    async def merged_stream():
        if first_chunk:
            import json
            yield f"data: {json.dumps(first_chunk, ensure_ascii=False)}\n\n"
        async for chunk in stream:
            if isinstance(chunk, (bytes, str)):
                yield chunk if isinstance(chunk, str) else chunk.decode()
            else:
                import json
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    return merged_stream