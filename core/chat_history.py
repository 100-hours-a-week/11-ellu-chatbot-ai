from langchain.memory import ConversationBufferWindowMemory
from typing import Dict, List

# ────────────────────────────────────────────────────────
# 사용자 대화 히스토리 관리
# ────────────────────────────────────────────────────────

# 최근 10개 메시지를 유지하는 인메모리 대화 히스토리 관리
class UserMemoryManager:
    def __init__(self):
        self._store: Dict[str, ConversationBufferWindowMemory] = {}

    def get_user_memory(self, user_id: str) -> ConversationBufferWindowMemory:
        if user_id not in self._store:
            self._store[user_id] = ConversationBufferWindowMemory(
                memory_key="history",
                input_key="user_input",
                output_key="response",
                return_messages=True,
                k=10
            )
        return self._store[user_id]
    
    # 히스토리 조회
    def get_history(self, user_id: str) -> List[str]:
        mem = self.get_user_memory(user_id)
        mem_vars = mem.load_memory_variables({})
        history = mem_vars.get("history", [])

        if isinstance(history, list):
            return [msg.content for msg in history]
        elif isinstance(history, str):
            return history.splitlines() if history else []
        else:
            return []
    
memory_manager = UserMemoryManager()