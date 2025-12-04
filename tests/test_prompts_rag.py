import pytest

from app.prompts import experience_plan, materials_suggestion, steps_suggestion


def _sample_args():
    return {
        "category": "자연 및 야외활동",
        "years_of_experience": "10",
        "job_description": "해녀",
        "materials": "테왁, 망사리",
        "location": "제주 바다",
        "duration_minutes": "90",
        "capacity": "6",
        "price_per_person": "80000",
    }


@pytest.mark.anyio
async def test_experience_plan_prompt_without_rag_context_matches_baseline():
    args = _sample_args()

    prompt_without_context = experience_plan.build_user_prompt(**args)

    assert "<reference_context>" not in prompt_without_context
    assert "</reference_context>" not in prompt_without_context


@pytest.mark.anyio
async def test_experience_plan_prompt_appends_rag_context_when_provided():
    args = _sample_args()
    rag_context = "관련 체험 A, 관련 체험 B"

    prompt_with_context = experience_plan.build_user_prompt(
        **args, rag_context=rag_context
    )

    assert "<reference_context>" in prompt_with_context
    assert "</reference_context>" in prompt_with_context
    assert rag_context in prompt_with_context


def _materials_args():
    return {
        "category": "예술 & 디자인",
        "years_of_experience": "3",
        "job_description": "목공 강사",
    }


@pytest.mark.anyio
async def test_materials_prompt_without_rag_context_matches_baseline():
    args = _materials_args()

    prompt = materials_suggestion.build_user_prompt(**args)

    assert "<reference_context>" not in prompt
    assert "</reference_context>" not in prompt


@pytest.mark.anyio
async def test_materials_prompt_appends_rag_context_when_provided():
    args = _materials_args()
    rag_context = "재료 추천 참고 A"

    prompt = materials_suggestion.build_user_prompt(**args, rag_context=rag_context)

    assert "<reference_context>" in prompt
    assert "</reference_context>" in prompt
    assert rag_context in prompt


def _steps_args():
    return {
        "category": "식음료",
        "years_of_experience": "7",
        "job_description": "파티시에",
        "materials": "밀가루, 설탕, 버터",
    }


@pytest.mark.anyio
async def test_steps_prompt_without_rag_context_matches_baseline():
    args = _steps_args()

    prompt = steps_suggestion.build_user_prompt(**args)

    assert "<reference_context>" not in prompt
    assert "</reference_context>" not in prompt


@pytest.mark.anyio
async def test_steps_prompt_appends_rag_context_when_provided():
    args = _steps_args()
    rag_context = "단계 참고 A"

    prompt = steps_suggestion.build_user_prompt(**args, rag_context=rag_context)

    assert "<reference_context>" in prompt
    assert "</reference_context>" in prompt
    assert rag_context in prompt
