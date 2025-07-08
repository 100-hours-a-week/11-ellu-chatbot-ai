from langchain.output_parsers import StructuredOutputParser
from model.json_parsed import slot_parser, planner_parser, generate_parser
from model.prompt_template import qa_prompt, exercise_prompt, learning_prompt, planner_prompt, project_prompt, other_prompt, schedule_ask_prompt, slot_recommendation_prompt, intent_prompt, slot_category_prompt
from model.chat_llm import llm

# ────────────────────────────────────────────────────────
# 챗봇 응답 체인 정의
# ────────────────────────────────────────────────────────


def qa_chain():
    return qa_prompt | llm

def exercise_chain():
    return  exercise_prompt | llm 

def learning_chain():
    return  learning_prompt | llm 

def project_chain():
    return  project_prompt | llm 

def planner_chain():
    return  planner_prompt | llm 

def other_chain():
    return  other_prompt | llm

def schedule_ask_chain():
    return schedule_ask_prompt | llm 

def slot_recommendation_chain():
    return slot_recommendation_prompt | llm 

def intent_chain() -> StructuredOutputParser:
    return intent_prompt | llm | generate_parser

def slot_category_chain() -> StructuredOutputParser:
    return slot_category_prompt | llm | slot_parser