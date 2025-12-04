import re
from pathlib import Path


def test_init_sql_has_updated_class_columns():
    init_sql = Path("database/postgres/base/init.sql").read_text()
    for field in ["years_of_experience", "job_description", "materials", "price_per_person", "template JSONB"]:
        assert field in init_sql
    assert "start_time" not in init_sql
    assert "notes" not in init_sql


def test_seed_sql_matches_new_class_columns():
    seed_sql = Path("database/postgres/base/seed_test_data.sql").read_text()
    for field in ["years_of_experience", "job_description", "materials", "price_per_person", "template"]:
        assert field in seed_sql
    assert "start_time" not in seed_sql
    assert "notes" not in seed_sql


def test_seed_sql_contains_korean_and_core_ids_with_enough_classes():
    seed_sql = Path("database/postgres/base/seed_test_data.sql").read_text()
    assert "550e8400-e29b-41d4-a716-446655440002" in seed_sql  # OLD_USER_ID core
    assert "550e8400-e29b-41d4-a716-446655440011" in seed_sql  # YOUNG_USER_ID core
    assert re.search(r"[가-힣]", seed_sql), "Seed 데이터에 한글이 포함되어야 합니다."
    classes_section = seed_sql.split("-- Enrollments", maxsplit=1)[0]
    class_ids = re.findall(r"'650e8400-e29b-41d4-a716-4466554400[0-9]+'", classes_section)
    class_count = len(set(class_ids))
    assert class_count >= 10, "클래스 초기 데이터가 충분히 다양해야 합니다."
