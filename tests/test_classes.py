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
        "duration_minutes": 90,
        "capacity": 10,
        "years_of_experience": "5y",
        "job_description": "Cooking expert",
        "materials": "Apron, pan",
        "price_per_person": "$30",
        "template": {
            "template": "Cooking class template",
            "클래스 소개": "쿠킹 클래스 소개",
            "난이도": "초급",
            "로드맵": "심화 요리와 케이터링까지 확장",
        },
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
        # "years_of_experience" missing
        "category": "music",
        "location": "Seoul, Korea",
        "duration_minutes": 90,
        "capacity": 10,
        "job_description": "Performer",
        "materials": "Microphone",
        "price_per_person": "$100",
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
        "duration_minutes": 120,
        "capacity": 8,
        "years_of_experience": "10y",
        "job_description": "Professional guitarist",
        "materials": "Guitar strings, picks",
        "price_per_person": "$50",
        "template": {
            "template": "Full class template content",
            "클래스 소개": "음악 클래스 소개",
            "난이도": "초급",
            "로드맵": "버스킹과 공연 기획까지 확장",
        },
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
    assert data["years_of_experience"] == payload["years_of_experience"]
    assert data["job_description"] == payload["job_description"]
    assert data["materials"] == payload["materials"]
    assert data["price_per_person"] == payload["price_per_person"]
    assert data["template"] == payload["template"]

    class_id = UUID(data["id"])

    async with session_maker() as session:
        result = await session.execute(
            select(OneDayClass).where(OneDayClass.id == class_id)
        )
        row = result.scalar_one_or_none()

    assert row is not None
    assert row.category == payload["category"]
    assert row.location == payload["location"]
    assert row.duration_minutes == payload["duration_minutes"]
    assert row.capacity == payload["capacity"]
    assert row.years_of_experience == payload["years_of_experience"]
    assert row.job_description == payload["job_description"]
    assert row.materials == payload["materials"]
    assert row.price_per_person == payload["price_per_person"]
    assert row.template == payload["template"]


@pytest.mark.anyio
async def test_get_class_by_id(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    payload = {
        "category": "baking",
        "location": "Daegu, Korea",
        "duration_minutes": 60,
        "capacity": 12,
        "years_of_experience": "8y",
        "job_description": "Baker",
        "materials": "Flour, sugar",
        "price_per_person": "$20",
        "template": None,
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
            "duration_minutes": 60,
            "capacity": 5,
            "years_of_experience": "3y",
            "job_description": "Artist",
            "materials": "Paint, brush",
            "price_per_person": "$15",
            "template": None,
        },
        {
            "category": "cook",
            "location": "Busan",
            "duration_minutes": 90,
            "capacity": 10,
            "years_of_experience": "6y",
            "job_description": "Chef",
            "materials": "Knife",
            "price_per_person": "$25",
            "template": {
                "template": "Cooking outline",
                "클래스 소개": "쿠킹 아웃라인",
                "난이도": "초급",
                "로드맵": "홈파티 요리까지 확장",
            },
        },
    ]

    created_class_ids = []
    for payload in payloads:
        res = await client.post(
            "/api/v1/classes",
            json=payload,
            headers={"wadeulwadeul-user": str(old_user_id)},
        )
        assert res.status_code == 201
        created_class_ids.append(res.json()["id"])

    res = await client.get(
        "/api/v1/classes?skip=0&limit=10",
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2

    # 최신순 정렬 검증: 두 번째 생성된 클래스(cook)가 첫 번째에 와야 함
    assert data[0]["id"] == created_class_ids[1], "최신 클래스가 첫 번째에 있어야 함"
    assert data[0]["category"] == "cook"
    assert data[1]["id"] == created_class_ids[0], "이전 클래스가 두 번째에 있어야 함"
    assert data[1]["category"] == "art"


@pytest.mark.anyio
async def test_public_list_classes_with_pagination(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)

    created_class_ids = []
    for idx in range(3):
        payload = {
            "category": f"cat-{idx}",
            "location": f"loc-{idx}",
            "duration_minutes": 30 + idx,
            "capacity": 5 + idx,
            "years_of_experience": f"{idx + 1}y",
            "job_description": f"Job-{idx}",
            "materials": f"Materials-{idx}",
            "price_per_person": f"${10 + idx}",
            "template": None,
        }
        res = await client.post(
            "/api/v1/classes",
            json=payload,
            headers={"wadeulwadeul-user": str(old_user_id)},
        )
        assert res.status_code == 201
        created_class_ids.append(res.json()["id"])

    # no auth header, pagination
    res = await client.get("/api/v1/classes/public?skip=0&limit=2")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2

    # 최신순 정렬 검증: 가장 최근 생성된 클래스들이 먼저 와야 함
    assert data[0]["id"] == created_class_ids[2], "가장 최신 클래스가 첫 번째에 있어야 함"
    assert data[0]["category"] == "cat-2"
    assert data[1]["id"] == created_class_ids[1], "두 번째로 최신 클래스가 두 번째에 있어야 함"
    assert data[1]["category"] == "cat-1"

    res_next = await client.get("/api/v1/classes/public?skip=2&limit=2")
    assert res_next.status_code == 200
    data_next = res_next.json()
    assert len(data_next) == 1

    # 페이지네이션 검증: 세 번째(가장 오래된) 클래스가 마지막 페이지에 있어야 함
    assert data_next[0]["id"] == created_class_ids[0], "가장 오래된 클래스가 마지막에 있어야 함"
    assert data_next[0]["category"] == "cat-0"


@pytest.mark.anyio
async def test_update_class_by_creator(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)
    young_user_id = await create_user(session_maker, "Young User", "young@example.com", UserType.YOUNG)

    payload = {
        "category": "dance",
        "location": "Seoul",
        "duration_minutes": 45,
        "capacity": 6,
        "years_of_experience": "4y",
        "job_description": "Dancer",
        "materials": "Shoes",
        "price_per_person": "$35",
        "template": None,
    }

    create_res = await client.post(
        "/api/v1/classes",
        json=payload,
        headers={"wadeulwadeul-user": str(old_user_id)},
    )
    assert create_res.status_code == 201
    class_id = create_res.json()["id"]

    update_payload = {
        "category": "dance-updated",
        "capacity": 7,
        "materials": "Shoes, water",
        "template": {
            "template": "Updated template",
            "클래스 소개": "업데이트된 소개",
            "난이도": "초급",
            "로드맵": "댄스 심화와 공연 기획까지 확장",
        },
    }

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
    assert data["materials"] == "Shoes, water"
    assert data["template"] == {
        "template": "Updated template",
        "클래스 소개": "업데이트된 소개",
        "난이도": "초급",
        "로드맵": "댄스 심화와 공연 기획까지 확장",
    }


@pytest.mark.anyio
async def test_delete_class_by_creator(client: AsyncClient, session_maker):
    old_user_id = await create_user(session_maker, "Old User", "old@example.com", UserType.OLD)
    young_user_id = await create_user(session_maker, "Young User", "young@example.com", UserType.YOUNG)

    payload = {
        "category": "craft",
        "location": "Incheon",
        "duration_minutes": 80,
        "capacity": 9,
        "years_of_experience": "7y",
        "job_description": "Crafter",
        "materials": "Wood, glue",
        "price_per_person": "$40",
        "template": {
            "template": "Craft template",
            "클래스 소개": "공예 클래스 소개",
            "난이도": "초급",
            "로드맵": "소품 제작과 판매까지 확장",
        },
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
