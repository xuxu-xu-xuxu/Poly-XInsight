from backend.llm import get_llm_client
from backend.models.database import get_db
from sqlalchemy import text
import json
import re

VIZ_PROMPT = """你是数据可视化专家。根据用户需求生成图表。

用户需求: {query}

已知实体类型: {available_types}

entities表: paper_id TEXT, entity_type TEXT, attributes JSONB, source_span TEXT

SQL规则（必须严格遵守）:
- attributes是JSONB，用 attributes->>'key' 访问键值
- 数值比较: (attributes->>'field')::numeric
- 字符串比较: attributes->>'field' = 'value'
- 绝对不要使用 ? 或 ?| 或 ?& 操作符
- 结果集第一列为分类/标签列，后续列为数值列
- 散点图需要至少两列数值（x, y）

输出纯JSON（不要markdown包裹）:
{{
  "sql": "SELECT ... FROM entities WHERE ...",
  "chart_type": "bar|scatter|line|pie",
  "title": "图表标题",
  "explanation": "图表说明"
}}
"""


async def generate_chart(query: str) -> dict:
    """Generate a chart from a natural language query."""
    # Fetch available entity types
    async for db in get_db():
        try:
            types_result = await db.execute(
                text("SELECT DISTINCT entity_type FROM entities LIMIT 50")
            )
            available_types = [row[0] for row in types_result.fetchall()]
        except Exception:
            available_types = []
        break

    # Get LLM plan
    llm = get_llm_client()
    prompt = VIZ_PROMPT.format(
        query=query,
        available_types=json.dumps(available_types, ensure_ascii=False),
    )
    response = await llm.chat([{"role": "user", "content": prompt}])

    # Parse LLM response
    plan = _parse_llm_json(response)
    if not plan:
        raise ValueError("LLM 返回了无效的 JSON，请重试")

    sql = plan.get("sql", "")
    if not sql:
        raise ValueError("LLM 未生成 SQL 查询语句")

    # Execute SQL
    async for db in get_db():
        try:
            result = await db.execute(text(sql))
            columns = list(result.keys())
            raw_rows = result.fetchall()
            rows = [dict(zip(columns, row)) for row in raw_rows]
        except Exception as e:
            raise ValueError(f"SQL 执行失败: {e}")
        break

    # Build chart from data
    chart_type = plan.get("chart_type", "bar")
    title = plan.get("title", "可视化")
    explanation = plan.get("explanation", "")

    if not rows:
        return {
            "chart_type": chart_type,
            "title": title,
            "data": [],
            "echarts_option": {
                "title": {"text": "暂无数据", "left": "center", "top": "center",
                          "textStyle": {"color": "#9ca3af"}},
                "backgroundColor": "transparent",
            },
            "explanation": explanation or "查询未返回任何数据。",
        }

    option = _build_echarts_option(chart_type, title, rows, columns)

    return {
        "chart_type": chart_type,
        "title": title,
        "data": rows,
        "echarts_option": option,
        "explanation": explanation,
    }


# ── helpers ──────────────────────────────────────────────────────────


def _parse_llm_json(response: str) -> dict | None:
    """Robustly parse JSON from an LLM response string."""
    cleaned = response.strip()

    # Remove markdown code fences
    for prefix in ["```json", "```"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    for suffix in ["```"]:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)].strip()

    # Direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Regex fallback: extract first JSON object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _classify_columns(
    rows: list[dict], columns: list[str]
) -> tuple[list[str], list[str]]:
    """Split columns into categorical (string) and numeric groups."""
    cat_cols: list[str] = []
    num_cols: list[str] = []

    for col in columns:
        has_value = False
        all_numeric = True
        for row in rows[:30]:
            val = row.get(col)
            if val is None:
                continue
            has_value = True
            try:
                float(val)
            except (ValueError, TypeError):
                all_numeric = False
                break

        if not has_value:
            cat_cols.append(col)
        elif all_numeric:
            num_cols.append(col)
        else:
            cat_cols.append(col)

    return cat_cols, num_cols


def _build_echarts_option(
    chart_type: str, title: str, rows: list[dict], columns: list[str]
) -> dict:
    """Build a complete ECharts option from query results."""
    cat_cols, num_cols = _classify_columns(rows, columns)

    # If no numeric column found, try using first column as category with count
    if not num_cols:
        cat_col = cat_cols[0] if cat_cols else columns[0]
        return {
            "title": {"text": title, "left": "center",
                      "textStyle": {"color": "#374151", "fontSize": 14}},
            "backgroundColor": "transparent",
            "textStyle": {"color": "#374151"},
            "grid": {"left": "3%", "right": "7%", "bottom": "12%", "containLabel": True},
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "category",
                "data": [str(r[cat_col]) for r in rows],
                "axisLabel": {"color": "#6b7280"},
            },
            "yAxis": {"type": "value", "name": "count"},
            "series": [{
                "type": "bar",
                "data": [1] * len(rows),  # placeholder counts
                "itemStyle": {"color": "#2c5282"},
            }],
        }

    cat_col = cat_cols[0] if cat_cols else columns[0]
    categories = [str(r[cat_col]) for r in rows]

    option: dict = {
        "title": {"text": title, "left": "center",
                  "textStyle": {"color": "#374151", "fontSize": 14}},
        "backgroundColor": "transparent",
        "textStyle": {"color": "#374151"},
        "grid": {"left": "3%", "right": "7%", "bottom": "12%", "containLabel": True},
    }

    # ── scatter ──────────────────────────────────────────────────
    if chart_type == "scatter" and len(num_cols) >= 2:
        option["tooltip"] = {"trigger": "item", "formatter": "{b}"}
        option["xAxis"] = {
            "type": "value", "name": num_cols[0],
            "nameTextStyle": {"color": "#6b7280"},
        }
        option["yAxis"] = {
            "type": "value", "name": num_cols[1],
            "nameTextStyle": {"color": "#6b7280"},
            "scale": True,
        }
        option["series"] = [{
            "type": "scatter",
            "symbolSize": 8,
            "itemStyle": {"color": "#2c5282"},
            "data": [
                {
                    "name": str(r.get(cat_col, "")),
                    "value": [
                        _to_num(r.get(num_cols[0])),
                        _to_num(r.get(num_cols[1])),
                    ],
                }
                for r in rows
            ],
        }]
        return option

    # ── pie ──────────────────────────────────────────────────────
    if chart_type == "pie":
        val_col = num_cols[0]
        option["tooltip"] = {"trigger": "item", "formatter": "{b}: {c} ({d}%)"}
        option["series"] = [{
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["50%", "55%"],
            "label": {"color": "#6b7280", "formatter": "{b}: {d}%"},
            "data": [
                {"name": str(r[cat_col]), "value": _to_num(r[val_col])}
                for r in rows
            ],
        }]
        return option

    # ── bar / line (default) ─────────────────────────────────────
    option["tooltip"] = {"trigger": "axis"}
    option["xAxis"] = {
        "type": "category",
        "data": categories,
        "axisLabel": {
            "color": "#6b7280",
            "rotate": 45 if len(categories) > 6 else 0,
        },
    }
    option["yAxis"] = {
        "type": "value",
        "scale": True,
        "nameTextStyle": {"color": "#6b7280"},
    }

    COLORS = ["#2c5282", "#e53e3e", "#38a169", "#d69e2e", "#805ad5", "#3182ce", "#dd6b20"]
    use_color = len(num_cols) == 1  # only colour bars when single metric

    series_list = []
    for i, ncol in enumerate(num_cols[:6]):  # max 6 series
        s: dict = {
            "type": chart_type if chart_type in ("bar", "line") else "bar",
            "name": ncol,
            "data": [_to_num(r.get(ncol)) for r in rows],
        }
        if use_color:
            s["itemStyle"] = {"color": COLORS[i % len(COLORS)]}
        series_list.append(s)

    option["series"] = series_list
    return option


def _to_num(val) -> float:
    """Safely convert a value to float, defaulting to 0."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
