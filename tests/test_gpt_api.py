import json
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes import experience_plan as experience_plan_api
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


class _StubRAGRetriever:
    def __init__(self, context: str, raise_error: bool = False):
        self.context = context
        self.raise_error = raise_error
        self.called_queries: list[str] = []

    def retrieve(self, query: str, top_k: int = 3):
        self.called_queries.append(query)
        self.last_top_k = top_k
        if self.raise_error:
            raise RuntimeError("rag failure")
        return [
            {
                "title": self.context or "워크숍 A",
                "introduction": "소개 A",
                "alltag": "tagA",
                "address": "주소 A",
            }
        ]


@pytest.fixture
async def client():
    expected_output = {
        "체험 제목": "한 시간 만에 배우는 제주 돌담 쌓기 기초 체험",
        "클래스 소개": "제주 돌담을 처음 배우는 분들을 위한 기초 체험입니다. 현무암의 특성을 이해하고 기본 쌓기 원리를 배웁니다.",
        "난이도": "초급 - 누구나 쉽게 참여할 수 있으며 안전 교육과 함께 진행됩니다.",
        "로드맵": "돌담 기초를 시작으로 전통 돌담 보수, 마을 경관 프로젝트까지 확장할 수 있습니다.",
        "오프닝": "5분 - 제주 돌담 소개, 안전 교육, 오늘의 일정 안내",
        "준비 단계": "10분 - 도구 사용법, 돌 고르는 법, 기초 원리 학습",
        "핵심 체험": "40분 - Step 1: 돌 고르기 (5분) | Step 2: 바닥돌 놓기 (10분) | Step 3: 쌓기 체험 (20분) | Step 4: 완성 확인 (5분)",
        "마무리": "5분 - 핵심 복습, 다른 돌담 종류 소개, 기념 촬영",
        "준비물": "다양한 크기의 돌, 튼튼한 장갑, 무릎 보호대, 작업 매트, 보호 안경",
        "특별 안내사항": "돌을 옮길 때 손가락을 조심하시고 무거운 돌은 혼자 들지 마세요. 보호 안경 착용이 필수입니다.",
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
    assert response_data == expected_output

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


@pytest.mark.anyio
async def test_materials_suggestion_uses_rag_context_when_available():
    expected_suggestion = "dummy"
    fake_client = _FakeOpenAIClient(expected_suggestion)
    rag_context = "재료 컨텍스트 A"
    stub_retriever = _StubRAGRetriever(context=rag_context)

    async def _override_openai():
        return fake_client

    def _override_rag():
        return stub_retriever

    app.dependency_overrides[openai_client.get_openai_client] = _override_openai
    app.dependency_overrides[experience_plan_api.get_rag_retriever] = _override_rag

    payload = {
        "category": "자연 및 야외활동",
        "years_of_experience": "3",
        "job_description": "해녀",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        res = await ac.post("/api/v1/experience-plan/materials-suggestion", json=payload)

    app.dependency_overrides.clear()

    assert res.status_code == 200
    assert stub_retriever.called_queries
    user_message = fake_client.store["messages"][1]["content"]
    assert "<reference_context>" in user_message
    assert rag_context in user_message


@pytest.mark.anyio
async def test_materials_suggestion_falls_back_when_rag_fails():
    expected_suggestion = "dummy"
    fake_client = _FakeOpenAIClient(expected_suggestion)
    stub_retriever = _StubRAGRetriever(context="", raise_error=True)

    async def _override_openai():
        return fake_client

    def _override_rag():
        return stub_retriever

    app.dependency_overrides[openai_client.get_openai_client] = _override_openai
    app.dependency_overrides[experience_plan_api.get_rag_retriever] = _override_rag

    payload = {
        "category": "자연 및 야외활동",
        "years_of_experience": "3",
        "job_description": "해녀",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        res = await ac.post("/api/v1/experience-plan/materials-suggestion", json=payload)

    app.dependency_overrides.clear()

    assert res.status_code == 200
    user_message = fake_client.store["messages"][1]["content"]
    assert "<reference_context>" not in user_message


@pytest.mark.anyio
async def test_steps_suggestion_uses_rag_context_when_available():
    expected_steps = "dummy"
    fake_client = _FakeOpenAIClient(expected_steps)
    rag_context = "단계 컨텍스트 A"
    stub_retriever = _StubRAGRetriever(context=rag_context)

    async def _override_openai():
        return fake_client

    def _override_rag():
        return stub_retriever

    app.dependency_overrides[openai_client.get_openai_client] = _override_openai
    app.dependency_overrides[experience_plan_api.get_rag_retriever] = _override_rag

    payload = {
        "category": "자연 및 야외활동",
        "years_of_experience": "3",
        "job_description": "해녀",
        "materials": "테왁",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        res = await ac.post("/api/v1/experience-plan/steps-suggestion", json=payload)

    app.dependency_overrides.clear()

    assert res.status_code == 200
    assert stub_retriever.called_queries
    user_message = fake_client.store["messages"][1]["content"]
    assert "<reference_context>" in user_message
    assert rag_context in user_message


@pytest.mark.anyio
async def test_steps_suggestion_falls_back_when_rag_fails():
    expected_steps = "dummy"
    fake_client = _FakeOpenAIClient(expected_steps)
    stub_retriever = _StubRAGRetriever(context="", raise_error=True)

    async def _override_openai():
        return fake_client

    def _override_rag():
        return stub_retriever

    app.dependency_overrides[openai_client.get_openai_client] = _override_openai
    app.dependency_overrides[experience_plan_api.get_rag_retriever] = _override_rag

    payload = {
        "category": "자연 및 야외활동",
        "years_of_experience": "3",
        "job_description": "해녀",
        "materials": "테왁",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        res = await ac.post("/api/v1/experience-plan/steps-suggestion", json=payload)

    app.dependency_overrides.clear()

    assert res.status_code == 200
    user_message = fake_client.store["messages"][1]["content"]
    assert "<reference_context>" not in user_message


@pytest.mark.anyio
async def test_generate_experience_plan_uses_rag_context_when_available():
    expected_output = {
        "체험 제목": "dummy",
        "클래스 소개": "dummy",
        "난이도": "dummy",
        "로드맵": "dummy",
        "오프닝": "dummy",
        "준비 단계": "dummy",
        "핵심 체험": "dummy",
        "마무리": "dummy",
        "준비물": "dummy",
        "특별 안내사항": "dummy",
    }
    fake_client = _FakeOpenAIClient(json.dumps(expected_output))
    rag_context = "워크숍 A | 소개 A | tagA | 주소 A"
    stub_retriever = _StubRAGRetriever(context=rag_context)

    async def _override_openai():
        return fake_client

    def _override_rag():
        return stub_retriever

    app.dependency_overrides[openai_client.get_openai_client] = _override_openai
    app.dependency_overrides[experience_plan_api.get_rag_retriever] = _override_rag

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

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        res = await ac.post("/api/v1/experience-plan", json=payload)

    app.dependency_overrides.clear()

    assert res.status_code == 200
    assert stub_retriever.called_queries
    messages = fake_client.store["messages"]
    user_message = messages[1]["content"]
    assert "<reference_context>" in user_message
    assert rag_context in user_message


@pytest.mark.anyio
async def test_generate_experience_plan_falls_back_when_rag_fails():
    expected_output = {
        "체험 제목": "dummy",
        "클래스 소개": "dummy",
        "난이도": "dummy",
        "로드맵": "dummy",
        "오프닝": "dummy",
        "준비 단계": "dummy",
        "핵심 체험": "dummy",
        "마무리": "dummy",
        "준비물": "dummy",
        "특별 안내사항": "dummy",
    }
    fake_client = _FakeOpenAIClient(json.dumps(expected_output))
    stub_retriever = _StubRAGRetriever(context="", raise_error=True)

    async def _override_openai():
        return fake_client

    def _override_rag():
        return stub_retriever

    app.dependency_overrides[openai_client.get_openai_client] = _override_openai
    app.dependency_overrides[experience_plan_api.get_rag_retriever] = _override_rag

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

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        res = await ac.post("/api/v1/experience-plan", json=payload)

    app.dependency_overrides.clear()

    assert res.status_code == 200
    user_message = fake_client.store["messages"][1]["content"]
    assert "<reference_context>" not in user_message
