from langchain.output_parsers import StructuredOutputParser
from model.json_parsed import slot_parser, planner_parser, generate_parser
from model.prompt_template import qa_prompt, exercise_prompt, unified_prompt, learning_prompt, planner_prompt, project_prompt
from model.chat_llm import llm

# ────────────────────────────────────────────────────────
# 챗봇 응답 체인 정의
# ────────────────────────────────────────────────────────

def unified_slot_chain() -> StructuredOutputParser:
    return  unified_prompt | llm | slot_parser

def qa_chain() -> StructuredOutputParser:
    return  qa_prompt | llm | generate_parser

def exercise_chain() -> StructuredOutputParser:
    return  exercise_prompt | llm | planner_parser

def learning_chain() -> StructuredOutputParser:
    return  learning_prompt | llm | planner_parser

def project_chain() -> StructuredOutputParser:
    return  project_prompt | llm | planner_parser

def planner_chain() -> StructuredOutputParser:
    return  planner_prompt | llm | planner_parser