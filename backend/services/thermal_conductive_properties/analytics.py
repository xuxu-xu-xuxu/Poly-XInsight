from statistics import median

from sqlalchemy import select

from backend.models.database import ThermalConductiveProperty, get_db


# ─── Helpers ──────────────────────────────────────────────────────────

def _record_to_dict(record: ThermalConductiveProperty) -> dict:
    return {
        "id": record.id,
        "paper_id": record.paper_id,
        "filler_name": record.filler_name,
        "filler_type": record.filler_type,
        "matrix_name": record.matrix_name,
        "filler_content": record.filler_content,
        "filler_content_unit": record.filler_content_unit,
        "particle_size": record.particle_size,
        "surface_treatment": record.surface_treatment,
        "property_category": record.property_category,
        "property_name": record.property_name,
        "value": record.value,
        "value_min": record.value_min,
        "value_max": record.value_max,
        "unit": record.unit,
        "temperature_value": record.temperature_value,
        "temperature_unit": record.temperature_unit,
        "frequency": record.frequency,
        "method": record.method,
        "condition_text": record.condition_text,
        "evidence_text": record.evidence_text,
        "source_chunk_id": record.source_chunk_id,
        "confidence": record.confidence,
        "status": record.status,
    }


async def _fetch_records(
    category: str | None = None,
    property_name: str | None = None,
    confidence_min: float = 0.0,
    status: str | None = None,
) -> list[ThermalConductiveProperty]:
    async for db in get_db():
        query = select(ThermalConductiveProperty).where(
            ThermalConductiveProperty.confidence >= confidence_min
        )
        if category:
            query = query.where(ThermalConductiveProperty.property_category == category)
        if property_name:
            query = query.where(ThermalConductiveProperty.property_name == property_name)
        if status:
            query = query.where(ThermalConductiveProperty.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())
    return []


def _material_label(record: ThermalConductiveProperty) -> str:
    filler = record.filler_name or "unknown"
    matrix = record.matrix_name or ""
    if matrix:
        return f"{filler}/{matrix}"
    return filler


def _bar_echarts(title: str, x_data: list[str], y_data: list[float], y_name: str, color: str = "#2563eb") -> dict:
    return {
        "chart_type": "bar",
        "title": title,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "18%", "containLabel": True},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data, "axisLabel": {"rotate": 45}},
            "yAxis": {"type": "value", "name": y_name},
            "series": [{"type": "bar", "data": y_data, "itemStyle": {"color": color}}],
        },
    }


def _pie_echarts(title: str, data: list[dict]) -> dict:
    return {
        "chart_type": "pie",
        "title": title,
        "echarts_option": {
            "tooltip": {"trigger": "item"},
            "series": [{
                "type": "pie",
                "radius": ["40%", "70%"],
                "data": data,
                "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowOffsetX": 0, "shadowColor": "rgba(0,0,0,0.5)"}},
            }],
        },
    }


def _scatter_echarts(title: str, items: list[dict], x_name: str, y_name: str) -> dict:
    return {
        "chart_type": "scatter",
        "title": title,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "12%", "containLabel": True},
            "tooltip": {"trigger": "item", "formatter": "{b}<br/>{c}"},
            "xAxis": {"type": "value", "name": x_name},
            "yAxis": {"type": "value", "name": y_name},
            "series": [{"type": "scatter", "data": items}],
        },
    }


# ─── Records endpoint ─────────────────────────────────────────────────

async def records_response(
    category: str | None = None,
    property_name: str | None = None,
    confidence_min: float = 0.0,
    status: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    records = await _fetch_records(category, property_name, confidence_min, status)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": [_record_to_dict(r) for r in records[start:end]],
        "total": len(records),
        "page": page,
        "page_size": page_size,
    }


# ─── Tab 1: 导热材料原料 ──────────────────────────────────────────────

async def filler_types(confidence_min: float = 0.0) -> dict:
    records = await _fetch_records(confidence_min=confidence_min)
    counts: dict[str, int] = {}
    for rec in records:
        ft = rec.filler_type or "unknown"
        counts[ft] = counts.get(ft, 0) + 1
    data = [{"name": k, "value": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
    return {
        **_pie_echarts("填料类型分布", data),
        "data": data,
    }


async def filler_frequency(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(confidence_min=confidence_min)
    counts: dict[str, int] = {}
    for rec in records:
        fn = rec.filler_name or "unknown"
        counts[fn] = counts.get(fn, 0) + 1
    sorted_items = sorted(counts.items(), key=lambda x: -x[1])[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"filler": k, "count": v} for k, v in sorted_items]
    return {
        **_bar_echarts("Top 填料出现频次", x_data, y_data, "出现次数", "#b91c1c"),
        "data": rows,
    }


async def filler_content_vs_conductivity(confidence_min: float = 0.0) -> dict:
    """Scatter plot: filler content vs thermal conductivity."""
    tc_records = await _fetch_records(property_name="thermal_conductivity", confidence_min=confidence_min)
    items = []
    for rec in tc_records:
        if rec.filler_content is not None and rec.value is not None:
            items.append({
                "name": _material_label(rec),
                "value": [rec.filler_content, rec.value],
            })
    return {
        **_scatter_echarts("填料含量 vs 导热率", items, "填料含量 (%)", "导热率 (W/(m·K))"),
        "data": items,
    }


# ─── Tab 2: 导热率/热阻 ──────────────────────────────────────────────

async def conductivity_by_filler(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(property_name="thermal_conductivity", confidence_min=confidence_min)
    grouped: dict[str, list[float]] = {}
    for rec in records:
        if rec.value is not None and rec.value > 0 and rec.value <= 5000:
            grouped.setdefault(rec.filler_name or "unknown", []).append(rec.value)
    sorted_items = sorted(
        [(k, sum(v) / len(v), len(v)) for k, v in grouped.items() if v],
        key=lambda x: -x[1],
    )[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"filler": item[0], "avg_conductivity": item[1], "count": item[2]} for item in sorted_items]
    return {
        **_bar_echarts("不同填料导热率对比", x_data, y_data, "平均导热率 W/(m·K)", "#059669"),
        "data": rows,
    }


async def conductivity_by_matrix(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(property_name="thermal_conductivity", confidence_min=confidence_min)
    grouped: dict[str, list[float]] = {}
    for rec in records:
        if rec.value is not None and rec.value > 0 and rec.value <= 5000:
            grouped.setdefault(rec.matrix_name or "unknown", []).append(rec.value)
    sorted_items = sorted(
        [(k, sum(v) / len(v), len(v)) for k, v in grouped.items() if v],
        key=lambda x: -x[1],
    )[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"matrix": item[0], "avg_conductivity": item[1], "count": item[2]} for item in sorted_items]
    return {
        **_bar_echarts("不同基体导热率对比", x_data, y_data, "平均导热率 W/(m·K)", "#7c3aed"),
        "data": rows,
    }


async def conductivity_distribution(confidence_min: float = 0.0, bins: int = 15) -> dict:
    records = await _fetch_records(property_name="thermal_conductivity", confidence_min=confidence_min)
    values = [rec.value for rec in records if rec.value is not None and rec.value > 0 and rec.value <= 5000]
    if not values:
        return {"chart_type": "bar", "title": "导热率分布", "data": [], "echarts_option": {}}
    min_v, max_v = min(values), max(values)
    if min_v == max_v:
        return {"chart_type": "bar", "title": "导热率分布", "data": [], "echarts_option": {}}
    bin_width = (max_v - min_v) / bins
    bin_edges = [min_v + i * bin_width for i in range(bins + 1)]
    hist = [0] * bins
    for v in values:
        idx = min(int((v - min_v) / bin_width), bins - 1)
        hist[idx] += 1
    labels = [f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}" for i in range(bins)]
    return {
        **_bar_echarts("导热率分布 (W/(m·K))", labels, hist, "频次", "#059669"),
        "data": [{"range": labels[i], "count": hist[i]} for i in range(bins)],
    }


# ─── Tab 3: 流变模量/黏度 ────────────────────────────────────────────

async def viscosity_by_material(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(category="rheological", property_name="complex_viscosity", confidence_min=confidence_min)
    if not records:
        records = await _fetch_records(category="rheological", property_name="shear_viscosity", confidence_min=confidence_min)
    grouped: dict[str, list[float]] = {}
    for rec in records:
        if rec.value is not None and rec.value > 0:
            grouped.setdefault(_material_label(rec), []).append(rec.value)
    sorted_items = sorted(
        [(k, sum(v) / len(v), len(v)) for k, v in grouped.items() if v],
        key=lambda x: -x[1],
    )[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"material": item[0], "avg_viscosity": item[1], "count": item[2]} for item in sorted_items]
    return {
        **_bar_echarts("复合黏度对比 (Pa·s)", x_data, y_data, "黏度 (Pa·s)", "#d97706"),
        "data": rows,
    }


async def storage_modulus_by_material(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(category="rheological", property_name="storage_modulus", confidence_min=confidence_min)
    grouped: dict[str, list[float]] = {}
    for rec in records:
        if rec.value is not None and rec.value > 0:
            grouped.setdefault(_material_label(rec), []).append(rec.value)
    sorted_items = sorted(
        [(k, sum(v) / len(v), len(v)) for k, v in grouped.items() if v],
        key=lambda x: -x[1],
    )[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"material": item[0], "avg_storage_modulus": item[1], "count": item[2]} for item in sorted_items]
    return {
        **_bar_echarts("储能模量 G' 对比 (Pa)", x_data, y_data, "G' (Pa)", "#dc2626"),
        "data": rows,
    }


async def tan_delta_by_material(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(category="rheological", property_name="tan_delta", confidence_min=confidence_min)
    grouped: dict[str, list[float]] = {}
    for rec in records:
        if rec.value is not None and rec.value > 0:
            grouped.setdefault(_material_label(rec), []).append(rec.value)
    sorted_items = sorted(
        [(k, sum(v) / len(v), len(v)) for k, v in grouped.items() if v],
        key=lambda x: -x[1],
    )[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"material": item[0], "avg_tan_delta": item[1], "count": item[2]} for item in sorted_items]
    return {
        **_bar_echarts("Tan δ 对比", x_data, y_data, "tan δ", "#ea580c"),
        "data": rows,
    }


# ─── Tab 4: 力学性质 ─────────────────────────────────────────────────

async def tensile_strength_by_material(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(category="mechanical", property_name="tensile_strength", confidence_min=confidence_min)
    grouped: dict[str, list[float]] = {}
    for rec in records:
        if rec.value is not None and rec.value > 0:
            grouped.setdefault(_material_label(rec), []).append(rec.value)
    sorted_items = sorted(
        [(k, sum(v) / len(v), len(v)) for k, v in grouped.items() if v],
        key=lambda x: -x[1],
    )[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"material": item[0], "avg_tensile_strength": item[1], "count": item[2]} for item in sorted_items]
    return {
        **_bar_echarts("拉伸强度对比 (MPa)", x_data, y_data, "拉伸强度 (MPa)", "#2563eb"),
        "data": rows,
    }


async def youngs_modulus_by_material(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(category="mechanical", property_name="youngs_modulus", confidence_min=confidence_min)
    grouped: dict[str, list[float]] = {}
    for rec in records:
        if rec.value is not None and rec.value > 0:
            grouped.setdefault(_material_label(rec), []).append(rec.value)
    sorted_items = sorted(
        [(k, sum(v) / len(v), len(v)) for k, v in grouped.items() if v],
        key=lambda x: -x[1],
    )[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"material": item[0], "avg_youngs_modulus": item[1], "count": item[2]} for item in sorted_items]
    return {
        **_bar_echarts("杨氏模量对比 (GPa)", x_data, y_data, "杨氏模量 (GPa)", "#0891b2"),
        "data": rows,
    }


async def impact_strength_by_material(confidence_min: float = 0.0, top_n: int = 20) -> dict:
    records = await _fetch_records(category="mechanical", property_name="impact_strength", confidence_min=confidence_min)
    grouped: dict[str, list[float]] = {}
    for rec in records:
        if rec.value is not None and rec.value > 0:
            grouped.setdefault(_material_label(rec), []).append(rec.value)
    sorted_items = sorted(
        [(k, sum(v) / len(v), len(v)) for k, v in grouped.items() if v],
        key=lambda x: -x[1],
    )[:top_n]
    x_data = [item[0] for item in sorted_items]
    y_data = [item[1] for item in sorted_items]
    rows = [{"material": item[0], "avg_impact_strength": item[1], "count": item[2]} for item in sorted_items]
    return {
        **_bar_echarts("冲击强度对比 (kJ/m²)", x_data, y_data, "冲击强度 (kJ/m²)", "#4f46e5"),
        "data": rows,
    }
