"""Tests for OLD users viewing enrollments in their classes."""

from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import auth as auth_module
from app.core import database as db_module
from app.core.database import Base, get_db
from app.main import app
from app.models import class_ as class_model  # noqa: F401
from app.models import enrollment as enrollment_model  # noqa: F401
from app.models.class_ import OneDayClass
from app.models.enrollment import Enrollment
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


async def create_user(
    session_maker, name: str, email: str | None, user_type: UserType
) -> UUID:
    """테스트용 사용자 생성. email 없이도 UUID 반환."""
    async with session_maker() as session:
        user = User(name=name, email=email, type=user_type)
        session.add(user)
        await session.flush()
        await session.refresh(user)
        user_id = user.id
        await session.commit()
        return user_id


async def create_class_for_user(
    session_maker, creator_id: UUID, category: str, location: str
) -> OneDayClass:
    """특정 사용자의 클래스 생성. creator_id (UUID)를 받음."""
    async with session_maker() as session:
        cls = OneDayClass(
            creator_id=creator_id,
            category=category,
            location=location,
            duration_minutes=60,
            capacity=10,
            years_of_experience="5y",
            job_description="Instructor",
            materials="Basic materials",
            price_per_person="$30",
            template={
                "template": "Class template",
                "클래스 소개": "클래스 소개",
                "난이도": "초급",
                "로드맵": "체험 운영, 관광 상품화로 확장",
            },
        )
        session.add(cls)
        await session.commit()
        await session.refresh(cls)
        return cls


async def enroll_user_to_class(
    session_maker, user_id: UUID, class_id, applied_date: str, headcount: int
) -> Enrollment:
    """사용자를 클래스에 등록. user_id (UUID)를 받음."""
    async with session_maker() as session:
        enrollment = Enrollment(
            class_id=class_id,
            user_id=user_id,
            applied_date=applied_date,
            headcount=headcount,
        )
        session.add(enrollment)
        await session.commit()
        await session.refresh(enrollment)
        return enrollment


@pytest.mark.anyio
async def test_old_user_can_view_their_class_enrollments(client: AsyncClient, session_maker):
    """OLD 사용자가 자신의 클래스 신청자 목록 조회 성공."""
    # OLD 사용자 생성
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    # YOUNG 사용자 2명 생성
    young1_id = await create_user(session_maker, "Young1", "young1@example.com", UserType.YOUNG)
    young2_id = await create_user(session_maker, "Young2", "young2@example.com", UserType.YOUNG)

    # OLD 사용자가 2개의 클래스 생성
    class1 = await create_class_for_user(
        session_maker, old_user_id, "cooking", "Seoul"
    )
    class2 = await create_class_for_user(
        session_maker, old_user_id, "painting", "Busan"
    )

    # 각 클래스에 YOUNG 사용자들이 신청
    await enroll_user_to_class(session_maker, young1_id, class1.id, "2025-12-19", 2)
    await enroll_user_to_class(session_maker, young2_id, class1.id, "2025-12-19", 1)
    await enroll_user_to_class(session_maker, young1_id, class2.id, "2025-12-18", 3)

    # OLD 사용자로 엔드포인트 호출
    res = await client.get(
        "/api/v1/classes/my-classes/enrollments",
        headers={"wadeulwadeul-user": str(old_user_id)},
    )

    # 검증
    assert res.status_code == 200
    data = res.json()

    # 2개의 클래스 정보가 반환되는지 확인
    assert len(data) == 2

    # 각 클래스에 신청자 정보가 포함되어 있는지 확인
    class_ids = {item["class_id"] for item in data}
    assert str(class1.id) in class_ids
    assert str(class2.id) in class_ids

    # 첫 번째 클래스 검증 (cooking - 2명 신청)
    cooking_class = next(item for item in data if item["class_info"]["category"] == "cooking")
    assert cooking_class["class_info"]["location"] == "Seoul"
    assert len(cooking_class["enrollments"]) == 2

    # 신청자 정보 검증
    enrollments = cooking_class["enrollments"]
    user_names = {e["user_info"]["name"] for e in enrollments}
    assert "Young1" in user_names
    assert "Young2" in user_names

    # 두 번째 클래스 검증 (painting - 1명 신청)
    painting_class = next(item for item in data if item["class_info"]["category"] == "painting")
    assert painting_class["class_info"]["location"] == "Busan"
    assert len(painting_class["enrollments"]) == 1
    assert painting_class["enrollments"][0]["user_info"]["name"] == "Young1"
    assert painting_class["enrollments"][0]["headcount"] == 3


@pytest.mark.anyio
async def test_old_user_sees_null_email_when_missing(client: AsyncClient, session_maker):
    """email 없이 신청한 사용자의 email 필드는 null 로 반환."""
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)
    young_user_id = await create_user(session_maker, "Young User", None, UserType.YOUNG)

    clazz = await create_class_for_user(session_maker, old_user_id, "cooking", "Seoul")
    await enroll_user_to_class(session_maker, young_user_id, clazz.id, "2025-12-19", 1)

    res = await client.get(
        "/api/v1/classes/my-classes/enrollments",
        headers={"wadeulwadeul-user": str(old_user_id)},
    )

    assert res.status_code == 200
    data = res.json()
    assert data[0]["enrollments"][0]["user_info"]["email"] is None


@pytest.mark.anyio
async def test_young_user_cannot_access_endpoint(client: AsyncClient, session_maker):
    """YOUNG 사용자는 접근 불가."""
    young_user_id = await create_user(session_maker, "Young", "young@example.com", UserType.YOUNG)

    res = await client.get(
        "/api/v1/classes/my-classes/enrollments",
        headers={"wadeulwadeul-user": str(young_user_id)},
    )

    assert res.status_code == 403
    assert "Only OLD users" in res.json()["detail"]


@pytest.mark.anyio
async def test_unauthenticated_user_cannot_access(client: AsyncClient):
    """인증되지 않은 사용자는 접근 불가."""
    res = await client.get("/api/v1/classes/my-classes/enrollments")

    assert res.status_code == 401


@pytest.mark.anyio
async def test_old_user_sees_classes_with_no_enrollments(client: AsyncClient, session_maker):
    """신청자가 없는 클래스도 반환."""
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    # 클래스 생성하지만 아무도 신청하지 않음
    await create_class_for_user(session_maker, old_user_id, "pottery", "Incheon")

    res = await client.get(
        "/api/v1/classes/my-classes/enrollments",
        headers={"wadeulwadeul-user": str(old_user_id)},
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["class_info"]["category"] == "pottery"
    assert data[0]["enrollments"] == []


@pytest.mark.anyio
async def test_old_user_only_sees_their_own_classes(client: AsyncClient, session_maker):
    """다른 OLD 사용자의 클래스는 반환하지 않음."""
    # OLD 사용자 2명 생성
    old1_id = await create_user(session_maker, "Old1", "old1@example.com", UserType.OLD)
    old2_id = await create_user(session_maker, "Old2", "old2@example.com", UserType.OLD)
    young_id = await create_user(session_maker, "Young", "young@example.com", UserType.YOUNG)

    # old1이 클래스 생성
    class1 = await create_class_for_user(session_maker, old1_id, "yoga", "Seoul")
    # old2가 클래스 생성
    await create_class_for_user(session_maker, old2_id, "pilates", "Busan")

    # YOUNG이 old1의 클래스에 신청
    await enroll_user_to_class(session_maker, young_id, class1.id, "2025-12-19", 1)

    # old1로 조회
    res = await client.get(
        "/api/v1/classes/my-classes/enrollments",
        headers={"wadeulwadeul-user": str(old1_id)},
    )

    assert res.status_code == 200
    data = res.json()

    # old1의 클래스만 반환되어야 함
    assert len(data) == 1
    assert data[0]["class_info"]["category"] == "yoga"
    assert len(data[0]["enrollments"]) == 1
