from pathlib import Path


def test_init_sql_has_updated_class_columns():
    init_sql = Path("database/postgres/base/init.sql").read_text()
    for field in ["years_of_experience", "job_description", "materials", "price_per_person", "template"]:
        assert field in init_sql
    assert "start_time" not in init_sql
    assert "notes" not in init_sql


def test_seed_sql_matches_new_class_columns():
    seed_sql = Path("database/postgres/base/seed_test_data.sql").read_text()
    for field in ["years_of_experience", "job_description", "materials", "price_per_person", "template"]:
        assert field in seed_sql
    assert "start_time" not in seed_sql
    assert "notes" not in seed_sql
