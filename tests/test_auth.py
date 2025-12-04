"""Tests for authentication with UUID-based headers."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import auth as auth_module
from app.core import database as db_module
from app.core.database import Base
from app.main import app
from app.models.user import User, UserType


@pytest.fixture
async def session_maker(tmp_path):
    """독립적인 SQLite 세션 팩토리."""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    TestingSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 미들웨어와 get_db가 같은 세션 팩토리를 사용하도록 패치
    auth_module.AsyncSessionLocal = TestingSessionLocal
    db_module.AsyncSessionLocal = TestingSessionLocal

    try:
        yield TestingSessionLocal
    finally:
        await engine.dispose()


@pytest.fixture
async def client(session_maker):
    """테스트 클라이언트."""

    async def override_get_db():
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from app.core.database import get_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)  # type: ignore
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_auth_with_valid_uuid(client: AsyncClient, session_maker) -> None:
    """
    테스트: 유효한 UUID로 인증 성공

    Given: 데이터베이스에 사용자가 존재
    When: wadeulwadeul-user 헤더에 해당 사용자의 UUID를 전달
    Then: 인증이 성공하고 사용자 정보를 반환
    """
    # Given: 사용자 생성
    async with session_maker() as session:
        user = User(name="Test User", email="test@example.com", type=UserType.OLD)
        session.add(user)
        await session.flush()
        await session.refresh(user)
        user_id = user.id
        await session.commit()

    # When: UUID를 헤더로 전달하여 API 호출
    response = await client.get(
        "/api/v1/users/me",
        headers={"wadeulwadeul-user": str(user_id)},
    )

    # Then: 200 응답 및 사용자 정보 확인
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_id)
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"


@pytest.mark.anyio
async def test_auth_with_invalid_uuid_format(client: AsyncClient) -> None:
    """
    테스트: 잘못된 UUID 형식

    Given: 잘못된 UUID 형식의 문자열
    When: wadeulwadeul-user 헤더에 전달
    Then: 401 Unauthorized 에러 발생
    """
    # When: 잘못된 UUID 형식 전달
    response = await client.get(
        "/api/v1/users/me",
        headers={"wadeulwadeul-user": "not-a-valid-uuid"},
    )

    # Then: 401 에러
    assert response.status_code == 401


@pytest.mark.anyio
async def test_auth_with_nonexistent_uuid(client: AsyncClient) -> None:
    """
    테스트: 존재하지 않는 UUID

    Given: 유효하지만 존재하지 않는 UUID
    When: wadeulwadeul-user 헤더에 전달
    Then: 401 Unauthorized 에러 발생
    """
    # Given: 존재하지 않는 UUID 생성
    nonexistent_uuid = uuid4()

    # When: 존재하지 않는 UUID 전달
    response = await client.get(
        "/api/v1/users/me",
        headers={"wadeulwadeul-user": str(nonexistent_uuid)},
    )

    # Then: 401 에러
    assert response.status_code == 401


@pytest.mark.anyio
async def test_auth_without_header(client: AsyncClient) -> None:
    """
    테스트: 헤더 없이 요청

    Given: 헤더 없이 요청
    When: 인증이 필요한 엔드포인트 호출
    Then: 401 Unauthorized 에러 발생
    """
    # When: 헤더 없이 요청
    response = await client.get("/api/v1/users/me")

    # Then: 401 에러
    assert response.status_code == 401


@pytest.mark.anyio
async def test_create_user_without_email(session_maker) -> None:
    """
    테스트: Email 없이 User 생성

    Given: email 필드 없이 사용자 데이터
    When: User를 생성
    Then: 정상적으로 생성됨
    """
    # Given & When: email 없이 사용자 생성
    async with session_maker() as session:
        user = User(name="No Email User", type=UserType.YOUNG)
        session.add(user)
        await session.flush()
        await session.refresh(user)

        # Then: 정상 생성 확인
        assert user.id is not None
        assert user.name == "No Email User"
        assert user.email is None

        user_id = user.id
        await session.commit()

    # 데이터베이스에서 조회하여 재확인
    async with session_maker() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        saved_user = result.scalar_one()
        assert saved_user.email is None
