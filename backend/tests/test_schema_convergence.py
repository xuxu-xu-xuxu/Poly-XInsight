from backend.services.schema_convergence import CONVERGENCE_PROMPT


def test_convergence_prompt_has_placeholders():
    assert "{type_list}" in CONVERGENCE_PROMPT
    assert "canonical" in CONVERGENCE_PROMPT.lower()


def test_empty_schema_no_mappings():
    prompt = CONVERGENCE_PROMPT.format(type_list='["抗拉强度"]')
    assert "抗拉强度" in prompt
