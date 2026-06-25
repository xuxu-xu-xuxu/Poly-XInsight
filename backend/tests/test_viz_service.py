from backend.services.viz_service import VIZ_PROMPT


def test_viz_prompt_has_required_fields():
    assert "{query}" in VIZ_PROMPT
    assert "{available_types}" in VIZ_PROMPT
    assert "chart_type" in VIZ_PROMPT
    assert "echarts_option" in VIZ_PROMPT
    assert "sql" in VIZ_PROMPT
