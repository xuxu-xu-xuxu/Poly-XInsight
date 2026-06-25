from sqlalchemy import select

from backend.models.database import SolidElectrolyteRecord, get_db
from backend.models.schemas import AnalyticsQueryParams, RecordQueryParams
from backend.services.solid_electrolyte import aggregate_by_element


def _record_to_dict(record: SolidElectrolyteRecord) -> dict:
    return {
        "id": record.id,
        "paper_id": record.paper_id,
        "material_formula": record.material_formula,
        "normalized_formula": record.normalized_formula,
        "elements": record.elements,
        "conductivity_value": record.conductivity_value,
        "conductivity_unit": record.conductivity_unit,
        "conductivity_s_cm": record.conductivity_s_cm,
        "temperature_value": record.temperature_value,
        "temperature_unit": record.temperature_unit,
        "temperature_k": record.temperature_k,
        "method": record.method,
        "method_detail": record.method_detail,
        "is_crystalline": record.is_crystalline,
        "crystallinity": record.crystallinity,
        "evidence_text": record.evidence_text,
        "page_or_section": record.page_or_section,
        "confidence": record.confidence,
    }


async def fetch_records(params: AnalyticsQueryParams | RecordQueryParams) -> list[SolidElectrolyteRecord]:
    async for db in get_db():
        query = select(SolidElectrolyteRecord).where(SolidElectrolyteRecord.conductivity_s_cm.is_not(None))
        if getattr(params, "method", None):
            query = query.where(SolidElectrolyteRecord.method == params.method)
        if getattr(params, "confidence_min", None) is not None:
            query = query.where(SolidElectrolyteRecord.confidence >= params.confidence_min)
        if getattr(params, "temperature_min", None) is not None:
            query = query.where(SolidElectrolyteRecord.temperature_k >= params.temperature_min)
        if getattr(params, "temperature_max", None) is not None:
            query = query.where(SolidElectrolyteRecord.temperature_k <= params.temperature_max)
        if getattr(params, "paper_id", None):
            query = query.where(SolidElectrolyteRecord.paper_id == params.paper_id)
        result = await db.execute(query)
        records = result.scalars().all()
        break
    element = getattr(params, "element", None)
    if element:
        records = [r for r in records if element in (r.elements or [])]
    return records


async def records_response(params: RecordQueryParams) -> dict:
    records = await fetch_records(params)
    start = (params.page - 1) * params.page_size
    end = start + params.page_size
    return {
        "items": [_record_to_dict(r) for r in records[start:end]],
        "total": len(records),
        "page": params.page,
        "page_size": params.page_size,
    }


async def by_element(params: AnalyticsQueryParams) -> dict:
    records = await fetch_records(params)
    rows = aggregate_by_element(records, params.metric)
    return {
        "chart_type": "bar",
        "title": "Average ionic conductivity by element" if params.metric == "avg" else "Median ionic conductivity by element",
        "data": rows,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "12%", "containLabel": True},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "xAxis": {"type": "category", "data": [r["element"] for r in rows], "axisLabel": {"rotate": 45}},
            "yAxis": {"type": "value", "name": "S/cm", "scale": True},
            "series": [{"type": "bar", "data": [r["conductivity_s_cm"] for r in rows], "itemStyle": {"color": "#2c5282"}}],
        },
    }


async def by_method(params: AnalyticsQueryParams) -> dict:
    records = await fetch_records(params)
    grouped: dict[str, list[float]] = {}
    for record in records:
        grouped.setdefault(record.method or "unknown", []).append(record.conductivity_s_cm)
    rows = [
        {
            "method": method,
            "count": len(values),
            "avg_conductivity_s_cm": sum(values) / len(values),
        }
        for method, values in grouped.items() if values
    ]
    return {
        "chart_type": "bar",
        "title": "Ionic conductivity by method",
        "data": rows,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "12%", "containLabel": True},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [r["method"] for r in rows]},
            "yAxis": {"type": "value", "name": "S/cm", "scale": True},
            "series": [{"type": "bar", "data": [r["avg_conductivity_s_cm"] for r in rows], "itemStyle": {"color": "#2c5282"}}],
        },
    }


async def by_temperature(params: AnalyticsQueryParams) -> dict:
    records = [r for r in await fetch_records(params) if r.temperature_k is not None]
    rows = [
        {
            "material_formula": r.material_formula,
            "temperature_k": r.temperature_k,
            "conductivity_s_cm": r.conductivity_s_cm,
            "method": r.method,
        }
        for r in records
    ]
    return {
        "chart_type": "scatter",
        "title": "Ionic conductivity vs temperature",
        "data": rows,
        "echarts_option": {
            "grid": {"left": "3%", "right": "7%", "bottom": "10%", "containLabel": True},
            "tooltip": {
                "trigger": "item",
                "formatter": "{b}",
            },
            "xAxis": {"type": "value", "name": "Temperature (K)"},
            "yAxis": {"type": "value", "name": "S/cm", "scale": True},
            "series": [{
                "type": "scatter",
                "symbolSize": 8,
                "itemStyle": {"color": "#2c5282"},
                "data": [
                    {
                        "name": f"{r['material_formula']} ({r.get('method', '?')})",
                        "value": [r["temperature_k"], r["conductivity_s_cm"]],
                    }
                    for r in rows
                ],
            }],
        },
    }
