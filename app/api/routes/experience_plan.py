"""GPT-based experience plan generation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user_optional
from app.core.database import get_db
from app.libs.openai_client import get_openai_client
from app.models.user import User
from app.prompts import experience_plan as experience_plan_prompts
from app.prompts import materials_suggestion, steps_suggestion

router = APIRouter(prefix="/experience-plan", tags=["experience-plan"])


class ExperienceRequest(BaseModel):
    """Request for experience plan generation with 8 fields."""

    experience_type: str = Field(..., description="체험 유형")
    years_of_experience: str = Field(..., description="해당 분야 경력 년수")
    job_description: str = Field(..., description="직업/전문 분야")
    materials: str = Field(..., description="준비 재료")
    location: str = Field(..., description="만나는 장소")
    duration_minutes: str = Field(..., description="소요 시간 (분)")
    max_participants: str = Field(..., description="최대 참여 인원")
    price_per_person: str = Field(..., description="1인당 요금")


class ExperienceResponse(BaseModel):
    """Response for experience plan generation."""

    template: str = Field(..., description="체험 클래스 전체 템플릿")


@router.post("/", status_code=status.HTTP_200_OK)
async def generate_experience_plan(
    payload: ExperienceRequest,
    _current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
) -> ExperienceResponse:
    """
    OpenAI GPT API를 호출하여 체험 클래스 템플릿 생성.

    Args:
        payload: 8가지 체험 정보
        _current_user: 현재 인증된 사용자 (선택적)
        db: 데이터베이스 세션
        openai_client: OpenAI 비동기 클라이언트

    Returns:
        체험 클래스 전체 템플릿 텍스트
    """
    # db dependency kept for parity/transaction control if needed
    _ = db

    system_prompt = experience_plan_prompts.get_system_prompt()
    user_prompt = experience_plan_prompts.build_user_prompt(
        experience_type=payload.experience_type,
        years_of_experience=payload.years_of_experience,
        job_description=payload.job_description,
        materials=payload.materials,
        location=payload.location,
        duration_minutes=payload.duration_minutes,
        max_participants=payload.max_participants,
        price_per_person=payload.price_per_person,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    completion = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0,
    )

    template = completion.choices[0].message.content

    return ExperienceResponse(template=template)


class MaterialsSuggestionRequest(BaseModel):
    """Request for materials suggestion."""

    experience_type: str = Field(..., description="체험 유형")
    years_of_experience: str = Field(..., description="해당 분야 경력 년수")
    job_description: str = Field(..., description="직업/전문 분야")


class MaterialsSuggestionResponse(BaseModel):
    """Response for materials suggestion."""

    suggestion: str = Field(..., description="재료 추천 텍스트")


@router.post("/materials-suggestion", status_code=status.HTTP_200_OK)
async def suggest_materials(
    payload: MaterialsSuggestionRequest,
    _current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
) -> MaterialsSuggestionResponse:
    """
    OpenAI GPT API를 호출하여 재료 추천 텍스트 생성.

    Args:
        payload: 체험 유형, 경력, 직업 정보
        _current_user: 현재 인증된 사용자 (선택적)
        db: 데이터베이스 세션
        openai_client: OpenAI 비동기 클라이언트

    Returns:
        재료 추천 텍스트를 포함한 응답
    """
    # db dependency kept for parity/transaction control if needed
    _ = db

    system_prompt = materials_suggestion.get_system_prompt()
    user_prompt = materials_suggestion.build_user_prompt(
        experience_type=payload.experience_type,
        years_of_experience=payload.years_of_experience,
        job_description=payload.job_description,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    completion = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0,
    )

    suggestion = completion.choices[0].message.content

    return MaterialsSuggestionResponse(suggestion=suggestion)


class StepsSuggestionRequest(BaseModel):
    """Request for steps suggestion."""

    experience_type: str = Field(..., description="체험 유형")
    years_of_experience: str = Field(..., description="해당 분야 경력 년수")
    job_description: str = Field(..., description="직업/전문 분야")
    materials: str = Field(..., description="준비 재료")


class StepsSuggestionResponse(BaseModel):
    """Response for steps suggestion."""

    suggestion: str = Field(..., description="단계별 방법 텍스트")


@router.post("/steps-suggestion", status_code=status.HTTP_200_OK)
async def suggest_steps(
    payload: StepsSuggestionRequest,
    _current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
    openai_client: AsyncOpenAI = Depends(get_openai_client),
) -> StepsSuggestionResponse:
    """
    OpenAI GPT API를 호출하여 단계별 방법 텍스트 생성.

    Args:
        payload: 체험 유형, 경력, 직업, 재료 정보
        _current_user: 현재 인증된 사용자 (선택적)
        db: 데이터베이스 세션
        openai_client: OpenAI 비동기 클라이언트

    Returns:
        단계별 방법 텍스트를 포함한 응답
    """
    # db dependency kept for parity/transaction control if needed
    _ = db

    system_prompt = steps_suggestion.get_system_prompt()
    user_prompt = steps_suggestion.build_user_prompt(
        experience_type=payload.experience_type,
        years_of_experience=payload.years_of_experience,
        job_description=payload.job_description,
        materials=payload.materials,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    completion = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0,
    )

    suggestion = completion.choices[0].message.content

    return StepsSuggestionResponse(suggestion=suggestion)
