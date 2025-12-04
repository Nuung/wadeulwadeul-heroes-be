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
    expected_output = {"체험_제목": "테스트"}
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
        "answer1": "AI 그림 그리기",
        "answer2": "프로세스 이해",
        "answer3": "태블릿, 펜",
        "answer4": "스케치 후 채색",
    }

    res = await ac.post("/api/v1/experience-plan", json=payload)
    assert res.status_code == 200
    assert res.json() == expected_output

    messages = fake_client.store["messages"]
    assert messages[0]["role"] == "system"
    assert "체험/워크숍 프로그램 기획서" in messages[0]["content"]
    user_message = messages[1]["content"]
    assert payload["answer1"] in user_message
    assert "{{answer1}}" not in user_message
    assert fake_client.store["model"] == "gpt-4o"
