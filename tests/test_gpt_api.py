from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.libs import openai_client
from app.main import app


class _FakeCompletion:
    def __init__(self, content: str):
        self.choices = [
            type(
                "Choice",
                (),
                {"message": type("Msg", (), {"content": content})()},
            )()
        ]


class _FakeCompletions:
    def __init__(self, store: dict[str, Any]):
        self.store = store

    async def create(self, *, model: str, messages: list[dict], temperature: int):
        self.store["model"] = model
        self.store["messages"] = messages
        self.store["temperature"] = temperature
        return _FakeCompletion(self.store["response_content"])


class _FakeChat:
    def __init__(self, store: dict[str, Any]):
        self.completions = _FakeCompletions(store)


class _FakeOpenAIClient:
    def __init__(self, content: str):
        self.store: dict[str, Any] = {"response_content": content}
        self.chat = _FakeChat(self.store)


@pytest.fixture
async def client():
    expected_output = """체험 제목: "한 시간 만에 배우는 제주 돌담 기초 체험"

1) 오프닝 (5분)
"안녕하세요, 저는 제주 마을에서 평생 돌담 쌓아온 장인입니다."
오늘 할 것: 제주 돌담의 원리 + 작은 돌담 조각 만들어 보기
안전 설명: 돌 옮길 때 손가락 주의, 무거운 돌 혼자 들지 말기

2) 준비 단계 (10분)
필요한 준비물: 다양한 크기의 돌, 장갑, 수평 확인용 작은 막대, 작업 매트
기본 원리 간단 설명: 돌담은 시멘트를 사용하지 않고 돌과 돌의 균형으로 쌓는다

3) 핵심 체험 (40분)
Step 1: 돌 고르기 (5분)
Step 2: 바닥돌 놓기 (10분)
Step 3: 쌓기 체험 (20분)
Step 4: 완성 확인 (5분)

4) 마무리 (5분)
"돌담은 결국 사람과 자연의 대화입니다."
오늘 배운 돌담 원리 복습"""

    fake_client = _FakeOpenAIClient(expected_output)

    async def _override():
        return fake_client

    app.dependency_overrides[openai_client.get_openai_client] = _override

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac, expected_output, fake_client

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_generate_experience_plan_uses_prompts(client):
    ac, expected_output, fake_client = client

    payload = {
        "category": "자연 및 야외활동",
        "years_of_experience": "20",
        "job_description": "제주도 돌담 장인",
        "materials": "현무암 돌 (크기별 분류), 장갑, 돌망치, 수평계",
        "location": "제주 마을 야외 작업장",
        "duration_minutes": "60",
        "capacity": "10",
        "price_per_person": "50000",
    }

    res = await ac.post("/api/v1/experience-plan", json=payload)
    assert res.status_code == 200
    response_data = res.json()
    assert "template" in response_data
    assert response_data["template"] == expected_output

    messages = fake_client.store["messages"]
    assert messages[0]["role"] == "system"
    assert "체험" in messages[0]["content"] or "클래스" in messages[0]["content"]
    user_message = messages[1]["content"]
    assert payload["category"] in user_message
    assert payload["job_description"] in user_message
    assert payload["materials"] in user_message
    assert payload["location"] in user_message
    assert fake_client.store["model"] == "gpt-4o"


@pytest.fixture
async def materials_client():
    expected_suggestion = "체험용으로 작은 돌들이 여러 크기로 필요합니다. 작업 장갑, 수평 맞추는 막대, 그리고 돌 놓을 작업 매트가 있으면 안전합니다."
    fake_client = _FakeOpenAIClient(expected_suggestion)

    async def _override():
        return fake_client

    app.dependency_overrides[openai_client.get_openai_client] = _override

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac, expected_suggestion, fake_client

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_materials_suggestion_returns_text(materials_client):
    ac, expected_suggestion, _fake_client = materials_client

    payload = {
        "category": "예술 & 디자인",
        "years_of_experience": "5",
        "job_description": "돌담 쌓기 장인",
    }

    res = await ac.post("/api/v1/experience-plan/materials-suggestion", json=payload)
    assert res.status_code == 200
    response_data = res.json()
    assert "suggestion" in response_data
    assert response_data["suggestion"] == expected_suggestion


@pytest.mark.anyio
async def test_materials_suggestion_uses_correct_prompts(materials_client):
    ac, _expected_suggestion, fake_client = materials_client

    payload = {
        "category": "자연 및 야외활동",
        "years_of_experience": "20",
        "job_description": "제주도 돌담 장인",
    }

    res = await ac.post("/api/v1/experience-plan/materials-suggestion", json=payload)
    assert res.status_code == 200

    messages = fake_client.store["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "재료" in messages[0]["content"] or "준비물" in messages[0]["content"]

    user_message = messages[1]["content"]
    assert payload["category"] in user_message
    assert payload["years_of_experience"] in user_message
    assert payload["job_description"] in user_message
    assert fake_client.store["model"] == "gpt-4o"


@pytest.fixture
async def steps_client():
    expected_steps = "첫째, 밑에 놓을 큰 돌을 고르는 것부터 시작합니다. 둘째, 바닥돌이 흔들리지 않게 자리를 잡아줍니다. 셋째, 그 위에 돌을 어긋나게 놓으면서 쌓아갑니다. 넷째, 돌 사이 빈틈을 작은 돌로 끼워 넣어 단단히 고정합니다. 마지막으로 흔들림을 확인하고 정리하면 끝납니다."
    fake_client = _FakeOpenAIClient(expected_steps)

    async def _override():
        return fake_client

    app.dependency_overrides[openai_client.get_openai_client] = _override

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac, expected_steps, fake_client

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_steps_suggestion_returns_text(steps_client):
    ac, expected_steps, _fake_client = steps_client

    payload = {
        "category": "자연 및 야외활동",
        "years_of_experience": "20",
        "job_description": "제주도 돌담 장인",
        "materials": "현무암 돌 (크기별 분류), 장갑, 돌망치, 수평계",
    }

    res = await ac.post("/api/v1/experience-plan/steps-suggestion", json=payload)
    assert res.status_code == 200
    response_data = res.json()
    assert "suggestion" in response_data
    assert response_data["suggestion"] == expected_steps


@pytest.mark.anyio
async def test_steps_suggestion_uses_correct_prompts(steps_client):
    ac, _expected_steps, fake_client = steps_client

    payload = {
        "category": "예술 & 디자인",
        "years_of_experience": "5",
        "job_description": "도자기 작가",
        "materials": "도자기 반제품, 유약, 붓, 스펀지",
    }

    res = await ac.post("/api/v1/experience-plan/steps-suggestion", json=payload)
    assert res.status_code == 200

    messages = fake_client.store["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "단계" in messages[0]["content"] or "방법" in messages[0]["content"]

    user_message = messages[1]["content"]
    assert payload["category"] in user_message
    assert payload["years_of_experience"] in user_message
    assert payload["job_description"] in user_message
    assert payload["materials"] in user_message
    assert fake_client.store["model"] == "gpt-4o"
