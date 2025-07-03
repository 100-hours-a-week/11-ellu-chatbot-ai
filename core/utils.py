import datetime
from typing import Any, Dict, Generator

# datetime, dict, list를 문자열로 변환
def convert_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: convert_datetime(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_datetime(i) for i in obj]
    return obj

# 챗봇 메시지 payload 생성
def make_payload(message_type: str, data: dict) -> dict:
    return {"message": message_type, "data": data}

# 텍스트를 토큰 단위로 yield
def yield_tokens(text: str, message_type: str, data_key: str = "text") -> Generator[dict, None, None]:
    tokens = text.split()
    for i, token in enumerate(tokens):
        yield make_payload(message_type, {data_key: token, "done": i == len(tokens) - 1})

# LLM 응답 파싱
def parse_llm_response(raw_output: Any) -> Any:
    if isinstance(raw_output, dict):
        if 'response' in raw_output:
            return raw_output['response']
        else:
            return raw_output
    return str(raw_output)

# 슬롯 dict 병합 (빈 값은 무시)
def merge_slots(existing: dict, new: dict) -> dict:
    for k, v in new.items():
        if v and v.strip():
            existing[k] = v
    return existing

# chunk에서 content 추출
def extract_content(chunk: Any) -> Any:
    content = getattr(chunk, 'content', None)
    if content is None and isinstance(chunk, dict):
        content = chunk.get('content')
    return content if content is not None else str(chunk) 