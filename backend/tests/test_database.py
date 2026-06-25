import pytest
from sqlalchemy import inspect

from backend.models.database import Base, Paper, Entity


def test_paper_model_exists():
    mapper = inspect(Paper)
    assert mapper.tables[0].name == "papers"
    assert "title" in mapper.columns
    assert "full_text" in mapper.columns


def test_entity_model_jsonb():
    mapper = inspect(Entity)
    assert "attributes" in mapper.columns
    assert "entity_type" in mapper.columns
