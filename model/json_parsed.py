from langchain.output_parsers import StructuredOutputParser, ResponseSchema

# ────────────────────────────────────────────────────────
# JSON Output Parser 설정
# ────────────────────────────────────────────────────────

# intent, slots parser
slot_schemas = [
    ResponseSchema(name="task_title", description="요청된 메인 테스크"),
    ResponseSchema(name="intent", description="schedule 또는 general"),
    ResponseSchema(name="slots", description="추출된 슬롯 객체")
]
slot_parser = StructuredOutputParser.from_response_schemas(slot_schemas)
slot_format_instructions = slot_parser.get_format_instructions()

# schedule parser
planner_schemas = [
    ResponseSchema(
        name="task_title", 
        description="메인 태스크 제목"
        ),
    ResponseSchema(
        name="detail",
        description=(
            "세부 일정 리스트. 각 항목은 'subtask', 'start_time', 'end_time'을 포함하는 객체로 구성"
            "시간 형식은 ISO 8601 (예: 2025-04-21T14:12:00)"
        )
    )
]
planner_parser = StructuredOutputParser.from_response_schemas(planner_schemas)
planner_format_instructions = planner_parser.get_format_instructions()

# 일반 응답 parser
generate_schemas = [
    ResponseSchema(name="response", description="AI 응답 결과")
]
generate_parser = StructuredOutputParser.from_response_schemas(generate_schemas)
generate_format_instructions = generate_parser.get_format_instructions()
