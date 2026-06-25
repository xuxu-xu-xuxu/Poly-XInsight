import re
from statistics import median

from sqlalchemy import select

from backend.models.database import SolidElectrolyteProperty, get_db
from backend.services.solid_electrolyte_properties.extractor import VALID_ELEMENTS


def _property_to_dict(record: SolidElectrolyteProperty) -> dict:
    return {
        "id": record.id,
        "paper_id": record.paper_id,
        "material_name": record.material_name,
        "normalized_formula": record.normalized_formula,
        "property_name": record.property_name,
        "value": record.value,
        "value_max": record.value_max,
        "unit": record.unit,
        "temperature_value": record.temperature_value,
        "temperature_unit": record.temperature_unit,
        "method": record.method,
        "condition_text": record.condition_text,
        "evidence_text": record.evidence_text,
        "source_chunk_id": record.source_chunk_id,
        "confidence": record.confidence,
        "status": record.status,
    }


def _elements(formula: str) -> list[str]:
    return sorted({token for token in re.findall(r"[A-Z][a-z]?", formula or "") if token in VALID_ELEMENTS})


def _record_formula(record: SolidElectrolyteProperty | dict) -> str:
    if isinstance(record, dict):
        return str(record.get("normalized_formula") or record.get("material_name") or "")
    return str(record.normalized_formula or record.material_name or "")


def _record_value(record: SolidElectrolyteProperty | dict) -> float | None:
    value = record.get("value") if isinstance(record, dict) else record.value
    try:
        parsed = float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
    if parsed is None or parsed <= 0 or parsed > 10:
        return None
    return parsed


def element_frequency_rows(records: list[SolidElectrolyteProperty | dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for record in records:
        for element in _elements(_record_formula(record)):
            counts[element] = counts.get(element, 0) + 1
    return [
        {"element": element, "count": count}
        for element, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]


def conductivity_by_element_rows(records: list[SolidElectrolyteProperty | dict], metric: str = "avg") -> list[dict]:
    grouped: dict[str, list[float]] = {}
    for record in records:
        value = _record_value(record)
        if value is None:
            continue
        for element in _elements(_record_formula(record)):
            grouped.setdefault(element, []).append(value)
    rows = []
    for element, values in grouped.items():
        conductivity = median(values) if metric == "median" else sum(values) / len(values)
        rows.append({"element": element, "conductivity_s_cm": conductivity, "count": len(values)})
    return sorted(rows, key=lambda row: row["conductivity_s_cm"], reverse=True)


async def fetch_property_records(
    property_name: str | None = None,
    confidence_min: float = 0.0,
    status: str | None = None,
) -> list[SolidElectrolyteProperty]:
    async for db in get_db():
        query = select(SolidElectrolyteProperty).where(SolidElectrolyteProperty.confidence >= confidence_min)
        if property_name:
            query = query.where(SolidElectrolyteProperty.property_name == property_name)
        if status:
            query = query.where(SolidElectrolyteProperty.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())
    return []


async def records_response(
    property_name: str | None = None,
    confidence_min: float = 0.0,
    status: str | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    records = await fetch_property_records(property_name, confidence_min, status)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": [_property_to_dict(record) for record in records[start:end]],
        "total": len(records),
        "page": page,
        "page_size": page_size,
    }


async def conductivity_by_material(confidence_min: float = 0.0) -> dict:
    records = [
        record for record in await fetch_property_records("ionic_conductivity", confidence_min)
        if _record_value(record) is not None
    ]
    grouped: dict[str, list[float]] = {}
    for record in records:
        grouped.setdefault(record.material_name or "unknown", []).append(float(record.value))
    rows = [
        {
            "material": material,
            "avg_conductivity_s_cm": sum(values) / len(values),
            "count": len(values),
        }
        for material, values in grouped.items()
    ]
    rows.sort(key=lambda row: row["avg_conductivity_s_cm"], reverse=True)
    return {
        "chart_type": "bar",
        "title": "Ionic conductivity by material",
        "data": rows,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "18%", "containLabel": True},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [row["material"] for row in rows], "axisLabel": {"rotate": 45}},
            "yAxis": {"type": "value", "name": "S/cm", "scale": True},
            "series": [{"type": "bar", "data": [row["avg_conductivity_s_cm"] for row in rows]}],
        },
    }


async def element_frequency(confidence_min: float = 0.0) -> dict:
    records = await fetch_property_records("ionic_conductivity", confidence_min)
    rows = element_frequency_rows(records)
    return {
        "chart_type": "bar",
        "title": "Element frequency in extracted solid-electrolyte formulas",
        "data": rows,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "16%", "containLabel": True},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [row["element"] for row in rows], "axisLabel": {"rotate": 45}},
            "yAxis": {"type": "value", "name": "count"},
            "series": [{"type": "bar", "data": [row["count"] for row in rows], "itemStyle": {"color": "#2563eb"}}],
        },
    }


async def conductivity_by_element(metric: str = "avg", confidence_min: float = 0.0) -> dict:
    records = await fetch_property_records("ionic_conductivity", confidence_min)
    rows = conductivity_by_element_rows(records, metric)
    return {
        "chart_type": "bar",
        "title": "Average ionic conductivity by element" if metric == "avg" else "Median ionic conductivity by element",
        "data": rows,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "16%", "containLabel": True},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [row["element"] for row in rows], "axisLabel": {"rotate": 45}},
            "yAxis": {"type": "log", "name": "S/cm", "scale": True},
            "series": [{"type": "bar", "data": [row["conductivity_s_cm"] for row in rows], "itemStyle": {"color": "#059669"}}],
        },
    }


async def electrochemical_window_by_material(confidence_min: float = 0.0) -> dict:
    records = [
        record for record in await fetch_property_records("electrochemical_window", confidence_min)
        if record.value_max is not None
    ]
    grouped: dict[str, list[float]] = {}
    for record in records:
        grouped.setdefault(record.material_name or "unknown", []).append(record.value_max)
    rows = [
        {
            "material": material,
            "max_window_v": max(values),
            "avg_window_v": sum(values) / len(values),
            "count": len(values),
        }
        for material, values in grouped.items()
    ]
    rows.sort(key=lambda row: row["max_window_v"], reverse=True)
    return {
        "chart_type": "bar",
        "title": "Electrochemical window by material",
        "data": rows,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "18%", "containLabel": True},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [row["material"] for row in rows], "axisLabel": {"rotate": 45}},
            "yAxis": {"type": "value", "name": "V", "scale": True},
            "series": [{"type": "bar", "data": [row["max_window_v"] for row in rows]}],
        },
    }
