from core.chat_chains import unified_slot_chain, qa_chain, exercise_chain, learning_chain, project_chain, planner_chain
from langchain_core.exceptions import OutputParserException
import json
from langchain_core.exceptions import OutputParserException
from typing import Dict, Any, Optional
from datetime import datetime
from langchain_community.tools import TavilySearchResults
from typing import TypedDict, List, Dict
from core.state import ConversationState
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────
# 챗봇 대화 노드 정의
# ────────────────────────────────────────────────────────

class BaseNode:
    def __call__(self, state: ConversationState) -> ConversationState:
        try:
            return self._run(state)
        except Exception as exc:
            logger.exception(f"{self.__class__.__name__} failed: %s", exc)
            state['response'] = '서버 내부 오류가 발생했습니다.'
            return state

    def _run(self, state: ConversationState) -> ConversationState:
        raise NotImplementedError(f"_run not implemented in {self.__class__.__name__}")

# intent 분류 및 슬롯 추출 노드
class DetectedIntent(BaseNode):
    def __init__(self):
        self.chain = unified_slot_chain()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if state.get("conversation_context") == "awaiting_slot_input":
            logger.info("재질문 응답으로 질문 생략")
            return state

        history = "\n".join(state.get("history", []))

        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state["user_input"]
            })
            logger.info("User Info: %s", state["user_input"])
            logger.info("DetectedIntent raw_output: %s", raw_output)
            if not isinstance(raw_output, dict):
                raise OutputParserException(f"Expected dict but got {type(raw_output)}")
            parsed = raw_output

        except Exception as e:
            logger.exception("Failed to parse intent and slots: %s", e)
            parsed = {'task_title': None, 'intent': 'general', 'slots': {}}

        state["task_title"] = parsed.get("task_title")
        state["intent"] = parsed.get("intent", "general")
        prev_slots = state.get("slots", {})
        new_slots = parsed.get("slots", {})

        # 빈 문자열 필터링하여 병합
        filtered_new_slots = {k: v for k, v in new_slots.items() if v != ""}
        state["slots"] = {**prev_slots, **filtered_new_slots}
        logger.info('Intent=%s, Slots=%s', state['intent'], state['slots'])
        return state

# 슬롯 업데이트 노드
class SlotUpdater(BaseNode):
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if state.get('awaiting_slot'):
            slot_name = state['awaiting_slot']
            user_value = state['user_input'].strip()
            
            # conversation_context가 설정되어 있으면 기존 intent와 slots 정보 유지
            if state.get('conversation_context') == 'awaiting_slot_input':
                if user_value:
                    if 'slots' not in state:
                        state['slots'] = {}
                    state['slots'][slot_name] = user_value
                    print(f"✅ Updated slot '{slot_name}' with value: {user_value}")
                    print(f"✅ Current slots: {state['slots']}")
                else:
                    print(f"❌ Empty input for slot '{slot_name}'")

        return state

# 누락된 슬롯 질문 노드
class MissingSlotAsker(BaseNode):
    _CFG = {
        "learning": dict(required=["period", "duration_minutes", "preferred_time"], next_node="schedule_generator"),
        "exercise": dict(required=["period", "duration_minutes", "preferred_time"], next_node="exercise_searcher"),
        "project": dict(required=["deadline", "work_hours"], next_node="schedule_generator"),
        "recurring": dict(required=["start_end_time", "frequency"], next_node="schedule_generator"),
        "personal": dict(required=["start_end_time"], next_node="schedule_generator"),
    }

    _QUESTIONS = {
        "period": "목표하는 기간이 어떻게 되나요? (예: 3일)",
        "duration_minutes": "하루에 몇 시간을 할애하실 수 있나요? (예: 1시간)",
        "preferred_time": "선호하는 시간대가 언제인가요?",
        "deadline": "프로젝트 마감일이 언제인가요? (예: 2025‑05‑26)",
        "work_hours": "프로젝트 업무시간을 알려주세요. (예: 09:00-17:00)",
        "frequency": "반복 주기가 어떻게 되나요? (예: 매일, 매주 월요일)",
        "start_end_time": "일정 시작 시간과 종료 시간을 알려주세요. (예: 09:00-10:00)",
    }

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cat = state.get("slots", {}).get("category", "")
        cfg = self._CFG.get(cat)
        if not cfg:
            state.update(
                ask=False,
                response="죄송합니다. 활동 유형을 인식할 수 없습니다. 학습, 운동, 프로젝트 또는 반복 일정 중 하나를 알려주시겠어요?",
            )
            print(f"인식불가 카테고리: {cat}")
            return state

        missing = [f for f in cfg["required"] if not state["slots"].get(f)]
        print(f"Missing slots for category '{cat}': {missing}")
        if missing:
            need = missing[0]
            state.update(
                ask=True,
                awaiting_slot=need,
                conversation_context=None,
                response=self._QUESTIONS[need],
            )
        else:
            state.update(
                ask=False,
                awaiting_slot=None,
                conversation_context="awaiting_slot_input",
                next_node=cfg["next_node"],
                response="필요한 정보를 모두 확인했습니다. 일정을 생성합니다.",
            )
        return state

# Tavily 검색 노드
class ExerciseSearchInfo(BaseNode):
    def __init__(self, tool: Optional[TavilySearchResults] = None, top_k: int = 5):
        self.tavily = tool or TavilySearchResults()
        self.top_k = top_k

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("task_title") or state["user_input"]
        try:
            hits = self.tavily.invoke(query) or []
            state["search_results"] = hits[: self.top_k]
            logger.info(f"Tavily search results {query}: %s", state["search_results"])
        except Exception as exc:
            logger.exception("Tavily search failed: %s", exc)
            state["search_results"] = "검색 결과를 가져오는데 실패했습니다."
        return state

# 스케줄 생성 노드 - 운동
class ExerciseScheduleGenerator(BaseNode):
    def run(state: ConversationState) -> dict:
        """검색 결과를 활용한 운동 스케줄 생성"""
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)
        search_results = state.get('search_results', '검색 결과 없음')

        print(f"Generating exercise schedule with search results")

        try:
            raw_output = exercise_chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                "search_results": search_results,
                "date": state['date'] or datetime.now().isoformat()
            })
            print("Raw exercise chain output:", raw_output)
            state['response'] = raw_output

        except Exception as e:
            print(f"Error generating exercise schedule: {e}")
            state['response'] = "운동 일정 생성 중 오류가 발생했습니다."

        return state
    
    def _extra_payload(self, state):
        return {"search_results": state.get("search_results", "검색 결과 없음")}

# 스케줄 생성 노드 - 학습
class LearningScheduleGenerator(BaseNode):
    def __init__(self):
        self.chain = learning_chain()

    def __call__(self, state: ConversationState) -> dict:
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)
        # relevant_docs = state.get('relevant_docs') or '관련 문서 없음'

        # print(f"Generating learning schedule with RAG docs")

        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                # "relevant_docs": relevant_docs,
                "date": state['date'] or datetime.now().isoformat()
            })
            print("Raw learning chain output:", raw_output)
            state['response'] = raw_output

        except Exception as e:
            print(f"Error generating learning schedule: {e}")
            state['response'] = "학습 일정 생성 중 오류가 발생했습니다."

        return state
    
# 스케줄 생성 노드 - 프로젝트
class ProjectScheduleGenerator(BaseNode):
    def __init__(self):
        self.chain = project_chain()

    def __call__(self, state: ConversationState) -> dict:
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)
        # relevant_docs = state.get('relevant_docs') or '관련 문서 없음'

        # print(f"Generating project schedule with RAG docs")

        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                # "relevant_docs": relevant_docs,
                "date": state['date'] or datetime.now().isoformat()
            })
            print("Raw Project chain output:", raw_output)
            state['response'] = raw_output

        except Exception as e:
            print(f"Error generating Project schedule: {e}")
            state['response'] = "프로젝트 일정 생성 중 오류가 발생했습니다."

        return state
    
# 스케줄 생성 노드 - 반복, 개인 일정
class PlannerGenerator(BaseNode):
    def __init__(self):
        self.chain = planner_chain()

    def __call__(self, state: ConversationState) -> dict:
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)

        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                "date": state['date'] or datetime.now().isoformat()
            })
            print("Raw Planner chain output:", raw_output)
            state['response'] = raw_output

        except Exception as e:
            print(f"Error generating planner schedule: {e}")
            state['response'] = "일반 일정 생성 중 오류가 발생했습니다."

        return state
# 일반 QA 생성 노드
class QaGenerator(BaseNode):
    def __init__(self):
        self.chain = qa_chain()

    def __call__(self, state: ConversationState) -> dict:
        history = "\n".join(state.get("history", []))
        print(f"Handling general QA for user input: {state['user_input']}")

        try:
            response_result = self.chain.invoke({
                "history": history, 
                "user_input": state['user_input'],
                "date": state['date'] or datetime.now().isoformat()
            })

            # 응답 텍스트 추출
            if isinstance(response_result, dict):
                if 'response' in response_result:
                    state['response'] = response_result['response']
                elif 'text' in response_result:
                    state['response'] = response_result['text']
                else:
                    state['response'] = str(response_result)
            else:
                state['response'] = str(response_result)
                
            print("General QA response:", state['response'])
            
        except Exception as e:
            print(f"Error in general QA chain: {e}")
            state['response'] = "일반적인 질문에 답변하는 중 오류가 발생했습니다."

        return state