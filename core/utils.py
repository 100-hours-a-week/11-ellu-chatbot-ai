import datetime
from typing import Any, Generator

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

# 슬롯 dict 병합
def merge_slots(existing: dict, new: dict) -> dict:
    result = dict(existing)
    new = new or {}
    for k, v in new.items():
        if k == "type":
            continue  # type은 무시
        if v and str(v).strip():
            result[k] = v
    return result

# LLM 응답에서 content/text/response만 추출
def extract_llm_content(obj):
    if hasattr(obj, 'content'):
        return obj.content
    elif hasattr(obj, 'text'):
        return obj.text
    elif isinstance(obj, dict) and 'content' in obj:
        return obj['content']
    elif isinstance(obj, dict) and 'response' in obj:
        return obj['response']
    elif isinstance(obj, str):
        return obj
    return None

# chunk에서 content 추출
def extract_content(chunk: Any) -> Any:
    content = getattr(chunk, 'content', None)
    if content is None and isinstance(chunk, dict):
        content = chunk.get('content')
    return content if content is not None else str(chunk) 

# task_title 병합
def merge_task_title(old_title, new_title):
    if new_title is not None and str(new_title).strip() != "":
        return new_title
    return old_title or "" 

# 청크 스트리밍
def stream_llm_chunks(stream, writer=None, message_type="stream", message_key="message"):
    response_chunks = []
    for chunk in stream:
        if chunk is None:
            continue 
        content = extract_content(chunk)
        if content is not None and content != "":
            content_str = str(content)
            response_chunks.append(content_str)
            if writer:
                writer({"type": message_type, message_key: content_str})
        if isinstance(chunk, dict) and chunk.get("type") == "subtask_end":
            break
    return "".join(response_chunks) 

def safe_convert(obj):
    if isinstance(obj, dict):
        return {k: safe_convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_convert(v) for v in obj]
    elif hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
        return str(obj)
    return obj 