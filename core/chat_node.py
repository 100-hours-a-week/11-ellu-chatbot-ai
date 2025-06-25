from core.chat_chains import unified_slot_chain, qa_chain, exercise_chain, learning_chain, project_chain, planner_chain, other_chain, schedule_ask_chain
from langchain_core.exceptions import OutputParserException
import json
from langchain_core.exceptions import OutputParserException
from typing import Dict, Any, Optional
from datetime import datetime
from langchain_tavily import TavilySearch
from typing import Dict
from core.state import ConversationState
import logging
from langgraph.config import get_stream_writer

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
        history = "\n".join(state.get("history", []))
        
        # 현재 슬롯 대기 상태 정보 추가
        awaiting_slot = state.get("awaiting_slot")
        current_slots = state.get("slots", {})
        
        # 대화 컨텍스트 정보를 히스토리에 추가
        context_info = ""
        if current_slots:
            context_info += f"\n[현재까지 수집된 일정 정보: {current_slots}]"
        
        if awaiting_slot:
            context_info += f"\n[현재 상황: AI가 '{awaiting_slot}' 정보를 요청한 상태입니다.]"
            # context_info += f"\n[중요: 사용자 입력이 이전 일정에 대한 슬롯 입력인지 새로운 일정 요청인지 판단하세요.]"
            # context_info += f"\n[주의: AI가 슬롯을 요청한 후 사용자가 답변하는 경우, 이는 새로운 일정 요청이 아닌 슬롯 입력입니다.]"
            # context_info += f"\n[슬롯 질문 예시: '하루에 몇 시간을 할애하실 수 있나요?', '선호하는 시간대가 언제인가요?', '목표하는 기간이 어떻게 되나요?']"
        
        enhanced_history = history + context_info

        try:
            raw_output = self.chain.invoke({
                "history": enhanced_history,
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
        merged_slots = {
            **prev_slots,
            **{k: v for k, v in new_slots.items() if v}
        }
        state["slots"] = merged_slots
        logger.info("병합된 슬롯: %s", merged_slots)
        logger.info('Intent=%s, Slots=%s', state['intent'], state['slots'])
        return state

# 슬롯 업데이트 노드
class SlotUpdater(BaseNode):
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 슬롯 대기 상태가 아니면 그대로 반환
        if not state.get("awaiting_slot"):
            return state
        
        # intent가 general인 경우 슬롯 업데이트를 건너뛰고 일반 응답으로 처리
        if state.get("intent") == "general":
            logger.info("일반 질의로 판단되어 슬롯 업데이트를 건너뜁니다: %s", state["user_input"])
            state["conversation_context"] = "general_query"
            state["ask"] = False
            return state
        
        slot_name = state['awaiting_slot']
        user_value = state['user_input'].strip()
        
        # 슬롯 관련 입력으로 판단되는 경우에만 슬롯 업데이트
        if user_value:
            state.setdefault("slots", {})
            state['slots'][slot_name] = user_value
            logger.info("Updated slot: %s with value %s", slot_name, user_value)
        else:
            logger.error("Empty input for slot: %s", slot_name)

        state["conversation_context"] = "slot_filled"
        state["awaiting_slot"] = None
        # 사용자 응답을 받았으므로 ask 상태를 False로 설정
        state["ask"] = False
        # 슬롯이 채워졌으므로 intent를 schedule로 설정
        state["intent"] = "schedule"
        # 기존 카테고리 유지 (새로운 카테고리로 덮어쓰지 않음)
        if state.get("slots", {}).get("category"):
            logger.info("기존 카테고리 유지: %s", state["slots"]["category"])
        logger.info("사용자 응답을 받았습니다. ask=False로 설정합니다.")
        logger.info("슬롯이 채워져서 intent를 schedule로 설정했습니다.")
        return state

# 누락된 슬롯 질문 노드
class MissingSlotAsker(BaseNode):
    _CFG = {
        "learning": dict(required=["period", "duration_minutes", "preferred_time"], next_node="schedule_generator"),
        "exercise": dict(required=["period", "duration_minutes", "preferred_time"], next_node="exercise_searcher"),
        "project": dict(required=["deadline", "work_hours"], next_node="schedule_generator"),
        "recurring": dict(required=["start_end_time", "frequency"], next_node="schedule_generator"),
        "personal": dict(required=["start_end_time"], next_node="schedule_generator"),
        "other": dict(required=[], next_node="schedule_ask"),
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
        # 일반 질의인 경우 슬롯 질문을 건너뛰고 일반 응답으로 처리
        if state.get("intent") == "general" or state.get("conversation_context") == "general_query":
            logger.info("일반 질의로 판단되어 슬롯 질문을 건너뜁니다")
            state.update(
                ask=False,
                awaiting_slot=None,
                conversation_context="general_query",
                next_node="qa_generator",
            )
            return state
            
        cat = state.get("slots", {}).get("category", "")
        logger.info("추출된 카테고리: %s", cat)
        cfg = self._CFG.get(cat)
        if not cfg:
            state.update(
                ask=False,
                response="죄송합니다. 활동 유형을 인식할 수 없습니다. 학습, 운동, 프로젝트 또는 반복 일정 중 하나를 알려주시겠어요?",
            )
            logger.error("카테고리를 인식할 수 없습니다: %s", cat)
            return state

        # other 카테고리는 특별 처리
        if cat == "other":
            state.update(
                ask=False,
                awaiting_slot=None,
                conversation_context="other_category",
                next_node="schedule_ask",
            )
            logger.info("other 카테고리 처리: schedule_ask로 이동")
            return state

        missing = [f for f in cfg["required"] if not state["slots"].get(f)]
        logger.info("누락된 슬롯: %s", missing)
        if missing:
            need = missing[0]
            state.update(
                ask=True,
                awaiting_slot=need,
                conversation_context="awating_slot_input",
                response=self._QUESTIONS[need],
            )
        else:
            state.update(
                ask=False,
                awaiting_slot=None,
                conversation_context="awaiting_slot_input",
                next_node=cfg["next_node"],
            )
            logger.info("슬롯이 모두 추출되었습니다.")
        return state

# Tavily 검색 노드
class ExerciseSearchInfo(BaseNode):
    def __init__(self, tool: Optional[TavilySearch] = None, top_k: int = 5):
        self.tavily = tool or TavilySearch()
        self.top_k = top_k

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("task_title") or state["user_input"]
        try:
            hits = self.tavily.invoke(query) or []
            results = hits.get("result", [])
            state["search_results"] = results[: self.top_k]
            logger.info("Tavily 검색 쿼리: %s", query)
        except Exception as exc:
            logger.exception("Tavily search failed: %s", exc)
            state["search_results"] = "검색 결과를 가져오는데 실패했습니다."
        return state

# 스케줄 생성 노드 - 운동
class ExerciseScheduleGenerator(BaseNode):
    def __init__(self):
        self.chain = exercise_chain()

    def __call__(self, state, writer=None):
        if writer is None:
            writer = get_stream_writer()
        writer({"type": "schedule_start", "message": "⏳ 일정 생성 중입니다..."})
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)
        search_results = state.get('search_results', '검색 결과 없음')
        logger.info("검색 결과와 함께 운동 일정을 생성합니다.")
        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                "search_results": search_results,
                "date": state['date'] or datetime.now().isoformat()
            })
            logger.info("운동 일정 실행 결과: %s", raw_output)
            state['response'] = raw_output
            state["slots"] = {}
            logger.info("운동 일정 생성 완료 후 슬롯을 초기화했습니다.")
        except Exception as e:
            logger.error("운동 일정 생성 중 오류가 발생했습니다.: %s", e)
            state['response'] = "운동 일정 생성 중 오류가 발생했습니다."
        return state
    
    def _extra_payload(self, state):
        return {"search_results": state.get("search_results", "검색 결과 없음")}

# 스케줄 생성 노드 - 학습
class LearningScheduleGenerator(BaseNode):
    def __init__(self):
        self.chain = learning_chain()

    def __call__(self, state, writer=None):
        if writer is None:
            writer = get_stream_writer()
        writer({"type": "schedule_start", "message": "⏳ 일정 생성 중입니다..."})
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)
        logger.info("학습 일정 생성 - 병합된 슬롯 정보: %s", slots_dict)
        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                "date": state['date'] or datetime.now().isoformat()
            })
            logger.info("학습 일정을 생성합니다.")
            logger.info("학습 일정 생성 결과: %s", raw_output)
            state['response'] = raw_output
            state["slots"] = {}
            logger.info("학습 일정 생성 완료 후 슬롯을 초기화했습니다.")
        except Exception as e:
            logger.error("학습 일정 생성 중 오류가 발생했습니다.: %s", e)
            state['response'] = "학습 일정 생성 중 오류가 발생했습니다."
        return state
    
# 스케줄 생성 노드 - 프로젝트
class ProjectScheduleGenerator(BaseNode):
    def __init__(self):
        self.chain = project_chain()

    def __call__(self, state, writer=None):
        if writer is None:
            writer = get_stream_writer()
        writer({"type": "schedule_start", "message": "⏳ 일정 생성 중입니다..."})
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)
        logger.info("프로젝트 일정을 생성합니다.")
        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                "date": state['date'] or datetime.now().isoformat()
            })
            logger.info("프로젝트 일정 생성 결과: %s", raw_output)
            state['response'] = raw_output
            state["slots"] = {}
            logger.info("프로젝트 일정 생성 완료 후 슬롯을 초기화했습니다.")
        except Exception as e:
            logger.error("프로젝트 일정 생성 중 오류가 발생했습니다.: %s", e)
            state['response'] = "프로젝트 일정 생성 중 오류가 발생했습니다."
        return state
    
# 스케줄 생성 노드 - 반복, 개인 일정
class PlannerGenerator(BaseNode):
    def __init__(self):
        self.chain = planner_chain()

    def __call__(self, state, writer=None):
        if writer is None:
            writer = get_stream_writer()
        writer({"type": "schedule_start", "message": "⏳ 일정 생성 중입니다..."})
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)
        logger.info("반복 및 개인 일정을 생성합니다.")
        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                "date": state['date'] or datetime.now().isoformat()
            })
            logger.info("반복 및 개인 일정을 생성 결과: %s", raw_output)
            state['response'] = raw_output
            state["slots"] = {}
            logger.info("반복 및 개인 일정 생성 완료 후 슬롯을 초기화했습니다.")
        except Exception as e:
            logger.error("반복 및 개인 일정 생성 중 오류가 발생했습니다: %s", e)
            state['response'] = "반복 및 개인 일정 생성 중 오류가 발생했습니다."
        return state
    
class ScheduleAsk(BaseNode):
    def __init__(self):
        self.chain = schedule_ask_chain()

    def __call__(self, state: ConversationState) -> dict:
        history = "\n".join(state.get("history", []))
        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "date": state['date'] or datetime.now().isoformat()
            })
            logger.info("기타 유형에 대한 재질문: %s", raw_output)
            state['response'] = raw_output
            # 사용자 응답을 기다리도록 ask 상태 설정
            state['ask'] = True
            logger.info("사용자 응답을 기다립니다.")

        except Exception as e:
            logger.error("기타 유형에 대한 재질문 중 오류가 발생했습니다: %s", e)
            state['response'] = "기타 유형에 대한 재질문 중 오류가 발생했습니다."

        return state
    
class OtherGenerator(BaseNode):
    def __init__(self):
        self.chain = other_chain()

    def __call__(self, state, writer=None):
        if writer is None:
            writer = get_stream_writer()
        writer({"type": "schedule_start", "message": "⏳ 일정 생성 중입니다..."})
        history = "\n".join(state.get("history", []))
        slots_dict = state.get('slots', {})
        slots_json = json.dumps(slots_dict, ensure_ascii=False)
        logger.info("기타 유형에 대한 일정을 생성합니다.")
        try:
            raw_output = self.chain.invoke({
                "history": history,
                "user_input": state['user_input'],
                "slots": slots_json,
                "date": state['date'] or datetime.now().isoformat()
            })
            logger.info("기타 유형에 대한 일정 생성 결과: %s", raw_output)
            state['response'] = raw_output
            state["slots"] = {}
            logger.info("기타 유형에 대한 일정 생성 완료 후 슬롯을 초기화했습니다.")
        except Exception as e:
            logger.error("기타 유형에 대한 일정 생성 중 오류가 발생했습니다: %s", e)
            state['response'] = "기타 유형에 대한 일정 생성 중 오류가 발생했습니다."
        return state
    
# 일반 QA 생성 노드
class QaGenerator(BaseNode):
    def __init__(self):
        self.chain = qa_chain()

    def __call__(self, state: ConversationState) -> dict:
        history = "\n".join(state.get("history", []))
        logger.info("일반 질의: %s", state['user_input'])

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
            
            logger.info("일반 질의에 대해 답변합니다.")
            logger.info("일반 질의 응답 결과: %s", response_result)
            
        except Exception as e:
            logger.error("일반 질의에 답변하는 중 오류가 발생했습니다.: %s", e)
            state['response'] = "일반 질의에 답변하는 중 오류가 발생했습니다."

        return state