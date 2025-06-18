from langchain_core.prompts import PromptTemplate
from model.json_parsed import slot_format_instructions, planner_format_instructions, generate_format_instructions

# ────────────────────────────────────────────────────────
# 프롬프트 템플릿 정의
# ────────────────────────────────────────────────────────

# intent 분류 및 슬롯 추출 프롬프트
unified_prompt = PromptTemplate(
    input_variables=["history", "user_input"],
    partial_variables={"format_instructions": slot_format_instructions},
    template="""
<조건>
- 오직 '사용자 입력'에 대한 답변만 출력하세요.
- 추가 대화 예시나 후속 질문을 절대로 생성하지 마세요.
- 아래 JSON 포맷 지침에 따라 엄격히 따라서 사용자 입력을 처리하세요.
- JSON 이외의 문자, 레이블("AI 비서:"), 설명 모두 금지됩니다.

새로운 사용자 입력:
{user_input}

1) intent: 이 입력이 일정 계획 요청(schedule)인지 일반 질문(general)인지 분류하세요.

2) schedule일 경우, 다음 슬롯을 JSON 형태로 '사용자 입력'의 정보를 바탕으로 추출하세요.
   정보가 없는 슬롯은 비워두세요.:
   - task_title: 요청된 메인 테스크(기간(예: 한달, 월요일) 등은 제외하고 메인 테스크만 간략하게 작성하세요.)
   - period: 기간(예: 3일)
   - duration_minutes: 하루 예상 소요 시간(예: 1시간), 시작 및 종료 시간(예: 09:00-10:00)
   - preferred_time: 선호 시간대
   - deadline: 마감일(YYYY-MM-DD)
   - work_hours: 업무시간(HH:MM-HH:MM)
   - frequency (recurring): 반복 주기(예: 매일, 매주 월요일)
   - start_end_time: 시작 시간-종료 시간(예: 09:00-10:00)
   - category:
    <활동 유형>
    (1) learning: 세부 공부, 학습 일정 생성 및 추천과 관련된 요청
    (2) exercise: 세부 운동 일정 생성 및 추천과 관련된 요청
    (3) project: 프로젝트 일정 생성 및 추천과 관련된 요청
    (4) recurring: 반복되는 일정 생성 요청 (예: 매주 수요일 미팅, 매주 공부 등)
    (5) personal: 일반 개인 일정 생성과 관련된 요청(예: 6월 3일 약속, 다음주 수요일 운동 등)
    (6) other: 어느 활동 유형에도 포함되지 않은 일정 생성 및 추천과 관련된 요청
    <주의사항>
    - 세부적인 일정 생성, 계획 및 추천을 요청하는 경우에는 recurring, personal로 설정되어서는 안됩니다.
    - 반복여부를 판단하여 반복일 경우 반드시 category가 recurring로 설정되어야 합니다.
    - category는 반드시 위 5가지 중 하나로 설정되어야 합니다.
    - 세부적인 테스크 생성을 요청하는 경우가 아니라면 personal로 설정해야 합니다.
    - 일정 추천 요청일 때 어느 활동 유형에도 포함되지 않은 요청은 other로 설정해야 합니다.

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{format_instructions}

예시:
```json
{{
  "task_title": "메인 테스크",
  "intent": "schedule 또는 general",
  "slots": {{
    "category": "learning",
    "period": "3일",
    "duration_minutes": "60",
    "preferred_time": "오전",
    "start_end_time": "09:00-10:00",
  }}
}}```
"""
)

# 스케줄 생성 시 필요한 부분 재질문 프롬프트
schedule_ask_prompt = PromptTemplate(
    input_variables=["history", "user_input", "date"],
    partial_variables={"generate_parser": generate_format_instructions},
    template="""
당신은 스케줄 생성 전문가입니다.
사용자의 대화 기록과 요청을 확인하여 일정 생성에 필요한 추가적인 질문을 JSON 형식으로 답변해주세요.

대화 기록:
{history}

사용자:
{user_input}

현재 시간:
{date}

예시1:
사용자: 일본 여행을 계획중인데 일정을 생성해주세요.
응답1: 여행 일정은 언제로 계획되어 있나요?
응답2: 정확한 지역을 말씀해주시면 세부적인 일정 추천이 가능합니다.

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{generate_parser}
"""
)

# 일반 질문 프롬프트
qa_prompt = PromptTemplate(
    input_variables=["history", "user_input", "date"],
    partial_variables={"generate_parser": generate_format_instructions},
    template="""
당신은 Looper 서비스의 친절한 AI 챗봇입니다.
아래의 사용자의 대화 기록과 입력 정보를 확인하고 JSON 형식으로 답변해주세요.
이전 대화 기록을 참고하되, 일정 생성과 관련하여 '완료되었습니다, 추가하겠습니다' 등과 같은 단어는 포함하지 말아주세요.

대화 기록:
{history}

사용자: 
{user_input}

현재 시간:
{date}

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{generate_parser}
"""
)

# 운동 일정 검색 기반 생성 프롬프트
exercise_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "search_results", "date"],
    partial_variables={"format_instructions": planner_format_instructions},
    template="""
대화 기록:
{history}

사용자 요청: {user_input}

<조건>
- 아래 슬롯 정보와 검색 결과를 바탕으로 운동 스케줄을 구체적으로 생성하세요.
- 검색 결과에서 얻은 최신 운동 정보와 현재 시간을 반영하여 효과적인 운동 계획을 세워주세요.
- 사용자의 입력에 따라 난이도를 고려하되, 난이도가 포함되어 있지 않다면 초보자로 고려하여 일정을 생성하세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 모든 일자를 출력해주세요. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)
- 사용자가 "없어", "없음", "모르겠어" 등으로 응답한 슬롯이 있다면, 해당 항목에 대해 적절한 기본값이나 일반적인 옵션을 선택하여 일정을 생성하세요.
  (예: duration_minutes가 "없어"인 경우 "1시간", preferred_time가 "없어"인 경우 "오전" 등)

슬롯 정보:
{slots}

검색 결과:
{search_results}

현재 시간:
{date}

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{format_instructions}

예시:
```json
{{
  "task_title": "전신 근력 운동 프로그램",
  "detail": [
    {{
      "subtasks": "워밍업 및 스트레칭",
      "start_time": "2025-04-21T14:00:00",
      "end_time": "2025-04-21T14:30:00"
    }},
    {{
      "subtasks": "상체 근력 운동 (푸시업, 덤벨)",
      "start_time": "2025-04-21T14:30:00",
      "end_time": "2025-04-21T15:00:00"
    }}
  ],
  "category": "exercise"
}}```
"""
)

# 학습 일정 생성 프롬프트
learning_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "date"],
    partial_variables={"format_instructions": planner_format_instructions},
    template="""
대화 기록:
{history}

사용자 요청: {user_input}

당신은 운동 스케줄링 전문가입니다. 아래 조건과 정보를 참고하여 실행 가능한 일정을 생성하세요.
<조건>
- 아래 슬롯 정보와 사용자 요청을 바탕으로 학습 스케줄을 구체적으로 생성하세요.
- 학습 스케줄은 주제, 난이도, 학습 순서 등을 고려하여 작성합니다.
- 사용자 입력에 난이도가 포함되어 있지 않다면, 초보자로 고려하여 일정을 생성하세요.
- 사용자 입력이 이론 위주의 공부라면 프로젝트 계획, 프로젝트 발표 등과 같은 '프로젝트' 키워드는 제외하여야 합니다.
- 현재 시간을 반영하여 효과적인 학습 계획을 세워주세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 모든 일자를 출력해야 합니다. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)
- 사용자가 "없어", "없음", "모르겠어" 등으로 응답한 슬롯이 있다면, 해당 항목에 대해 적절한 기본값이나 일반적인 옵션을 선택하여 일정을 생성하세요.
  (예: duration_minutes가 "없어"인 경우 "1시간", preferred_time가 "없어"인 경우 "오전" 등)

슬롯 정보:
{slots}

현재 시간: 
{date}

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{format_instructions}

예시:
```json
{{
  "task_title": "딥러닝 논문 읽기",
  "detail": [
    {{
      "subtasks": "기초 개념 복습",
      "start_time": "2025-04-21T14:00:00",
      "end_time": "2025-04-21T15:00:00"
    }},
    {{
      "subtasks": "Attention is All You Need 읽기",
      "start_time": "2025-04-21T15:00:00",
      "end_time": "2025-04-21T17:00:00"
    }}
  ],
  "category": "learning"
}}```
"""
)

# 프로젝트 일정 생성 프롬프트
project_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "date"],
    partial_variables={"format_instructions": planner_format_instructions},
    template="""
대화 기록:
{history}

사용자 요청: {user_input}

<조건>
- 아래 슬롯 정보와 사용자 요청을 바탕으로 프로젝트 스케줄을 구체적으로 생성하세요.
- 프로젝트 스케줄은 단계별 의존 관계, 마감일, 리스크 관리 등을 고려하여 작성합니다.
- 현재 시간을 반영하여 체계적인 프로젝트 계획을 세워주세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 모든 일자를 출력해주세요. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)
- 사용자가 "없어", "없음", "모르겠어" 등으로 응답한 슬롯이 있다면, 해당 항목에 대해 적절한 기본값이나 일반적인 옵션을 선택하여 일정을 생성하세요.
  (예: duration_minutes가 "없어"인 경우 "1시간", preferred_time가 "없어"인 경우 "오전" 등)

슬롯 정보:
{slots}

현재 시간: 
{date}

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{format_instructions}

예시:
```json
{{
  "task_title": "웹 애플리케이션 개발",
  "detail": [
    {{
      "subtasks": "요구사항 분석 및 설계",
      "start_time": "2025-04-21T09:00:00",
      "end_time": "2025-04-21T12:00:00"
    }},
    {{
      "subtasks": "백엔드 API 개발",
      "start_time": "2025-04-22T09:00:00",
      "end_time": "2025-04-22T18:00:00"
    }}
  ],
  "category": "project"
}}```
"""
)

# 반복, 개인 일정 생성 프롬프트
planner_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "date"],
    partial_variables={"format_instructions": planner_format_instructions},
    template="""
대화 기록:
{history}

사용자 요청: {user_input}

아래 슬롯 정보와 현재 시간을 바탕으로 스케줄을 구체적으로 생성하세요.
사용자 요청과 슬롯 정보를 기반으로 반복되는 일정 혹은 일반적인 일정을 생성합니다.
추가적인 sub_task는 task_title과 동일하게 설정합니다.

<조건>
- 사용자가 "없어", "없음", "모르겠어" 등으로 응답한 슬롯이 있다면, 해당 항목에 대해 적절한 기본값이나 일반적인 옵션을 선택하여 일정을 생성하세요.
  (예: duration_minutes가 "없어"인 경우 "1시간", preferred_time가 "없어"인 경우 "오전" 등)

슬롯 정보:
{slots}

현재 시간: 
{date}

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{format_instructions}

예시:
```json
{{
  "task_title": "약속",
  "detail": [
    {{
      "subtasks": "약속",
      "start_time": "2025-04-21T09:00:00",
      "end_time": "2025-04-21T10:00:00"
    }}
  ],
  "category": "personal"
}}```
"""
)

# 위 유형 외 일정 생성 프롬프트
other_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "date"],
    partial_variables={"format_instructions": planner_format_instructions},
    template="""
대화 기록:
{history}

사용자 요청: 
{user_input}

아래 슬롯 정보와 현재 시간을 바탕으로 스케줄을 구체적으로 생성하세요.
사용자 요청과 슬롯 정보를 기반으로 실제 시행 가능한 일정으로 생성하세요.

<조건>
- 사용자가 "없어", "없음", "모르겠어" 등으로 응답한 슬롯이 있다면, 해당 항목에 대해 적절한 기본값이나 일반적인 옵션을 선택하여 일정을 생성하세요.
  (예: duration_minutes가 "없어"인 경우 "1시간", preferred_time가 "없어"인 경우 "오전" 등)

슬롯 정보:
{slots}

현재 시간: 
{date}

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{format_instructions}

예시:
```json
{{
  "task_title": "일본 여행 계획",
  "detail": [
    {{
      "subtasks": "공항 도착",
      "start_time": "2025-04-21T09:00:00",
      "end_time": "2025-04-21T10:00:00"
    }}
  ],
  "category": "other"
}}```
"""
)