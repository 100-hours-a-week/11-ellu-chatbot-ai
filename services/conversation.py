import json
from datetime import datetime
from typing import Dict, Any, Optional
from core.chat_graph import chat_graph
from core.chat_history import memory_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 히스토리 저장 및 반환하여 챗봇 그래프 실행
# ────────────────────────────────────────────────────────

class ConversationService:
    def __init__(self):
        self._last_states: Dict[str, Dict[str, Any]] = {}
        self._memory_manager = memory_manager

    def run(self, user_id: str, user_input: str, date: Optional[str] = None) -> Dict[str, Any]:
        memory = memory_manager.get_user_memory(user_id)
        # mem_vars = memory.load_memory_variables({})
        # history_str = mem_vars.get("history", "")
        history_list: list[str] = self._memory_manager.get_history(user_id)

        state: Dict[str, Any] = {
            "user_input": user_input,
            "history": history_list,
            "date": date or datetime.now().isoformat(),
        }

        result = chat_graph.invoke(state)

        resp = result.get("response")
        saved_resp = resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False)
        memory.save_context({"user_input": user_input}, {"response": saved_resp})
        current_history = memory_manager.get_history(user_id)
        # logger.info("유저 아이디: %s", user_id)
        logger.info(f"{user_id} 히스토리 저장 성공")
        # logger.info("저장된 히스토리: %s", current_history)

        self._last_states[user_id] = result
        return result

conversation_service = ConversationService()