import json
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

    async def create(self, *, model: str, messages: list[dict], temperature: int, **kwargs):
        self.store["model"] = model
        self.store["messages"] = messages
        self.store["temperature"] = temperature
        if kwargs:
            self.store["extra"] = kwargs
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
    expected_output = {
        "template": '체험 제목: "한 시간 만에 배우는 제주 돌담 쌓기 기초 체험"\n\n1) 오프닝 (5분)\n- "안녕하세요, 저는 제주도에서 10년간 돌담 쌓기 전문가로 활동하고 있는 [호스트 이름]입니다."\n- 오늘 할 것: 제주 돌담의 기본 원리를 배우고, 직접 작은 돌담을 쌓아보는 체험을 진행합니다.\n- 안전 안내: 돌을 옮길 때 손가락을 조심하시고, 무거운 돌은 혼자 들지 마시기 바랍니다. 보호 안경을 착용하여 눈을 보호하세요.\n\n2) 준비 단계 (10분)\n- 필요한 준비물: 다양한 크기의 돌, 튼튼한 장갑, 무릎 보호대, 작업 매트, 보호 안경\n- 기본 원리 간단 설명: 돌담은 시멘트를 사용하지 않고 돌과 돌의 균형으로 쌓습니다. "큰 돌 아래, 작은 돌 위"라는 원칙을 기억하세요. 돌 사이의 균형과 안정감을 주는 것이 중요합니다.\n\n3) 핵심 체험 (40분)\n- Step 1: 돌 고르기 (5분)\n  - 크고 평평한 돌을 \'바닥돌\'로 선택합니다. 참가자 각자 돌의 모양을 살펴보며 좋은 돌을 고르는 법을 배웁니다.\n\n- Step 2: 바닥돌 놓기 (10분)\n  - 수평을 맞추기 위해 작업 매트를 사용하여 바닥돌을 놓는 방법을 배웁니다. 돌의 \'앉는 자리(면)\'를 찾는 법을 직접 시도해봅니다.\n\n- Step 3: 쌓기 체험 (20분)\n  - 돌과 돌 사이를 어긋나게 놓으면서 쌓아갑니다. 빈 곳을 작은 돌로 \'끼워 넣기\'를 실습합니다. 돌이 흔들릴 때는 돌 모양을 바꾸거나 아래 돌을 다시 조정하는 법을 배웁니다.\n\n- Step 4: 완성 확인 (5분)\n  - 완성된 돌담의 흔들림을 체크하고, 바다 근처에서 참가자들의 작품을 함께 감상합니다. 기념 사진을 촬영합니다.\n\n4) 마무리 (5분)\n- "돌담은 자연과의 조화 속에서 만들어지는 예술입니다."\n- 오늘 배운 핵심: 균형, 큰 돌과 작은 돌의 조화, 자연스러운 틈\n- 다른 돌담 종류(방풍담, 밭담) 간단 소개\n- "다음에 기회가 되신다면 더 큰 돌담 쌓기 체험도 도전해보세요!"',
        "클래스 소개": "제주 돌담을 처음 배우는 분들을 위한 기초 체험입니다.",
        "난이도": "초급",
        "로드맵": "돌담 기초를 시작으로 전통 돌담 보수, 마을 경관 프로젝트까지 확장할 수 있습니다.",
    }

    fake_client = _FakeOpenAIClient(json.dumps(expected_output))

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
