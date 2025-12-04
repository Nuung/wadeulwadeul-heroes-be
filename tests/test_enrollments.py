import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import auth as auth_module
from app.core import database as db_module
from app.core.database import Base, get_db
from app.main import app
from app.models import class_ as class_model  # noqa: F401
from app.models import enrollment as enrollment_model  # noqa: F401
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


async def create_user(session_maker, name: str, email: str, user_type: UserType) -> None:
    """테스트용 사용자 생성."""
    async with session_maker() as session:
        user = User(name=name, email=email, type=user_type)
        session.add(user)
        await session.commit()


async def create_class(session_maker, creator_email: str, creator_type: UserType) -> OneDayClass:
    """테스트용 클래스 생성."""
    await create_user(session_maker, "Creator", creator_email, creator_type)
    async with session_maker() as session:
        user = await session.execute(select(User).where(User.email == creator_email))
        user = user.scalar_one()
        cls = OneDayClass(
            creator_id=user.id,
            category="cat",
            location="loc",
            start_time="2025-12-20 ~ 2025-12-21",
            duration_minutes=60,
            capacity=10,
            notes=None,
        )
        session.add(cls)
        await session.commit()
        await session.refresh(cls)
        return cls


@pytest.mark.anyio
async def test_only_young_can_enroll(client: AsyncClient, session_maker):
    clazz = await create_class(session_maker, "old@example.com", UserType.OLD)
    await create_user(session_maker, "Young", "young@example.com", UserType.YOUNG)
    await create_user(session_maker, "OldUser", "olduser@example.com", UserType.OLD)

    payload = {"applied_date": "2025-12-19", "headcount": 2}

    # Old 사용자: 거부
    res = await client.post(
        f"/api/v1/classes/{clazz.id}/enroll",
        json=payload,
        headers={"wadeulwadeul-user": "olduser@example.com"},
    )
    assert res.status_code == 403

    # Young 사용자: 허용
    res = await client.post(
        f"/api/v1/classes/{clazz.id}/enroll",
        json=payload,
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res.status_code == 201


@pytest.mark.anyio
async def test_list_my_enrollments(client: AsyncClient, session_maker):
    clazz = await create_class(session_maker, "old@example.com", UserType.OLD)
    await create_user(session_maker, "Young", "young@example.com", UserType.YOUNG)

    payload = {"applied_date": "2025-12-19", "headcount": 1}
    res = await client.post(
        f"/api/v1/classes/{clazz.id}/enroll",
        json=payload,
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res.status_code == 201

    res = await client.get(
        "/api/v1/classes/enrollments/me",
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["class_id"] == str(clazz.id)


@pytest.mark.anyio
async def test_enroll_requires_fields(client: AsyncClient, session_maker):
    clazz = await create_class(session_maker, "old@example.com", UserType.OLD)
    await create_user(session_maker, "Young", "young@example.com", UserType.YOUNG)

    payload = {"headcount": 2}  # applied_date missing
    res = await client.post(
        f"/api/v1/classes/{clazz.id}/enroll",
        json=payload,
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res.status_code == 422


@pytest.mark.anyio
async def test_duplicate_enroll_blocked(client: AsyncClient, session_maker):
    clazz = await create_class(session_maker, "old@example.com", UserType.OLD)
    await create_user(session_maker, "Young", "young@example.com", UserType.YOUNG)

    payload = {"applied_date": "2025-12-19", "headcount": 1}
    res = await client.post(
        f"/api/v1/classes/{clazz.id}/enroll",
        json=payload,
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res.status_code == 201

    res_dup = await client.post(
        f"/api/v1/classes/{clazz.id}/enroll",
        json=payload,
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res_dup.status_code == 400


@pytest.mark.anyio
async def test_delete_enrollment(client: AsyncClient, session_maker):
    clazz = await create_class(session_maker, "old@example.com", UserType.OLD)
    await create_user(session_maker, "Young", "young@example.com", UserType.YOUNG)
    await create_user(session_maker, "Other", "other@example.com", UserType.YOUNG)

    payload = {"applied_date": "2025-12-19", "headcount": 1}
    res = await client.post(
        f"/api/v1/classes/{clazz.id}/enroll",
        json=payload,
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res.status_code == 201
    enrollment_id = res.json()["id"]

    # 다른 사용자 삭제 불가
    res_forbidden = await client.delete(
        f"/api/v1/classes/enrollments/{enrollment_id}",
        headers={"wadeulwadeul-user": "other@example.com"},
    )
    assert res_forbidden.status_code == 403

    # 본인 삭제 가능
    res_delete = await client.delete(
        f"/api/v1/classes/enrollments/{enrollment_id}",
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res_delete.status_code == 204

    # 삭제 후 목록 비어 있음
    res_list = await client.get(
        "/api/v1/classes/enrollments/me",
        headers={"wadeulwadeul-user": "young@example.com"},
    )
    assert res_list.status_code == 200
    assert res_list.json() == []
