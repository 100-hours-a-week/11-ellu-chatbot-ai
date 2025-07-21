from langchain_core.prompts import PromptTemplate
from model.json_parsed import slot_format_instructions, generate_format_instructions, query_format_instructions

# ────────────────────────────────────────────────────────
# 프롬프트 템플릿 정의
# ────────────────────────────────────────────────────────

# intent만 추출
intent_prompt = PromptTemplate(
    input_variables=["history", "user_input"],
    partial_variables={"generate_parser": generate_format_instructions},
    template="""
- 대화 기록: {history}
- 사용자 입력: {user_input}

<intent 분류 기준>
1) 반드시 **대화 기록**을 먼저 확인하고, 문맥에 맞게 intent를 분류하세요.
  - confirm: 일정 생성에 동의하거나, 추천/자동/기존 정보로 바로 일정을 생성해달라는 의사(예: "응", "이대로 생성해줘", "네", "진행해줘", "좋아요", "ㅇㅋ", "바로 생성해줘" 등)
  - schedule: 일정을 생성하거나 계획, 추천에 관련된 요청일 때 
  - calendar: 일정 조회 요청(특정 테스크나 일자 등의 일정에 대해 묻는 경우일 때)
  - general: 일정 생성과 관련 없는 일반 질문

아래 JSON 형식을 **반드시** 지켜서 응답하세요.
{generate_parser}

예시:
'''json
{{"response": "confirm"}}
'''
예시:
대화 기록: ... (이전 질문/답변)
사용자 입력: \"이대로 생성해줘\"
응답: {{"response": "confirm"}}

사용자 입력: \"운동 일정 만들어줘\"
응답: {{"response": "schedule"}}
"""
)

# slot/category 추출 
slot_category_prompt = PromptTemplate(
    input_variables=["history", "user_input", "task_title"],
    partial_variables={"format_instructions": slot_format_instructions},
    template="""
아래 대화 기록과 사용자 입력, 그리고 기존 task_title 정보를 참고하여 slot과 category, type을 추출하세요.

- 대화 기록: {history}
- 사용자 입력: {user_input}
- 기존 task_title: {task_title}

<recommend, auto 분류 기준>
1. 다음과 같은 추천을 원하는 사용자 응답 또는 요청에는 하나의 슬롯이라도 **반드시** "recommend"로 분류해야 합니다.
- "추천해줘", "추천", "정해줘", "날짜 추천", "코스 추천", "적당히", "적절히", "알아서 추천", "선택해줘", "고민이야", "모르겠어" 등
2. 다음과 같은 사용자 응답은 해당 슬롯을 "auto"로 분류하세요. 슬롯 이외의 질문에 대하여 다음과 같이 응답한다면 비어있는 모든 슬롯에 auto로 분류하세요.
- "상관없음", "아무거나", "없음", "알아서" 등

<추천 정보 인식 규칙>
- AI가 추천한 정보가 대화 기록에 있으면, 해당 정보를 적절한 슬롯에 설정하세요.
- "오전 9시-11시, 총 2시간"과 같은 추천이 있다면:
  * preferred_time: "오전 9시-11시"
  * duration_minutes: "2시간"
- 추천된 정보는 start_end_time이 아닌 preferred_time에 설정하세요.

1. 다음 슬롯을 추출하세요.
  <슬롯 추출 시 주의사항>
    - 대화 기록과 사용자 입력을 확인하여 새로운 일정 생성의 요청이라면 이전의 기간, 시간 등의 슬롯 정보는 참고하지 마세요.
    - 슬롯과 관련된 직전 질문을 확인하여 새로운 슬롯 정보만 추가하고, 정보가 없는 슬롯은 비워두세요.
    - 슬롯 유형을 참고하여 중복으로 추출할 수 있는 슬롯은 모두 추출하세요.
      - 예시: "오전 9-10시" -> duration_minutes: 1시간, preferred_time: 오전 9-10시, start_end_time: 09:00-10:00

  <슬롯 유형>   
   - task_title: 요청된 메인 테스크(기간(예: 한달, 월요일) 등은 제외하고 메인 테스크만 간략하게 작성하세요.)
   - schedule_ask: 일정 생성에 필요한 정보가 불충분하여 재질문이 필요한 경우 True를 추출하세요.(특정 기간, 일자, 장소 등 일정을 생성하는 데 필요한 최소한의 정보도 없을 시)
   - recommend_ask: 사용자 입력을 확인하여 추천을 원하는 사용자 응답 또는 요청에는 True를 추출하세요.(예: 추천해줘, 추천, 정해줘, 알아서 추천, 고민이야 등)
      - "바로 생성", "그냥 계획해줘", "알아서 생성해줘", "캘린더에 바로 넣어줘", "추천해서 캘린더에 추가해줘" 등과 같이 바로 캘린더/달력에 생성을 원하는 입력일 경우 schedule_ask와 recommend_ask 모두 False를 추출하세요.
   - period: 기간(예: 3일, 일주일, 한달 등)
   - duration_minutes: 하루 소요 시간(예: 1시간), 시작 및 종료 시간을 참고해서 추출해도 무방합니다.
   - preferred_time: 선호 시간대(예: 오전 9시-11시, 오후 2-4시)
   - frequency: 반복 주기(예: 매일, 매주 월요일)
   - start_end_time: 시작 시간-종료 시간(예: 09:00-10:00), 여행, 하루종일 소요하는 일정일 경우 자동으로 "00:00-23:59"으로 추가하세요.
   - category: 반드시 아래 활동유형 4가지 중 하나로 설정되어야 합니다.
    <활동 유형>
    (1) learning: 세부 공부, 학습 일정 생성 및 추천과 관련된 요청
    (2) exercise: 세부 운동 일정 생성 및 추천과 관련된 요청
    (3) project: 프로젝트 일정 생성 및 추천과 관련된 요청
    (4) other: 어느 활동 유형에도 포함되지 않은 일정 계획 생성 및 추천과 관련된 요청(예: 여행 일정 추천, 기타 다른 일정 추천)

2. type(personal) 분기 기준
  - 단일적이거나 반복적인 일정(예: 6/30 약속, 매주 수요일 미팅, 반복되는 개인 일정 등)은 type: personal로 추가하세요.
  - 일정 추천, 계획 등의 요청일 경우 **절대로** type을 명시하지 마세요.
  - 일정 추천이나 계획등의 요청이 아닌, 단순 일정 생성만을 요청하는 경우에는 반드시 type을 명시하세요.

아래 JSON 형식을 반드시 지켜서 응답하세요.
{format_instructions}

구체적인 예시:
사용자: "7월 10~13일간 강릉으로 여행갈건데 계획 세워서 캘린더에 바로 넣어줘."
응답:
```json
{{
  "task_title": "강릉 여행",
  "intent": "schedule",
  "slots": {{
    "category": "other",
    "duration_minutes": "",
    "preferred_time": "",
    "period": "7월 10~13일",
    "start_end_time": "00:00-23:59",
    "schedule_ask": "False",
    "recommend_ask": "False"
  }}
}}```
"""
)

# 스케줄 생성 시 추가 정보 재질문 프롬프트
schedule_ask_prompt = PromptTemplate(
    input_variables=["history", "user_input", "date"],
    template="""
당신은 스케줄 생성 전문가입니다.
사용자에게 친근하고 자연스로운 말투로 이모지를 사용하여 텍스트 형식으로만 답변하세요.
사용자 대화기록과 요청을 참고하여 일정 생성에 필요한 질문을 생성하세요.
간결하게 필요한 정보만을 질문해야 합니다.

- 대화 기록: {history}
- 사용자 요청: {user_input}
- 현재 시간: {date}

예시:
사용자: 일본 여행을 계획중인데 일정을 생성해주세요.
응답1: 여행 일정은 언제로 계획되어 있나요? ✈️
응답2: 정확한 지역을 말씀해주시면 세부적인 일정 추천이 가능합니다.
"""
)

# 슬롯 추천 프롬프트
slot_recommendation_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "category", "date"],
    template="""
아래 정보를 참고하여 사용자에게 친근한 말투(이모지 포함)로 추천 메세지를 한글로 작성하세요.

- 대화 기록: {history}
- 사용자 입력: {user_input}
- 현재 수집된 슬롯 정보: {slots}
- 활동 카테고리: {category}
- 현재 시간: {date} 

<규칙>
1. 카테고리가 'other'인 경우
 - 대화 기록과 사용자 입력을 중점적으로 참고하여 추천
 - 여행 등의 일정 계획인 경우 지역의 특색과 유명한 코스를 중점적으로 여행 계획을 생성하여 추천
2. 'other'이외의 카테고리는 현재 비어있거나 recommend로 추출된 슬롯을 중점으로 추천

3. 슬롯 종류
- period: 기간(예: 내일(1일), 3일, 일주일, 한달 등)
- duration_minutes: 하루 예상 소요 시간(예: 1시간), 시작 및 종료 시간(예: 09:00-10:00)
- preferred_time: 선호 시간대
- deadline: 마감일(YYYY-MM-DD)
- work_hours: 업무시간(HH:MM-HH:MM)
- frequency (recurring): 반복 주기(예: 매일, 매주 월요일)
- start_end_time: 시작 시간-종료 시간(예: 09:00-10:00)

4. 추천 기준
- 사용자의 task_title, category를 확인하여 평균적인 기준으로 추천
- 난이도가 없을 경우 사용자를 초보자로 고려하여 목표를 달성할 수 있도록 기간, 시간 등을 추천
- period의 경우 최소 하루, 최대 한달
- duration_minutes의 경우 최소 한시간, 최대 세시간
- preferred_time의 경우 오전 7시부터 오후 10사이로 추천하고, 점심시간(오후 12-1시), 저녁시간(오후 6-7시)는 제외

4. 추천 응답과 이유에 대해 텍스트 형식으로만 설명
- 사용자 입력이 단순히 슬롯에 대해서만 추천을 원할 경우 한 문장으로 간단하게 작성
- 일정 추천을 원할 때, 기간이 긴 경우에는 주차별로, 일주일 이내의 기간인 경우 일단위로 계획하여 자세히 답변
- 마지막 답변에는 항상 '이대로 진행할까요?'를 출력
- 슬롯 종류, 슬롯 영어를 그대로 응답하지 말고 풀어서 작성
- 예시: "코딩테스트 공부를 일주일동안 하루에 1시간, 오후 7-8시에 할애하는 것을 추천드려요! 
        6/12(목): 배열 및 기본 연산 개념 학습... 
        일주일동안 충분히 학습 가능하도록 계획했어요! 🔥 이대로 진행할까요?"
"""
)

# 일반 질문 프롬프트
qa_prompt = PromptTemplate(
    input_variables=["history", "user_input", "date"],
    template="""
당신은 Looper 서비스의 친절한 AI 챗봇입니다.
아래의 사용자의 대화 기록과 입력 정보를 확인하고 텍스트 형식으로만 답변해주세요.
이전 대화 기록을 참고하되, 일정 생성과 관련하여 '완료되었습니다, 추가하겠습니다, 캘린더에 넣어드릴게요' 등과 같은 단어는 절대로 포함하지 마세요.
사용자에게 친근한 말투로 적절한 이모지를 사용하여 답변하고, 반말은 절대 사용하지 마세요.
중복되는 응답, 부적절한 언어 등은 포함하지 마세요.

- 대화 기록: {history}
- 사용자: {user_input}
- 현재 시간: {date}

예시: 안녕하세요! Looper 챗봇입니다. 도움이 필요하시면 언제든지 말씀해주세요 ✨
"""
)

# 운동 일정 검색 기반 생성 프롬프트
exercise_prompt = PromptTemplate(
    input_variables=["history", "user_input", "slots", "search_results", "date"],
    template="""
- 대화 기록: {history}
- 사용자 요청: {user_input}

<조건>
- 아래 슬롯 정보와 검색 결과를 바탕으로 운동 스케줄을 구체적으로 생성하세요.
- 검색 결과에서 얻은 최신 운동 정보와 현재 시간을 반영하여 효과적인 운동 계획을 세워주세요.
- 사용자의 입력에 따라 난이도를 고려하되, 난이도가 포함되어 있지 않다면 초보자로 고려하여 일정을 생성하세요.
- 초보자용, 중급자용 등과 같은 난이도를 나타내는 단어는 사용하지 마세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 **모든 일자**를 출력해야 합니다. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)

- 슬롯 정보: {slots}
- 검색 결과: {search_results}
- 현재 시간: {date}

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
- 사용자 요청: {user_input}
- 기존 task_title: {task_title}

당신은 운동 스케줄링 전문가입니다. 아래 조건과 정보를 참고하여 실행 가능한 일정을 생성하세요.
<조건>
- 아래 슬롯 정보, 기존 task_title, 사용자 요청을 바탕으로 학습 스케줄을 구체적으로 생성하세요.
- 학습 스케줄은 주제, 난이도, 학습 순서 등을 고려하여 작성합니다.
- 사용자 입력에 난이도가 포함되어 있지 않다면, 초보자로 고려하여 일정을 생성하세요.
- 초보자용, 중급자용 등과 같은 난이도를 나타내는 단어는 사용하지 마세요.
- 사용자 입력이 이론 위주의 공부라면 프로젝트 계획, 프로젝트 발표 등과 같은 '프로젝트' 키워드는 제외하여야 합니다.
- 현재 시간을 반영하여 효과적인 학습 계획을 세워주세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 **모든 일자**를 출력해야 합니다. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)

- 슬롯 정보: {slots}
- 현재 시간: {date}

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
- 대화 기록: {history}
- 사용자 요청: {user_input}

<조건>
- 아래 슬롯 정보와 사용자 요청을 바탕으로 프로젝트 스케줄을 구체적으로 생성하세요.
- 프로젝트 스케줄은 단계별 의존 관계, 마감일, 리스크 관리 등을 고려하여 작성합니다.
- 현재 시간을 반영하여 체계적인 프로젝트 계획을 세워주세요.
- 각 subtask당 실행 시간은 실제 시행이 가능한 시간으로 고려하여 최소 30분 이상, 모든 시간은 30분, 1시간 단위로 생성하세요.
- 기간을 고려하여 모든 일정을 적절히 배분하여 출력해주세요. 압축하지 말고 **모든 일자**를 출력해야 합니다. 
  (예: 6/12부터 한달동안 운동 계획을 세우는 경우 일주일에 3번 정도로 배분하여 7/12까지, 한달간의 모든 계획을 세워야 합니다.)

- 슬롯 정보: {slots}
- 현재 시간: {date}

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
- 대화 기록: {history}
- 사용자 요청: {user_input}

아래 슬롯 정보와 현재 시간을 바탕으로 스케줄을 구체적으로 생성하세요.
사용자 요청과 슬롯 정보를 기반으로 반복되는 일정 혹은 일반적인 일정을 생성합니다.
기간이 명시되어 있지 않을 경우 기본 한달로 설정하세요.
추가적인 sub_task는 task_title과 동일하게 설정합니다.

- 슬롯 정보: {slots}
- 현재 시간: {date}

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
- 대화 기록: {history}
- 사용자 요청: {user_input}

아래 슬롯 정보와 현재 시간을 바탕으로 스케줄을 구체적으로 생성하세요.
사용자 요청과 슬롯 정보를 기반으로 실제 시행 가능한 일정으로 생성하세요.

- 슬롯 정보: {slots}
- 현재 시간: {date}

아래와 같이 각 subtask를 한 줄 JSON으로, 각 줄마다 출력하세요:
전체를 리스트로 감싸지 마세요. 

예시:
{{"subtasks": "공항 도착", "start_time": "2025-04-21T09:00:00", "end_time": "2025-04-21T10:00:00"}}
..."""
)

# 일정 조회 쿼리 생성 프롬프트
calendar_query_generation_prompt = PromptTemplate(
    input_variables=["history", "user_input", "date"],
    partial_variables={"query_format_instructions": query_format_instructions},
    template="""
아래의 대화 기록과 사용자 입력을 참고하여 일정 조회에 필요한 정보를 추출해 쿼리 JSON을 생성하세요.
<추출 조건>
1. 사용자 입력에 포함된 일정 조회 요청을 추출해야 합니다.
2. 사용자 입력에 기간이 포함되어 있지 않다면 현재 시간을 기준으로 +- 15일로 추출해야 합니다.
3. 최근, 근래, 최신 등과 같이 모호한 기간인 경우 현재 시간을 기준으로 +- 4일 이내의 기간을 추출하세요.
4. task_title_keyword 추출 기준:
  - 사용자 입력에 특정 타이틀이 포함되어 있지 않다면 task_title_keyword는 빈 문자열로 설정해야 합니다.
  - 가장 간단한 한 단어로만 추출해야 합니다. (예: 필라테스, 코딩테스트 등)
  - 예시: "6/30일정 보여줘", "다음주 일정에 대해 말해줘" 등 메인 테스크에 대한 요청이 포함되어 있지 않은 경우
5. 사용자 입력에 category는 4가지 중 하나로 설정해야 합니다.
  (1) learning: 세부 공부, 학습 일정 생성 및 추천과 관련된 요청
  (2) exercise: 세부 운동 일정 생성 및 추천과 관련된 요청
  (3) project: 프로젝트 일정 생성 및 추천과 관련된 요청
  (4) other: 어느 활동 유형에도 포함되지 않은 기타 유형(예: 여행 일정 추천, 기타 다른 일정 추천)
  (5) 일정 기간에 대한 조회를 요청하는 경우 빈 문자열로 설정해야 합니다. (예: 다음주, 6월달, 한달)
6. 운동, 프로젝트, 공부와 같이 모호한 요청에 대해 task_title_keyword가 빈 문자열로 추출되었다면 반드시 category도 빈 문자열로 설정하세요.

- 대화 기록: {history}
- 사용자 요청: {user_input}
- 현재 시간: {date}

아래 형식의 JSON으로 응답하세요:
{query_format_instructions}
예시:
{{
  "start": "YYYY-MM-DDTHH:MM:SS",
  "end": "YYYY-MM-DDTHH:MM:SS",
  "task_title_keyword": "키워드",
  "category": "카테고리"
}}
"""
)

# 일정 조회 결과 요약 프롬프트
calendar_query_summary_prompt = PromptTemplate(
    input_variables=["calendar_results", "user_input", "date"],
    template="""
아래는 사용자의 일정 조회 요청에 대한 DB 조회 결과입니다.

- 사용자 요청: {user_input}
- 조회 결과: {calendar_results}

사용자에게 친근하고 자연스러운 말투로 이모지를 활용하여 답변하세요.
사용자 입력에 적절한 주요 일정(날짜, 시간, 제목 등)을 요약해서 안내하는 답변을 작성하세요.
- 일정이 여러 개면 날짜별로 정리
- 일정이 없으면 "해당 기간에 일정이 없습니다. 조회하고자 하는 일정을 자세하게 입력해주시면 더 원활한 조회가 가능합니다." 등으로 안내
- 예시: "6월 12일(목) 14시~16시, 6월 18일(수) 10시~11시 30분에 필라테스가 예정되어 있습니다."
"""
)