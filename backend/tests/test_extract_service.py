import json

from backend.services.extract_service import (
    SCHEMA_DISCOVERY_PROMPT,
    EXTRACT_INSTANCES_PROMPT,
    _clean_json_response,
)


def test_schema_prompt_has_required_sections():
    assert "{paper_text}" in SCHEMA_DISCOVERY_PROMPT
    assert "entities" in SCHEMA_DISCOVERY_PROMPT
    assert "relations" in SCHEMA_DISCOVERY_PROMPT


def test_extract_prompt_has_required_sections():
    assert "{schema_json}" in EXTRACT_INSTANCES_PROMPT
    assert "{paper_text}" in EXTRACT_INSTANCES_PROMPT
    assert "entity_type" in EXTRACT_INSTANCES_PROMPT
    assert "attributes" in EXTRACT_INSTANCES_PROMPT


def test_json_response_cleaning():
    raw = '```json\n{"key": "value"}\n```'
    cleaned = _clean_json_response(raw)
    assert json.loads(cleaned) == {"key": "value"}


def test_json_response_cleaning_no_fences():
    raw = '{"key": "value"}'
    cleaned = _clean_json_response(raw)
    assert json.loads(cleaned) == {"key": "value"}
