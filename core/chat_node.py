from core.chat_chains import qa_chain, exercise_chain, learning_chain, project_chain, planner_chain, other_chain, schedule_ask_chain, slot_recommendation_chain, intent_chain, slot_category_chain, calendar_query_generation_chain, calendar_query_summary_chain
import json
from typing import Dict, Any, Optional, cast, Iterable
from datetime import datetime
from langchain_tavily import TavilySearch
from core.state import ConversationState
import logging
from langgraph.config import get_stream_writer
import re
from core.utils import parse_llm_response, merge_slots, extract_content, merge_task_title, stream_llm_chunks

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

# 사용자 피드백 처리 노드
class UserFeedbackProcessor(BaseNode):
    def __call__(self, state: ConversationState) -> ConversationState:
        if state.get("user_feedback") == "recommend":
            state["conversation_context"] = "requesting_recommendation"
        return state

# 슬롯 추천 노드
class SlotRecommender(BaseNode):
    def __init__(self):
        self.chain = slot_recommendation_chain()

    def __call__(self, state: ConversationState, writer=None) -> ConversationState:
        history = "\n".join(state.get("history", []))
        current_slots = state.get("slots", {})
        category = current_slots.get("category", "")
        awaiting_slot = state.get("awaiting_slot")
        logger.info("[SlotRecommender] category: %s, awaiting_slot: %s", category, awaiting_slot)
        default_recommendations = {
            "learning": {"period": "1주일", "duration_minutes": "1시간", "preferred_time": "오후 2-4시"},
            "exercise": {"period": "1주일", "duration_minutes": "30분", "preferred_time": "아침 7-8시"},
            "project": {"deadline": "2주 후", "work_hours": "09:00-18:00"},
            "other": {"start_end_time": "09:00-10:00", "frequency": "매일"}
        }
        try:
            recommend_slots = {k: v for k, v in current_slots.items() if v == "recommend"}
            target_slots = {}
            if awaiting_slot:
                target_slots[awaiting_slot] = "recommend"
            else:
                target_slots = recommend_slots
                if recommend_slots:
                    first_recommend_slot = list(recommend_slots.keys())[0]
                    state["awaiting_slot"] = first_recommend_slot
                    logger.info("[SlotRecommender] awaiting_slot: %s", first_recommend_slot)
            slot_name = list(target_slots.keys())[0] if target_slots else None
            default_value = default_recommendations.get(category, {}).get(slot_name, "적절한 값") if slot_name else "적절한 값"
            slots_json = json.dumps(current_slots, ensure_ascii=False)
            def chunk_writer(chunk):
                if writer:
                    writer(chunk)
            state['response'] = stream_llm_chunks(self.chain.stream({
                "history": history,
                "user_input": state["user_input"],
                "slots": slots_json,
                "category": category,
                "date": state.get('date') or datetime.now().isoformat()
            }), chunk_writer)
            raw_output = state['response']
            logger.info("recommend response: %s", raw_output)
            llm_response = parse_llm_response(raw_output)
            recommended_value = default_value
            if isinstance(raw_output, dict) and 'recommended_slots' in raw_output and slot_name:
                recommended_slots = raw_output['recommended_slots']
                if slot_name in recommended_slots:
                    recommended_value = recommended_slots[slot_name]
            slot_value = recommended_value
            recommendation_msg = str(llm_response) if llm_response and str(llm_response).strip() else f"다음과 같이 추천드립니다:\n• {slot_value}"
            state["response"] = recommendation_msg
            state["ask"] = True
            state["conversation_context"] = "recommendation_given"
            state["recommended_slots"] = {slot_name: recommended_value} if slot_name else {}
            state["recommendation_given"] = True
            # logger.info("[SlotRecommender] 슬롯 추천 완료: %s", slot_name)
        except Exception as e:
            logger.error("슬롯 추천 중 오류 발생: %s", e)
            if awaiting_slot or recommend_slots:
                slot_name = awaiting_slot or list(recommend_slots.keys())[0]
                default_value = default_recommendations.get(category, {}).get(slot_name, "적절한 값")
                state["recommended_slots"] = {slot_name: default_value}
                state["recommendation_given"] = False
                state["response"] = f"추천을 생성하는 중 오류가 발생했습니다. '{default_value}'으로 진행하시겠습니까?"
            else:
                state["response"] = "추천을 생성하는 중 오류가 발생했습니다."
            state["ask"] = True
        return state

# intent만 추출 노드
class IntentDetector(BaseNode):
    def __init__(self):
        self.chain = intent_chain()

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
        enhanced_history = history + context_info
        try:
            result = self.chain.invoke({
                "history": enhanced_history,
                "user_input": state["user_input"]
            })
            # logger.info("[IntentDetected] 사용자 입력: %s", state["user_input"])
            logger.info("[IntentDetected] raw_output: %s", result)
            if isinstance(result, dict):
                intent = result.get("response", "general")
            else:
                intent = str(result).strip()
        except Exception as e:
            logger.exception("[IntentDetected] Error: %s", e)
            intent = "general"
        return dict(state, intent=intent)

# slot/category 추출 노드
class SlotCategoryExtractor(BaseNode):
    def __init__(self):
        self.chain = slot_category_chain()

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # intent가 schedule 또는 confirm일 때만 동작
        if state.get("intent", "").strip().lower() not in ["schedule", "confirm"]:
            return state
        if state.get("intent", "").strip().lower() == "confirm" and state.get("slots", {}).get("category") == "other":
            merged_task_title = merge_task_title(state.get("task_title", ""), state.get("slots", {}).get("task_title", ""))
            return dict(state, task_title=merged_task_title)
        history = "\n".join(state.get("history", []))
        task_title = state.get("task_title", "")
        try:
            result = self.chain.invoke({
                "history": history,
                "user_input": state["user_input"],
                "task_title": task_title
            })
            logger.info("[SlotCategoryExtractor] %s", result)
            new_slots = merge_slots(state.get("slots", {}), result.get("slots", {})) if isinstance(result, dict) else state.get("slots", {})
            new_state = dict(state)
            new_state["slots"] = new_slots
            if isinstance(result, dict):
                if "type" in result and result["type"]:
                    new_state["type"] = result["type"]
                for key in ["recommend_ask", "schedule_ask"]:
                    if key in result:
                        new_state["slots"][key] = result[key]
                if result.get("task_title"):
                    new_state["slots"]["task_title"] = result.get("task_title")
                new_state["task_title"] = result.get("task_title", "")
                if "category" in new_state["slots"]:
                    new_state["category"] = new_state["slots"]["category"]
                has_recommend_slots = any(v == "recommend" for v in new_state["slots"].values())
                has_recommend_ask = new_state["slots"].get("recommend_ask", False) in [True, "True", "true"]
                if has_recommend_slots or has_recommend_ask:
                    new_state["user_feedback"] = "recommend"
                else:
                    if state.get("user_feedback") is None:
                        new_state["user_feedback"] = None
            else:
                logger.warning("[SlotCategoryExtractor] LLM 응답이 dict가 아님: %s", result)
            return new_state
        except Exception as e:
            logger.exception("[SlotCategoryExtractor] Error: %s", e)
            if "slots" not in state:
                return dict(state, slots={})
            return state

# 누락된 슬롯 질문 노드
class MissingSlotAsker(BaseNode):
    _CFG = {
        "learning": dict(required=["period", "duration_minutes", "preferred_time"], next_node="generate_learning_schedule"),
        "exercise": dict(required=["period", "duration_minutes", "preferred_time"], next_node="search_exercise_info"),
        "project": dict(required=["period", "duration_minutes", "preferred_time"], next_node="generate_project_schedule"),
        "other": dict(required=[], next_node="schedule_ask"),
        "personal": dict(required=["frequency", "start_end_time"], next_node="generate_schedule"),
    }

    _QUESTIONS = {
        "period": "목표하는 기간이 어떻게 되나요? (예: 3일)",
        "duration_minutes": "하루에 몇 시간을 할애하실 수 있나요? (예: 1시간)",
        "preferred_time": "선호하는 시간대가 언제인가요?",
        "frequency": "반복 주기가 어떻게 되나요? (예: 매일, 매주 월요일)",
        "start_end_time": "일정 시작 시간과 종료 시간을 알려주세요. (예: 09:00-10:00)",
    }

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # intent가 confirm이면 카테고리에 따라 일정 생성 노드로 분기
        if state.get("intent", "").strip().lower() == "confirm":
            cat = state.get("slots", {}).get("category", "")
            task_title = state.get("task_title", "")
            type = state.get("type", "")
            if cat == "exercise":
                next_node = "search_exercise_info"
            elif cat == "learning":
                next_node = "generate_learning_schedule"
            elif cat == "project":
                next_node = "generate_project_schedule"
            else:
                next_node = "generate_other_schedule"
            return dict(state,
                ask=False,
                awaiting_slot=None,
                conversation_context="user_confirmed",
                next_node=next_node,
                task_title=task_title,
                type=type
            )
        
        if state.get("awaiting_slot") and state.get("user_input"):
            state["awaiting_slot"] = None
            state["ask"] = False
            state["intent"] = "schedule"

        cat = state.get("slots", {}).get("category", "")
        cfg = self._CFG.get(cat)
        if not cfg:
            return dict(state,
                ask=False,
                response="죄송합니다. 활동 유형을 인식할 수 없습니다. 학습, 운동, 프로젝트 또는 반복 일정 중 하나를 알려주시겠어요?",
                next_node=None 
            )
            logger.error("[MissingSlotAsker] 카테고리를 인식할 수 없습니다: %s", cat)
            return state

        # other 카테고리는 특별 처리
        if cat == "other":
            slots = state["slots"]
            has_recommend = any(v == "recommend" for k, v in slots.items() if k != "category")
            has_auto = all(v == "auto" for k, v in slots.items() if k != "category")
            schedule_ask_true = any((k == "schedule_ask" and (v is True or str(v).lower() == "true")) for k, v in slots.items())
            schedule_ask_false = all((k != "schedule_ask" or v is False or str(v).lower() == "false") for k, v in slots.items())
            recommend_ask_true = any((k == "recommend_ask" and (v is True or str(v).lower() == "true")) for k, v in slots.items())
            recommend_ask_false = all((k != "recommend_ask" or v is False or str(v).lower() == "false") for k, v in slots.items())
            # 1. schedule_ask true가 있으면 schedule_ask로 이동
            if schedule_ask_true:
                state['ask'] = False
                state['awaiting_slot'] = None
                state['conversation_context'] = "other_category"
                state['next_node'] = "schedule_ask"
                return state
            # 2. recommend_ask true이거나 recommend 슬롯이 있으면 추천 단계로
            elif recommend_ask_true or has_recommend:
                state.update(
                    ask=True,
                    awaiting_slot=None,
                    conversation_context="recommendation_given",
                    next_node="recommend_slots",  
                )
                return state
            # 3. 모두 auto이거나 schedule_ask false/recommend_ask false만 있으면 바로 일정 생성
            elif has_auto or (schedule_ask_false and recommend_ask_false):
                state.update(
                    ask=False,
                    awaiting_slot=None,
                    conversation_context="awaiting_slot_input",
                    next_node="generate_other_schedule",
                )
                return state
            else:
                # recommend, auto, schedule_ask, recommend_ask 모두 없으면 schedule_ask로 이동
                state.update(
                    ask=False,
                    awaiting_slot=None,
                    conversation_context="other_category",
                    next_node="schedule_ask",
                )
                return state

        missing = [f for f in cfg["required"] if not state["slots"].get(f)]
        # logger.info("[MissingSlotAsker] missing slot: %s", missing)

        # 모든 필수 슬롯이 'auto' 또는 값이 있으면 바로 일정 생성으로 분기
        all_auto_or_filled = all(
            (state["slots"].get(f) and state["slots"].get(f) == "auto") or state["slots"].get(f)
            for f in cfg["required"]
        )
        type_value = str(state.get('type') or state.get('slots', {}).get('type', '')).strip().lower()
        # type이 명시되어 있으면 category와 무관하게 type 우선 분기
        if type_value:
            if type_value == 'personal':
                for required_slot in self._CFG["personal"]["required"]:
                    if not state["slots"].get(required_slot):
                        state.update(
                            ask=True,
                            awaiting_slot=required_slot,
                            conversation_context="awating_slot_input",
                            response=self._QUESTIONS[required_slot],
                            next_node="generate_schedule",
                        )
                        return state
                state.update(
                    ask=False,
                    awaiting_slot=None,
                    conversation_context="awaiting_slot_input",
                    next_node="generate_schedule",
                )
                return state
            # type이 다른 값일 경우에도 필요하다면 여기에 추가 분기 가능
        if all_auto_or_filled and cfg["required"]:
            if type_value == 'personal':
                # 위에서 처리됨
                pass
            else:
                state.update(
                    ask=False,
                    awaiting_slot=None,
                    conversation_context="awaiting_slot_input",
                    next_node=cfg["next_node"],
                )
                # logger.info("[MissingSlotAsker] 모든 필수 슬롯이 auto 또는 값이 있어 바로 일정 생성으로 이동합니다.")
        elif missing:
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
            # logger.info("[MissingSlotAsker] 슬롯이 모두 추출되었습니다.")
        return state

# Tavily 검색 노드
class ExerciseSearchInfo(BaseNode):
    def __init__(self, tool: Optional[TavilySearch] = None, top_k: int = 5):
        self.tavily = tool or TavilySearch()
        self.top_k = top_k

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("task_title") or state["user_input"]
        try:
            hits = self.tavily.invoke(query) or {}
            results = hits.get("result", [])
            state["search_results"] = results[: self.top_k]
            logger.info("[ExerciseSearchInfo] search query: %s", query)
        except Exception as exc:
            logger.exception("[ExerciseSearchInfo] Error %s", exc)
            state["search_results"] = "검색 결과를 가져오는데 실패했습니다."
        return state

class BaseChainNode(BaseNode):
    chain = None
    log_prefix = ""
    extra_invoke_args = []

    def __call__(self, state, writer=None):
        history = "\n".join(state.get("history", []))
        invoke_args = {
            "history": history,
            "user_input": state.get('user_input', ''),
            "date": state.get('date') or datetime.now().isoformat(),
        }
        for arg in self.extra_invoke_args:
            invoke_args[arg] = state.get(arg, "")
        logger.info(f"{self.log_prefix}: %s", state.get('user_input', ''))
        try:
            if self.chain is None or not hasattr(self.chain, 'stream') or not callable(getattr(self.chain, 'stream', None)):
                logger.error(f"{self.log_prefix} self.chain이 None이거나 stream 메서드가 없습니다! 체인 할당을 확인하세요.")
                state['response'] = f"{self.log_prefix} 체인에 문제가 있습니다."
                return state
            state['response'] = stream_llm_chunks(self.chain.stream(invoke_args), writer)
            logger.info(f"{self.log_prefix} 응답 결과(plain text): {state['response']}")
        except Exception as e:
            logger.error(f"{self.log_prefix} 중 오류가 발생했습니다.: {e}")
            state['response'] = f"{self.log_prefix} 중 오류가 발생했습니다."
        return state

class BaseScheduleGenerator(BaseChainNode):
    def __call__(self, state, writer=None):
        if writer is None:
            writer = get_stream_writer()
        writer({"type": "schedule_start", "message": "⏳ 일정 생성 중입니다..."})
        slots_dict = state.get('slots', {})
        task_title = state.get('task_title', "")
        state['slots_json'] = json.dumps(slots_dict, ensure_ascii=False)
        self.extra_invoke_args = getattr(self, 'extra_invoke_args', [])
        invoke_args = {
            "history": "\n".join(state.get("history", [])),
            "user_input": state.get('user_input', ''),
            "date": state.get('date') or datetime.now().isoformat(),
            "slots": state['slots_json'],
        }
        for arg in self.extra_invoke_args:
            invoke_args[arg] = state.get(arg, "")
        logger.info(f"{self.log_prefix} - 병합된 슬롯 정보: {task_title}, {slots_dict}")
        if self.chain is None or not hasattr(self.chain, 'stream') or not callable(getattr(self.chain, 'stream', None)):
            logger.error(f"{self.log_prefix} self.chain이 None이거나 stream 메서드가 없습니다! 체인 할당을 확인하세요.")
            state['response'] = f"{self.log_prefix} 체인에 문제가 있습니다."
            return state
        try:
            buffer = ""
            json_pattern = re.compile(r'\{[\s\S]*?\}(?=\n|$)')
            stream_result = self.chain.stream(invoke_args)
            stream_result = cast(Iterable[Any], stream_result)
            try:
                if not isinstance(stream_result, Iterable):
                    logger.error(f"{self.log_prefix} stream이 반복 가능한 객체를 반환하지 않습니다.")
                    state['response'] = f"{self.log_prefix} stream이 반복 가능한 객체를 반환하지 않습니다."
                    return state
                for chunk in stream_result:
                    # chunk에서 content만 추출해서 buffer에 누적
                    content = extract_content(chunk)
                    buffer = str(buffer)
                    if content is not None:
                        buffer = str(buffer) + str(content)
                    else:
                        buffer = str(buffer) + str(chunk)
                    # logger.info(f"BUFFER 상태: {repr(buffer)}")
                    matches = list(json_pattern.finditer(buffer))
                    if matches:
                        for match in matches:
                            json_str = match.group()
                            # logger.info(f"정규식 매칭된 JSON: {json_str}")
                            try:
                                subtask = json.loads(json_str)
                                # logger.info(f"writer로 전송 준비: {subtask}")
                                # subtask에 task_title이 있으면 우선 사용
                                subtask_title = subtask.get("task_title") if isinstance(subtask, dict) else None
                                if writer:
                                    logger.info(f"subtask를 전송: {subtask}")
                                    writer({
                                        "type": "subtask",
                                        "message": subtask,
                                        "task_title": subtask_title or task_title,
                                        "category": slots_dict.get("category", "")
                                    })
                                else:
                                    logger.warning(f"writer가 None입니다. subtask를 전송하지 못함: {subtask}")
                            except Exception as e:
                                logger.warning(f"파싱 실패: {json_str} ({e})")
                        buffer = str(buffer[matches[-1].end():])
                        # logger.info(f"파싱 후 buffer 상태: {repr(buffer)}")
            except TypeError as e:
                logger.error(f"{self.log_prefix} stream이 반복 가능한 객체를 반환하지 않습니다: {e}")
                state['response'] = f"{self.log_prefix} stream이 반복 가능한 객체를 반환하지 않습니다."
                return state
            state['response'] = ""
            state["slots"] = {}
            logger.info(f"{self.log_prefix} 완료 후 슬롯을 초기화했습니다.")
            # 모든 subtask 스트리밍이 끝난 후 subtask_end 신호 전송
            if writer:
                writer({"type": "subtask_end"})
        except Exception as e:
            logger.error(f"{self.log_prefix} 중 오류가 발생했습니다.: {e}")
            state['response'] = f"{self.log_prefix} 중 오류가 발생했습니다."
        return state

class ExerciseScheduleGenerator(BaseScheduleGenerator):
    chain = exercise_chain()
    log_prefix = "운동 일정 생성"
    extra_invoke_args = ["search_results"]

class LearningScheduleGenerator(BaseScheduleGenerator):
    chain = learning_chain()
    log_prefix = "학습 일정 생성"
    extra_invoke_args = ["task_title"]

class ProjectScheduleGenerator(BaseScheduleGenerator):
    chain = project_chain()
    log_prefix = "프로젝트 일정 생성"
    extra_invoke_args = []

class PlannerGenerator(BaseScheduleGenerator):
    chain = planner_chain()
    log_prefix = "반복/개인 일정 생성"
    extra_invoke_args = []

class OtherGenerator(BaseScheduleGenerator):
    chain = other_chain()
    log_prefix = "기타 일정 생성"
    extra_invoke_args = []

class ScheduleAsk(BaseNode):
    def __init__(self):
        self.chain = schedule_ask_chain()

    def __call__(self, state: ConversationState, writer=None) -> ConversationState:
        history = "\n".join(state.get("history", []))
        try:
            # logger.info(f"[ScheduleAsk] LLM stream 시작: history={history}, user_input={state['user_input']}, date={state.get('date')}")
            def debug_writer(chunk):
            #     logger.info(f"[ScheduleAsk] writer 호출: {chunk}")
                if writer:
                    writer(chunk)
            state['response'] = stream_llm_chunks(self.chain.stream({
                "history": history,
                "user_input": state['user_input'],
                "date": state['date'] or datetime.now().isoformat()
            }), debug_writer)
            logger.info(f"[ScheduleAsk] 응답 결과: {state['response']}")
            state['ask'] = True
            state['next_node'] = None
        except Exception as e:
            logger.error("[ScheduleAsk] 기타 유형에 대한 재질문 중 오류가 발생했습니다: %s", e)
            state['response'] = "기타 유형에 대한 재질문 중 오류가 발생했습니다."
        return state

class QaGenerator(BaseNode):
    log_prefix = "일반 질의"

    def __call__(self, state, writer=None):
        history = "\n".join(state.get("history", []))
        chain = qa_chain()
        state['response'] = stream_llm_chunks(chain.stream({
            "history": history,
            "user_input": state.get('user_input', ''),
            "date": state.get('date') or datetime.now().isoformat(),
        }), writer)
        logger.info(f"{self.log_prefix} 응답 결과: {state['response']}")
        return state

# 일정 조회 쿼리 생성
class CalendarQueryGenerationNode:
    def __init__(self):
        self.chain = calendar_query_generation_chain()

    def __call__(self, state):
        result = self.chain.invoke({
            "history": state.get("history", ""),
            "user_input": state.get("user_input", ""),
            "date": state.get("date", "")
        })
        if isinstance(result, dict) and "start_time" in result and "start" not in result:
            result["start"] = result.pop("start_time")
        # Only add user_id to the final returned result
        if isinstance(result, dict):
            result = {**result, "user_id": state.get("user_id", "unknown")}
        return result

# 일정 조회 요약
class CalendarQuerySummaryNode:
    def __init__(self):
        self.chain = calendar_query_summary_chain()

    def __call__(self, state, writer=None):
        result = stream_llm_chunks(self.chain.stream({
            "calendar_results": state.get("calendar_results", ""),
            "user_input": state.get("user_input", ""),
            "date": state.get("date", "")
        }), writer)
        return result

class CalendarQueryNode(BaseNode):
    async def __call__(self, state):
        from services.conversation import conversation_service  
        try:
            query_json = CalendarQueryGenerationNode().__call__(state)
            # logger.info(f"[CalendarQueryNode] 쿼리 생성 결과: {query_json}")
            calendar_result = await conversation_service.fetch_schedules(
                state.get("user_id", "unknown"),
                query_json.get("start", ""),
                query_json.get("end", ""),
                query_json.get("task_title_keyword", ""),
                query_json.get("category", "")
            )
            logger.info(f"[CalendarQueryNode] DB 응답 결과: {calendar_result}")

            summary = CalendarQuerySummaryNode().__call__({
                "calendar_results": calendar_result,
                "user_input": state.get("user_input", ""),
                "date": state.get("date", "")
            })
            logger.info(f"[CalendarQueryNode] 요약 결과: {summary}")
            response = summary
        except Exception as e:
            logger.error(f"[CalendarQueryNode] 일정 조회 중 오류: {e}")
            response = "일정 조회 중 오류가 발생했습니다."
        # 새로운 state dict 반환
        new_state = dict(state)
        new_state["user_id"] = state.get("user_id", "unknown")
        new_state["has_fetched_schedule"] = True
        new_state["response"] = response
        return new_state