from langchain_core.prompts import PromptTemplate
from model.json_parsed import slot_format_instructions, planner_format_instructions, generate_format_instructions

# ────────────────────────────────────────────────────────
# 프롬프트 템플릿 정의
# ────────────────────────────────────────────────────────

# intent만 추출
intent_prompt = PromptTemplate(
    input_variables=["history", "user_input"],
    partial_variables={"generate_parser": generate_format_instructions},
    template="""
대화 기록:
{history}

새로운 사용자 입력:
{user_input}

intent: 사용자 입력이 일정 계획 요청(schedule)인지 일반 질문(general)인지 분류하세요.

<중요한 분류 기준>
1) 반드시 **대화 기록**을 먼저 확인하고, 문맥에 맞게 intent를 분류하세요.
2) 인사말, 감사, 일반적인 질문 등은 intent를 general로 분류하세요.
3) 일정 생성 요청일 경우 schedule로 분류하세요.
  - 사용자의 대화 기록을 참고하여 '응', '일정 생성해줘', 'ㅇ', '어', '그래' 와 같은 동의의 응답일 때에는 schedule로 분류하세요.

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{generate_parser}

예시:
'''json
{{"response": "schedule"}}
'''
"""
)

# slot/category 추출 
slot_category_prompt = PromptTemplate(
    input_variables=["history", "user_input", "task_title"],
    partial_variables={"format_instructions": slot_format_instructions},
    template="""
아래 대화 기록과 사용자 입력, 그리고 기존 task_title 정보를 참고하여 slot과 category를 추출하세요.

대화 기록:
{history}
사용자 입력:
{user_input}
기존 task_title:
{task_title}

<중요한 분류 기준>
1) 반드시 대화 기록과 기존 task_title을 먼저 확인하세요.
2) 기존 task_title이 있으면 변경하지 말고 그대로 유지하세요. 새로운 일정 요청이 아닌 경우 기존 task_title을 그대로 사용하세요.
3) 사용자의 답변에 해당하는 슬롯 정보만 추가/업데이트하세요.
4) 만약 사용자의 입력이 완전히 새로운 일정 요청(예: "운동 일정을 만들어줘", "새로운 프로젝트 계획을 세워줘" 등)이라면, 새로운 task_title, category를 생성하세요.

<추천 요청 분류 기준>
다음과 같은 사용자 응답은 해당 슬롯을 "recommend"로 분류하세요:
- "없음", "모르겠음", "선택해줘", "정해줘", "추천해줘", "추천", "적당한", "적절한", "괜찮은", "좋은", "상관없어", "아무거나", "기본", "일반적인", "평균적인", "선택하기 어려워", "고민이야"

<주의사항>
- 사용자가 명확한 시간을 제시한 경우(예: "오후 6-7시", "아침 9시", "2시간" 등)는 recommend로 분류하지 마세요.
- 시간 관련 표현: "시", "시간", "분", "오전", "오후", "저녁", "아침" 등이 포함된 경우 해당 슬롯에 실제 값을 설정하세요.
- 기간 관련 표현: "일주일", "3일", "한달" 등이 포함된 경우 해당 슬롯에 실제 값을 설정하세요.
- 사용자가 처음 일정을 요청할 때 구체적인 정보를 포함한 경우(예: "일주일간 공부할거야", "아침에 운동하고 싶어")는 해당 정보를 슬롯에 설정하고, 나머지만 recommend로 분류하세요.
- "계획 세워줘", "일정 만들어줘" 등의 표현은 recommend 요청이 아니라 일정 생성 요청입니다.

<슬롯 구분 중요사항>
- preferred_time: 선호하는 시간대 (예: "오전 9시-11시", "오후 2-4시", "저녁 7-9시") : 시작, 종료 시간과 같아도 무관합니다.
- start_end_time: 실제 시작-종료 시간 (예: "09:00-11:00", "14:00-16:00")
- duration_minutes, work_hours: 하루 예상 소요 시간 (예: "2시간", "30분", "1시간 30분", "7-9시")
- period, deadline: 시행하는 기간 혹은 마감기한 (예: 일주일, 2025-10-30까지)

<추천 정보 인식 규칙>
- AI가 추천한 정보가 대화 기록에 있으면, 해당 정보를 적절한 슬롯에 설정하세요.
- "오전 9시-11시, 총 2시간"과 같은 추천이 있다면:
  * preferred_time, work_hours: "오전 9시-11시"
  * duration_minutes: "2시간"
- 추천된 정보는 start_end_time이 아닌 preferred_time에 설정하세요.

1) 다음 슬롯을 추출하세요.
  <슬롯 추출 시 주의사항>
    - 슬롯과 관련된 직전 질문을 확인하여 새로운 슬롯 정보만 추가하고, 정보가 없는 슬롯은 비워두세요.
    - 슬롯 유형을 참고하여 중복으로 추출할 수 있는 슬롯은 모두 추출하세요.
    - 사용자의 대화 기록을 참고하여 문맥에 따라 새로운 일정을 요청할 때에만 정보가 없는 슬롯은 비워둔 후, 슬롯에 관련한 질문에 대한 응답이라면 recommned로 추출하세요.
    - '모두', '다' 등과 같이 모든 일정에 대한 추천을 원하는 응답이라면 비어 있는 슬롯을 모두 recommend로 추출하세요.
    - 사용자의 대화 기록을 참고하여 '응', '일정 생성해줘', 'ㅇ', '어' 와 같은 동의의 응답일 때에는 추천된 일정에 따라 슬롯을 추출하세요.
    - AI가 추천한 시간 정보는 preferred_time에 설정하고, start_end_time은 비워두세요.
    - 프로젝트(category: project) 일정 생성 시 work_hours와 deadline은 반드시 추출해야 합니다.
  <슬롯 유형>   
   - task_title: 요청된 메인 테스크(기간(예: 한달, 월요일) 등은 제외하고 메인 테스크만 간략하게 작성하세요.)
   - period: 기간(예: 3일, 일주일, 한달 등)
   - duration_minutes: 하루 소요 시간(예: 1시간), 시작 및 종료 시간을 참고해서 추출해도 무방합니다.
   - preferred_time: 선호 시간대(예: 오전 9시-11시, 오후 2-4시)
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
    (5) personal: 단일적인 일반 개인 일정 생성과 관련된 요청(예: 6월 3일 약속, 다음주 수요일 운동 등)
    (6) other: 어느 활동 유형에도 포함되지 않은 일정 계획 생성 및 추천과 관련된 요청(예: 여행 일정 추천, 기타 다른 일정 추천)
    <활동 유형 추출 시 주의사항>
    - 세부적인 일정 생성, 계획 및 추천을 요청하는 경우에는 recurring, personal로 설정되어서는 안됩니다.
    - 반복여부를 판단하여 반복일 경우 반드시 category가 recurring로 설정되어야 합니다.
    - category는 반드시 위 5가지 중 하나로 설정되어야 합니다.
    - 세부적인 테스크 생성을 요청하는 경우가 아니라면 personal로 설정해야 합니다.
    - 일정 추천 요청일 때 어느 활동 유형에도 포함되지 않은 요청은 other로 설정해야 합니다.

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{format_instructions}

구체적인 예시 1:
사용자 대화 기록: "오늘부터 일주일간 챗봇 구현 방법에 대해 오후 6-7시까지 공부할거야. 계획 세워줘"
응답:
```json
{{
  "task_title": "챗봇 구현 방법 공부",
  "intent": "schedule",
  "slots": {{
    "category": "learning",
    "period": "일주일",
    "duration_minutes": "",
    "preferred_time": ""  
    }}
}}```
응답 : 선호하는 시간대가 언제인가요?
사용자 : 다 추천해줘
```json
{{
  "task_title": "챗봇 구현 방법 공부",
  "intent": "schedule",
  "slots": {{
    "category": "learning",
    "period": "일주일",
    "duration_minutes": "recommend",
    "preferred_time": "recommend"
  }}
}}```

구체적인 예시 2:
사용자: "아침에 6-7시까지 운동하고 싶어"
응답:
```json
{{
  "task_title": "운동",
  "intent": "schedule",
  "slots": {{
    "category": "exercise",
    "duration_minutes": "6-7시",
    "preferred_time": "아침",
    "period": ""
  }}
}}```
"""
)

# 스케줄 생성 시 추가 정보 재질문 프롬프트
schedule_ask_prompt = PromptTemplate(
    input_variables=["history", "user_input", "date"],
    partial_variables={"generate_parser": generate_format_instructions},
    template="""
당신은 스케줄 생성 전문가입니다.
사용자의 대화 기록과 요청을 확인하여 일정 생성에 필요한 추가적인 질문을 JSON 형식으로 답변해주세요.
사용자에게 친근하고 자연스로운 말투로 이모지를 사용하여 답변하세요.

대화 기록:
{history}

사용자 요청:
{user_input}

현재 시간:
{date}

예시1:
사용자: 일본 여행을 계획중인데 일정을 생성해주세요.
응답1: 여행 일정은 언제로 계획되어 있나요? ✈️
응답2: 정확한 지역을 말씀해주시면 세부적인 일정 추천이 가능합니다.

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{generate_parser}
"""
)

# 슬롯 추천 프롬프트
slot_recommendation_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "category", "date"],
    partial_variables={"generate_parser": generate_format_instructions},
    template="""
당신은 스케줄 생성 전문가입니다.
현재 수집된 정보를 바탕으로 적절한 슬롯 값을 추천해주세요.

대화 기록:
{history}

사용자 입력:
{user_input}

현재 수집된 슬롯 정보:
{slots}

활동 카테고리:
{category}

현재 시간:
{date}

<추천 규칙>
1. 현재 비어있거나 recommend로 추출된 슬롯에 대해서 추천하세요.

2. 슬롯 종류
- period: 기간(예: 3일, 일주일, 한달 등)
- duration_minutes: 하루 예상 소요 시간(예: 1시간), 시작 및 종료 시간(예: 09:00-10:00)
- preferred_time: 선호 시간대
- deadline: 마감일(YYYY-MM-DD)
- work_hours: 업무시간(HH:MM-HH:MM)
- frequency (recurring): 반복 주기(예: 매일, 매주 월요일)
- start_end_time: 시작 시간-종료 시간(예: 09:00-10:00)

3. 추천 기준
- 사용자의 task_title, category를 확인하여 평균적인 기준으로 추천해주세요.
- 난이도가 없을 경우 사용자를 초보자로 고려하여 목표를 달성할 수 있도록 기간, 시간 등을 추천해야 합니다.
- period의 경우 최소 하루, 최대 한달까지만 추천하세요.
- duration_minutes의 경우 최소 한시간, 최대 세시간까지만 추천하세요.
- preferred_time의 경우 오전 7시부터 오후 10사이로 추천하고, 점심시간(오후 12-1시), 저녁시간(오후 6-7시)는 제외하고 추천하세요.

4. 추천 응답과 이유에 대해 한 문장으로 간단히 설명해주세요.
- 사용자에게 친근하고 자연스러운 톤으로 이모지를 사용하여 추천 메시지를 작성해주세요.
- 예시: "일주일동안 하루에 1시간을 할애하는 것을 추천드려요! 이는 일주일 동안 충분한 학습 시간을 확보할 수 있는 적절한 시간입니다 🔥"

아래 JSON 형식으로 응답하세요:
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
친근한 말투와 적절한 이모지를 사용하여 답변해주세요.

대화 기록:
{history}

사용자: 
{user_input}

현재 시간:
{date}

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{generate_parser}

예시: 안녕하세요! Looper 챗봇입니다. 도움이 필요하시면 언제든지 말씀해주세요 ✨
"""
)

# 운동 일정 검색 기반 생성 프롬프트
exercise_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "search_results", "date"],
    template="""
대화 기록:
{history}

사용자 요청: {user_input}

<조건>
- 아래 슬롯 정보와 검색 결과를 바탕으로 운동 스케줄을 구체적으로 생성하세요.
- 검색 결과에서 얻은 최신 운동 정보와 현재 시간을 반영하여 효과적인 운동 계획을 세워주세요.
- 사용자의 입력에 따라 난이도를 고려하되, 난이도가 포함되어 있지 않다면 초보자로 고려하여 일정을 생성하세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 **모든 일자**를 출력해야 합니다. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)

슬롯 정보:
{slots}

검색 결과:
{search_results}

현재 시간:
{date}

아래와 같이 각 subtask를 한 줄 JSON으로, 각 줄마다 출력하세요:
전체를 리스트로 감싸지 마세요. 

예시:
{{"subtasks": "워밍업 및 스트레칭", "start_time": "2025-04-21T14:00:00", "end_time": "2025-04-21T14:30:00"}}
{{"subtasks": "상체 근력 운동 (푸시업, 덤벨)", "start_time": "2025-04-21T14:30:00", "end_time": "2025-04-21T15:00:00"}}
..."""
)

# 학습 일정 생성 프롬프트
learning_prompt = PromptTemplate(
    input_variables=["user_input", "slots", "date", "task_title"],
    template="""
사용자 요청: {user_input}

기존 task_title: {task_title}

당신은 운동 스케줄링 전문가입니다. 아래 조건과 정보를 참고하여 실행 가능한 일정을 생성하세요.
<조건>
- 아래 슬롯 정보, 기존 task_title, 사용자 요청을 바탕으로 학습 스케줄을 구체적으로 생성하세요.
- 학습 스케줄은 주제, 난이도, 학습 순서 등을 고려하여 작성합니다.
- 사용자 입력에 난이도가 포함되어 있지 않다면, 초보자로 고려하여 일정을 생성하세요.
- 사용자 입력이 이론 위주의 공부라면 프로젝트 계획, 프로젝트 발표 등과 같은 '프로젝트' 키워드는 제외하여야 합니다.
- 현재 시간을 반영하여 효과적인 학습 계획을 세워주세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 **모든 일자**를 출력해야 합니다. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)

슬롯 정보:
{slots}

현재 시간: 
{date}
아래와 같이 각 subtask를 한 줄 JSON으로, 각 줄마다 출력하세요:
전체를 리스트로 감싸지 마세요. 

예시:
{{"subtasks": "기초 개념 복습", "start_time": "2025-04-21T14:00:00", "end_time": "2025-04-21T15:00:00"}}
{{"subtasks": "Attention is All You Need 읽기", "start_time": "2025-04-21T15:00:00", "end_time": "2025-04-21T17:00:00"}}
...
"""
)

# 프로젝트 일정 생성 프롬프트
project_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "date"],
    template="""
대화 기록:
{history}

사용자 요청: {user_input}

<조건>
- 아래 슬롯 정보와 사용자 요청을 바탕으로 프로젝트 스케줄을 구체적으로 생성하세요.
- 프로젝트 스케줄은 단계별 의존 관계, 마감일, 리스크 관리 등을 고려하여 작성합니다.
- 현재 시간을 반영하여 체계적인 프로젝트 계획을 세워주세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 **모든 일자**를 출력해야 합니다. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)

슬롯 정보:
{slots}

현재 시간: 
{date}

아래와 같이 각 subtask를 한 줄 JSON으로, 각 줄마다 출력하세요:
전체를 리스트로 감싸지 마세요. 

예시:
{{"subtasks": "요구사항 분석 및 설계", "start_time": "2025-04-21T09:00:00", "end_time": "2025-04-21T12:00:00"}}
{{"subtasks": "백엔드 API 개발", "start_time": "2025-04-22T09:00:00", "end_time": "2025-04-22T18:00:00"}}
..."""
)

# 반복, 개인 일정 생성 프롬프트
planner_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "date"],
    template="""
대화 기록:
{history}

사용자 요청: {user_input}

아래 슬롯 정보와 현재 시간을 바탕으로 스케줄을 구체적으로 생성하세요.
사용자 요청과 슬롯 정보를 기반으로 반복되는 일정 혹은 일반적인 일정을 생성합니다.
추가적인 sub_task는 task_title과 동일하게 설정합니다.

슬롯 정보:
{slots}

현재 시간: 
{date}

아래와 같이 각 subtask를 한 줄 JSON으로, 각 줄마다 출력하세요:
전체를 리스트로 감싸지 마세요. 

예시:
{{"subtasks": "약속", "start_time": "2025-04-21T09:00:00", "end_time": "2025-04-21T10:00:00"}}
..."""
)

# 위 유형 외 일정 생성 프롬프트
other_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "date"],
    template="""
대화 기록:
{history}

사용자 요청: 
{user_input}

아래 슬롯 정보와 현재 시간을 바탕으로 스케줄을 구체적으로 생성하세요.
사용자 요청과 슬롯 정보를 기반으로 실제 시행 가능한 일정으로 생성하세요.

슬롯 정보:
{slots}

현재 시간: 
{date}

아래와 같이 각 subtask를 한 줄 JSON으로, 각 줄마다 출력하세요:
전체를 리스트로 감싸지 마세요. 

예시:
{{"subtasks": "공항 도착", "start_time": "2025-04-21T09:00:00", "end_time": "2025-04-21T10:00:00"}}
..."""
)
