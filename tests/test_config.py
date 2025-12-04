import pytest

from app.core.config import Settings


def test_production_without_db_host_raises():
    settings = Settings(environment="production", db_host="")

    with pytest.raises(ValueError):
        _ = settings.database_url
