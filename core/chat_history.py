from langchain.memory import ConversationBufferWindowMemory
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 사용자 대화 히스토리 관리
# ────────────────────────────────────────────────────────

# 최근 10개 메시지를 유지하는 인메모리 대화 히스토리 관리
class UserMemoryManager:
    def __init__(self):
        self._store: Dict[str, ConversationBufferWindowMemory] = {}

    def get_user_memory(self, user_id: str) -> ConversationBufferWindowMemory:
        if user_id not in self._store:
            logger.info(f"사용자 {user_id}의 새 메모리가 생성되었습니다.")
            self._store[user_id] = ConversationBufferWindowMemory(
                memory_key="history",
                input_key="user_input",
                output_key="response",
                return_messages=True,
                k=10
            )
        else:
            logger.debug(f"사용자 {user_id}의 기존 메모리 반환")
        return self._store[user_id]
    
    # 히스토리 조회
    def get_history(self, user_id: str) -> List[str]:
        mem = self.get_user_memory(user_id)
        mem_vars = mem.load_memory_variables({})
        history = mem_vars.get("history", [])

        logger.debug(f"사용자 {user_id}의 히스토리가 로드되었습니다.")

        if isinstance(history, list):
            return [msg.content for msg in history]
        elif isinstance(history, str):
            return history.splitlines() if history else []
        else:
            logger.warning(f"예상치 못한 히스토리 타입: {type(history)}")
            history_lines = []

        logger.info(f"사용자 {user_id}의 히스토리 {len(history_lines)}개 반환되었습니다.")
        return history_lines
    
memory_manager = UserMemoryManager()