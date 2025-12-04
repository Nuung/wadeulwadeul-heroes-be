from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import auth as auth_module
from app.core import database as db_module
from app.core.database import Base, get_db
from app.main import app
from app.models import class_ as class_model  # noqa: F401  # 모델 등록을 위한 임포트
from app.models.class_ import OneDayClass
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

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


async def create_user(session_maker, name: str, email: str, user_type: UserType) -> UUID:
    """테스트용 사용자 생성. UUID를 반환."""
    async with session_maker() as session:
        user = User(name=name, email=email, type=user_type)
        session.add(user)
        await session.flush()
        await session.refresh(user)
        user_id = user.id
        await session.commit()
        return user_id


@pytest.mark.anyio
async def test_only_old_user_can_create_class(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)
    young_user_id = await create_user(session_maker, "Young User", "young@example.com", UserType.YOUNG)

    payload = {
        "category": "cooking",
        "location": "Seoul, Korea",
        "start_time": "2025-12-04T12:00:00Z",
        "duration_minutes": 90,
        "capacity": 10,
        "notes": "Bring your own apron",
    }

    # Young 사용자: 권한 없음
    res = await client.post(
        "/api/v1/classes",
        json=payload,
        headers={"wadeulwadeul-user": str(young_user_id)},
    )
    assert res.status_code == 403

    # Old 사용자: 생성 가능
    res = await client.post(
        "/api/v1/classes",
        json=payload,
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert res.status_code == 201


@pytest.mark.anyio
async def test_create_class_requires_fields(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    payload = {
        # "category" missing
        "location": "Seoul, Korea",
        "start_time": "2025-12-04T12:00:00Z",
        "duration_minutes": 90,
        "capacity": 10,
    }

    res = await client.post(
        "/api/v1/classes",
        json=payload,
        headers={"wadeulwadeul-user": str(old_user_id)},
    )

    assert res.status_code == 422


@pytest.mark.anyio
async def test_create_class_persists_and_returned(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    payload = {
        "category": "music",
        "location": "Busan, Korea",
        "start_time": "2025-12-05 ~ 2025-12-06",
        "duration_minutes": 120,
        "capacity": 8,
        "notes": "Bring your instrument",
    }

    res = await client.post(
        "/api/v1/classes",
        json=payload,
        headers={"wadeulwadeul-user": str(old_user_id)},
    )

    assert res.status_code == 201
    data = res.json()
    assert data["category"] == payload["category"]
    assert data["location"] == payload["location"]

    class_id = UUID(data["id"])

    async with session_maker() as session:
        result = await session.execute(
            select(OneDayClass).where(OneDayClass.id == class_id)
        )
        row = result.scalar_one_or_none()

    assert row is not None
    assert row.category == payload["category"]


@pytest.mark.anyio
async def test_get_class_by_id(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    payload = {
        "category": "baking",
        "location": "Daegu, Korea",
        "start_time": "2025-12-06 ~ 2025-12-07",
        "duration_minutes": 60,
        "capacity": 12,
        "notes": "Ingredients provided",
    }

    create_res = await client.post(
        "/api/v1/classes",
        json=payload,
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert create_res.status_code == 201
    class_id = create_res.json()["id"]

    get_res = await client.get(
        f"/api/v1/classes/{class_id}",
        headers={"wadeulwadeul-user": str(old_user_id)},
    )

    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == class_id
    assert data["category"] == payload["category"]


@pytest.mark.anyio
async def test_list_classes(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    payloads = [
        {
            "category": "art",
            "location": "Seoul",
            "start_time": "2025-12-10",
            "duration_minutes": 60,
            "capacity": 5,
            "notes": None,
        },
        {
            "category": "cook",
            "location": "Busan",
            "start_time": "2025-12-11",
            "duration_minutes": 90,
            "capacity": 10,
            "notes": "Apron",
        },
    ]

    for payload in payloads:
        res = await client.post(
            "/api/v1/classes",
            json=payload,
            headers={"wadeulwadeul-user": str(old_user_id)},
        )
        assert res.status_code == 201

    res = await client.get(
        "/api/v1/classes?skip=0&limit=10",
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_public_list_classes_with_pagination(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    for idx in range(3):
        payload = {
            "category": f"cat-{idx}",
            "location": f"loc-{idx}",
            "start_time": "2025-12-15T10:00:00Z",
            "duration_minutes": 30 + idx,
            "capacity": 5 + idx,
            "notes": None,
        }
        res = await client.post(
            "/api/v1/classes",
            json=payload,
            headers={"wadeulwadeul-user": str(old_user_id)},
        )
        assert res.status_code == 201

    # no auth header, pagination
    res = await client.get("/api/v1/classes/public?skip=0&limit=2")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2

    res_next = await client.get("/api/v1/classes/public?skip=2&limit=2")
    assert res_next.status_code == 200
    data_next = res_next.json()
    assert len(data_next) == 1


@pytest.mark.anyio
async def test_update_class_by_creator(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)
    young_user_id = await create_user(session_maker, "Young User", "young@example.com", UserType.YOUNG)

    payload = {
        "category": "dance",
        "location": "Seoul",
        "start_time": "2025-12-12",
        "duration_minutes": 45,
        "capacity": 6,
        "notes": None,
    }

    create_res = await client.post(
        "/api/v1/classes",
        json=payload,
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert create_res.status_code == 201
    class_id = create_res.json()["id"]

    update_payload = {"category": "dance-updated", "capacity": 7, "start_time": "2025-12-12 ~ 2025-12-13"}

    # Young 사용자: 수정 불가
    res = await client.put(
        f"/api/v1/classes/{class_id}",
        json=update_payload,
        headers={"wadeulwadeul-user": str(young_user_id)},
    )
    assert res.status_code == 403

    # Creator(OLD): 수정 가능
    res = await client.put(
        f"/api/v1/classes/{class_id}",
        json=update_payload,
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "dance-updated"
    assert data["capacity"] == 7


@pytest.mark.anyio
async def test_delete_class_by_creator(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)
    young_user_id = await create_user(session_maker, "Young User", "young@example.com", UserType.YOUNG)

    payload = {
        "category": "craft",
        "location": "Incheon",
        "start_time": "2025-12-13",
        "duration_minutes": 80,
        "capacity": 9,
        "notes": "Materials included",
    }

    create_res = await client.post(
        "/api/v1/classes",
        json=payload,
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert create_res.status_code == 201
    class_id = create_res.json()["id"]

    # Young 사용자: 삭제 불가
    res = await client.delete(
        f"/api/v1/classes/{class_id}",
        headers={"wadeulwadeul-user": str(young_user_id)},
    )
    assert res.status_code == 403

    # Creator(OLD): 삭제 가능
    res = await client.delete(
        f"/api/v1/classes/{class_id}",
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert res.status_code == 204

    # 이후 조회 시 404
    res = await client.get(
        f"/api/v1/classes/{class_id}",
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert res.status_code == 404
