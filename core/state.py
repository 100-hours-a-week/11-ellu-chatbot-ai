from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

# ────────────────────────────────────────────────────────
# 챗봇 Graph 상태 정의
# ────────────────────────────────────────────────────────

class ConversationState(TypedDict):
    user_id: Optional[str]
    user_input: str
    history: List[str] 
    task_title: Optional[str] 
    intent: Optional[str] # schedule or general
    slots: Dict[str, Any] 
    response: Optional[str] 
    date: Optional[datetime]  # 현재 시간
    ask: Optional[bool] 
    awaiting_slot: Optional[str]
    conversation_context: Optional[str]
    search_results: Optional[str]  # Tavily 검색 결과
    next_node: Optional[str]
    # relevant_docs: Optional[str]   # RAG 관련 문서
    recommended_slots: Optional[Dict[str, Any]]
    recommendation_given: Optional[bool]
    schedule_ready: Optional[bool]
    user_feedback: Optional[str]  # recommend, generate, other