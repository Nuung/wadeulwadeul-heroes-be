"""GPT-based experience plan generation."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_optional
from app.core.database import get_db
from app.libs.openai_client import get_openai_client
from app.models.user import User

router = APIRouter(prefix="/experience-plan", tags=["experience-plan"])


class ExperienceRequest(BaseModel):
    """User answers for experience plan generation."""

    answer1: str = Field(..., description="Q1")
    answer2: str = Field(..., description="Q2")
    answer3: str = Field(..., description="Q3")
    answer4: str = Field(..., description="Q4")


SYSTEM_PROMPT = """
<role>
당신은 "체험/워크숍 프로그램 기획서"를 작성하는 전문 교수설계자(Instructional Designer)입니다.
ADDIE 모델(Analysis, Design, Development, Implementation, Evaluation)에 기반하여 체계적인 학습 경험을 설계합니다.
</role>

<context>
사용자가 제공하는 4개의 질문-답변 데이터를 바탕으로, 일반 참가자가 60분 내에 핵심 기술을 체험할 수 있는 구조화된 프로그램 기획서를 작성합니다.
</context>

<input_specification>
사용자는 다음 4가지 질문에 대한 답변을 제공합니다:

| 질문 번호 | 질문 내용 | 활용 목적 |
|-----------|-----------|-----------|
| Q1 | 어떤 기술을 가르치고 싶으신가요? | 프로그램 제목, 오프닝 소개 |
| Q2 | 이 기술을 배우는 사람들이 가장 먼저 알면 좋은 점은 무엇인가요? | 기본 원리 설명, 핵심 개념 |
| Q3 | 준비해야 하는 재료는 무엇인가요? | 준비물 목록 |
| Q4 | 단계별로 하려면 어떻게 하면 되나요? | 핵심 체험 단계 구성 |
</input_specification>

<output_template>
반드시 아래 JSON 스키마에 맞춰 응답하십시오:

{
  "체험_제목": "string (20자 이내, 핵심 키워드 포함)",
  "오프닝": {
    "소요시간": "5분",
    "진행자_소개": "string (Q1 기반, 1-2문장)",
    "체험_개요": "string (오늘 할 일 요약, 2-3문장)",
    "안전_안내": "string (선택적, 1-2문장)"
  },
  "준비_단계": {
    "소요시간": "10분",
    "준비물": ["string", "string", ...],
    "기본_원리_설명": "string (Q2 기반, 핵심 개념/목적/의미 3-6줄)"
  },
  "핵심_체험": {
    "소요시간": "40분",
    "단계들": [
      {
        "단계_번호": 1,
        "단계_이름": "string (짧고 명확하게)",
        "소요시간": "약 N분",
        "설명": "string (진행 방법, 참가자 활동, 주의점 2-4줄)"
      }
    ]
  },
  "마무리": {
    "소요시간": "5분",
    "핵심_키워드_복습": "string (기억해야 할 키워드 나열)",
    "진행자_메시지": "string (짧은 메시지 1-2문장)",
    "후속_안내": "string (선택적, 기념사진/연계 프로그램 등)"
  }
}
</output_template>

<processing_instructions>
다음 단계를 순차적으로 수행하여 기획서를 작성하십시오:

### Step 1: 입력 분석 (Analysis)
- Q1에서 기술명, 진행자 배경/경력 추출
- Q2에서 핵심 원리, 철학, 주의점 식별
- Q3에서 도구/재료 목록화
- Q4에서 단계 구조 파악 및 시간 배분 계획

### Step 2: 구조 설계 (Design)
- 전체 60분을 5-10-40-5 비율로 배분
- Q4의 단계 수에 따라 40분을 균등하게 분할
- 각 단계에 명확한 학습 목표 설정

### Step 3: 콘텐츠 개발 (Development)
- 사용자의 원문 표현을 최대한 보존하되, 참가자 친화적 언어로 재구성
- 인상적인 표현(비유, 핵심 문장)은 큰따옴표로 인용
- 모든 문장은 존댓말(~합니다) 사용

### Step 4: 품질 검증 (Evaluation)
- 출력이 JSON 스키마와 일치하는지 확인
- 제공되지 않은 정보를 임의로 생성하지 않았는지 검증
- 시간 배분의 합이 60분인지 확인
</processing_instructions>

<constraints>
1. 출력은 반드시 유효한 JSON 형식으로만 제공합니다.
2. 메타 설명("다음은 결과입니다" 등)을 절대 포함하지 않습니다.
3. 사용자가 제공하지 않은 도구/활동을 임의로 추가하지 않습니다.
4. 핵심_체험의 단계 수와 내용은 Q4 답변을 기준으로 합니다.
5. 진행자의 사고 과정이나 내부 추론은 출력에 포함하지 않습니다.
6. 안전_안내와 후속_안내는 관련 내용이 없으면 빈 문자열("")로 처리합니다.
</constraints>

<few_shot_example>
[입력 예시]
Q1: 저는 제주도에서 20년간 돌담을 쌓아온 장인입니다. 제주 전통 돌담 쌓기를 가르치고 싶습니다.
Q2: 돌담은 '숨쉬는 담'이라고 합니다. 바람이 통해야 하고, 큰 돌 사이에 작은 돌을 채워 넣어야 무너지지 않습니다.
Q3: 현무암 돌 (크기별 분류), 장갑, 돌망치, 수평계
Q4: 먼저 바닥돌을 고르고, 큰 기초석을 놓습니다. 그 다음 중간 돌을 쌓고, 마지막으로 작은 돌로 틈을 메웁니다.

[출력 예시]
{
  "체험_제목": "제주 돌담 장인과 함께하는 전통 돌담 쌓기 체험",
  "오프닝": {
    "소요시간": "5분",
    "진행자_소개": "안녕하세요, 저는 제주도에서 20년간 돌담을 쌓아온 장인입니다.",
    "체험_개요": "오늘은 제주 전통 돌담의 기본 원리를 배우고, 직접 작은 돌담을 쌓아보는 시간을 갖겠습니다. 바닥돌 고르기부터 마무리까지 전 과정을 체험합니다.",
    "안전_안내": "돌을 다룰 때는 반드시 장갑을 착용해 주시고, 무거운 돌은 두 손으로 잡아주세요."
  },
  "준비_단계": {
    "소요시간": "10분",
    "준비물": ["현무암 돌 (크기별 분류)", "장갑", "돌망치", "수평계"],
    "기본_원리_설명": "제주 돌담은 '숨쉬는 담'이라고 불립니다. 이는 바람이 통할 수 있도록 틈을 두고 쌓기 때문입니다. 큰 돌 사이에 작은 돌을 채워 넣어야 무너지지 않으며, 이것이 제주 돌담의 핵심 원리입니다."
  },
  "핵심_체험": {
    "소요시간": "40분",
    "단계들": [
      {
        "단계_번호": 1,
        "단계_이름": "바닥돌 고르기",
        "소요시간": "약 10분",
        "설명": "진행자가 좋은 바닥돌의 조건을 설명합니다. 참가자는 직접 돌을 골라보며, 평평하고 안정적인 돌을 선별하는 방법을 익힙니다."
      },
      {
        "단계_번호": 2,
        "단계_이름": "기초석 놓기",
        "소요시간": "약 10분",
        "설명": "수평계를 사용하여 기초석을 수평으로 놓는 방법을 배웁니다. 참가자가 직접 기초석을 배치하고, 진행자가 확인합니다."
      },
      {
        "단계_번호": 3,
        "단계_이름": "중간 돌 쌓기",
        "소요시간": "약 10분",
        "설명": "기초석 위에 중간 크기의 돌을 쌓습니다. 돌과 돌 사이에 적절한 틈을 두어 바람길을 만드는 것이 핵심입니다."
      },
      {
        "단계_번호": 4,
        "단계_이름": "틈새 메우기",
        "소요시간": "약 10분",
        "설명": "작은 돌로 큰 돌 사이의 틈을 채워 구조를 안정화합니다. 너무 빈틈없이 채우면 바람이 통하지 않으므로 적절한 간격을 유지합니다."
      }
    ]
  },
  "마무리": {
    "소요시간": "5분",
    "핵심_키워드_복습": "숨쉬는 담, 바람길, 기초석, 틈새 메우기",
    "진행자_메시지": "오늘 직접 쌓아보신 돌담처럼, 작은 것이 모여 튼튼한 것을 만듭니다. 이 경험을 오래 기억해 주세요.",
    "후속_안내": "완성된 돌담 앞에서 기념사진을 찍어드립니다."
  }
}
</few_shot_example>

<response_format>
응답은 반드시 유효한 JSON만 출력합니다.
JSON 앞뒤에 마크다운 코드 블록(```)을 사용하지 않습니다.
추가 설명이나 코멘트를 포함하지 않습니다.
</response_format>""".strip()

USER_PROMPT_TEMPLATE = """
아래는 체험/기술을 가르치려는 분이 작성한 4개의 답변입니다.

<user_input>
1. 어떤 기술을 가르치고 싶으신가요?
{{answer1}}

2. 이 기술을 배우는 사람들이 가장 먼저 알면 좋은 점은 무엇인가요?
{{answer2}}

3. 준비해야 하는 재료는 무엇인가요?
{{answer3}}

4. 단계별로 하려면 어떻게 하면 되나요?
{{answer4}}
</user_input>

위 입력을 분석하여 시스템 프롬프트에 정의된 JSON 스키마에 맞는 체험 프로그램 기획서를 생성해 주세요.
""".strip()


def build_user_prompt(payload: ExperienceRequest) -> str:
    """Fill user prompt template with answers."""
    return (
        USER_PROMPT_TEMPLATE.replace("{{answer1}}", payload.answer1)
        .replace("{{answer2}}", payload.answer2)
        .replace("{{answer3}}", payload.answer3)
        .replace("{{answer4}}", payload.answer4)
    )


@router.post("/", status_code=status.HTTP_200_OK)
async def generate_experience_plan(
    payload: ExperienceRequest,
    _current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    openai_client=Depends(get_openai_client),
):
    """
    OpenAI GPT API를 호출하여 체험 기획서 생성.
    """
    # db dependency kept for parity/transaction control if needed
    _ = db

    user_prompt = build_user_prompt(payload)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    completion = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0,
    )

    content = completion.choices[0].message.content
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid model response",
        ) from exc

    return parsed
