from langgraph.graph import StateGraph, END
from core.state import ConversationState
from core.chat_node import DetectedIntent, MissingSlotAsker, ExerciseSearchInfo, ExerciseScheduleGenerator, LearningScheduleGenerator, ProjectScheduleGenerator, QaGenerator, PlannerGenerator, SlotUpdater, OtherGenerator, ScheduleAsk
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

        self.graph_builder.add_conditional_edges(
            "ask_missing_slot",
            lambda state: (
                "general_qa" if state.get("intent") == "general" or state.get("conversation_context") == "general_query"
                else "need_input" if state.get('ask', False)
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
                "generate_schedule": "generate_schedule", 
                "general_qa": "general_qa",
                "schedule_ask": "schedule_ask",
            }
        )

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

        self.graph_builder.add_conditional_edges(
            "update_slot",
            lambda state: (
                "general_qa" if state.get("intent") == "general" or state.get("conversation_context") == "general_query"
                else "generate_other_schedule" if state.get("conversation_context") == "other_response_received"
                else "ask_missing_slot"
            ),
            {
                "general_qa": "general_qa",
                "generate_other_schedule": "generate_other_schedule",
                "ask_missing_slot": "ask_missing_slot",
            }
        )

    def add_edge(self):
        self.graph_builder.add_edge("search_exercise_info", "generate_exercise_schedule")
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



