from langgraph.graph import StateGraph, END
from core.state import ConversationState
from core.chat_node import DetectedIntent, MissingSlotAsker, ExerciseSearchInfo, ExerciseScheduleGenerator, LearningScheduleGenerator, ProjectScheduleGenerator, QaGenerator, PlannerGenerator, SlotUpdater, OtherGenerator, ScheduleAsk
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 조건부 엣지 - intent에 따른 라우팅
def route_on_intent(state: ConversationState) -> str:
    """감지된 intent에 따라 라우팅"""
    if state.get('conversation_context') == 'awaiting_slot_input':
        logger.info("슬롯 대기 입력 상태")
        return "schedule"

    if state.get('intent') == 'schedule':
        return "schedule"
    else:
        return "general"  

# ────────────────────────────────────────────────────────
# 챗봇 그래프 빌더
# ────────────────────────────────────────────────────────

class ChatGraphBuilder:
    def __init__(self):
        self.graph_builder = StateGraph(ConversationState)

    def add_node(self):
        self.graph_builder.add_node("detect_intent_and_slots", DetectedIntent())
        self.graph_builder.add_node("update_slot", SlotUpdater())
        self.graph_builder.add_node("ask_missing_slot", MissingSlotAsker()) 
        self.graph_builder.add_node("search_exercise_info", ExerciseSearchInfo())
        # graph_builder.add_node("retrieve_docs", retrieve_docs)
        # 카테고리별 스케줄 생성 노드
        self.graph_builder.add_node("generate_exercise_schedule", ExerciseScheduleGenerator())
        self.graph_builder.add_node("generate_learning_schedule", LearningScheduleGenerator())
        self.graph_builder.add_node("generate_project_schedule", ProjectScheduleGenerator())
        self.graph_builder.add_node("generate_schedule", PlannerGenerator()) 
        self.graph_builder.add_node("general_qa", QaGenerator())
        self.graph_builder.add_node("generate_other_schedule", OtherGenerator())
        self.graph_builder.add_node("schedule_ask", ScheduleAsk())


    def set_entry_point(self):
        self.graph_builder.set_entry_point("detect_intent_and_slots")
        
    def add_conditional_edges(self):
        self.graph_builder.add_conditional_edges(
            "detect_intent_and_slots",
            lambda st: "update_slot" if st.get("awaiting_slot") or st.get("ask", False) else (
                "ask_missing_slot" if st.get("intent") == "schedule" else "general_qa"
            ),
            {
                "update_slot": "update_slot",
                "ask_missing_slot": "ask_missing_slot",
                "general_qa": "general_qa",
            }
        )

        # slot 확인 후 라우팅 설정
        self.graph_builder.add_conditional_edges(
            "ask_missing_slot",
            lambda state: (
                "need_input" if state.get('ask', False)
                else {
                    'exercise': 'search_exercise_info',
                    'learning': 'generate_learning_schedule',
                    'project': 'generate_project_schedule',
                    'recurring': 'generate_schedule',
                    'personal': 'generate_schedule',
                    'other': 'schedule_ask',
                }.get(state.get('slots', {}).get('category', ''), 'general_qa') 
            ),
            {
                "need_input": END,
                "search_exercise_info": "search_exercise_info",
                "generate_learning_schedule": "generate_learning_schedule",
                "generate_project_schedule": "generate_project_schedule",
                # "retrieve_docs": "retrieve_docs",
                "generate_schedule": "generate_schedule", 
                "general_qa": "general_qa",
                "schedule_ask": "schedule_ask",
            }
        )

        # schedule_ask 노드에서 사용자 응답 후 라우팅
        self.graph_builder.add_conditional_edges(
            "schedule_ask",
            lambda state: (
                "need_input" if state.get('ask', False)
                else "generate_other_schedule"
            ),
            {
                "need_input": END,
                "generate_other_schedule": "generate_other_schedule",
            }
        )

        # update_slot 노드에서 other 카테고리 응답 처리 후 라우팅
        self.graph_builder.add_conditional_edges(
            "update_slot",
            lambda state: (
                "generate_other_schedule" if state.get("conversation_context") == "other_response_received"
                else "ask_missing_slot"
            ),
            {
                "generate_other_schedule": "generate_other_schedule",
                "ask_missing_slot": "ask_missing_slot",
            }
        )

    def add_edge(self):
        # 검색 후 스케줄 생성으로 연결       
        self.graph_builder.add_edge("search_exercise_info", "generate_exercise_schedule")
        # 종료 엣지
        self.graph_builder.add_edge("generate_exercise_schedule", END)
        self.graph_builder.add_edge("generate_learning_schedule", END)
        self.graph_builder.add_edge("generate_project_schedule", END)
        self.graph_builder.add_edge("generate_schedule", END) 
        self.graph_builder.add_edge("general_qa", END)
        self.graph_builder.add_edge("generate_other_schedule", END)


    def compile(self):
        self.add_node()
        self.set_entry_point()
        self.add_conditional_edges()
        self.add_edge()
        return self.graph_builder.compile()
    
chat_graph = ChatGraphBuilder().compile()
    


