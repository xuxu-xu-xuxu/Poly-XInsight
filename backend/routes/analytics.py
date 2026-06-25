from fastapi import APIRouter, Depends

from backend.models.schemas import AnalyticsQueryParams, RecordQueryParams
from backend.services.analytics import by_element, by_method, by_temperature, records_response
from backend.services.solid_electrolyte_properties.analytics import (
    conductivity_by_element as property_conductivity_by_element,
    conductivity_by_material,
    element_frequency,
    electrochemical_window_by_material,
    records_response as property_records_response,
)
from backend.services.thermal_conductive_properties.analytics import (
    conductivity_by_filler,
    conductivity_by_matrix,
    conductivity_distribution,
    filler_content_vs_conductivity,
    filler_frequency,
    filler_types,
    impact_strength_by_material,
    records_response as thermal_records_response,
    storage_modulus_by_material,
    tan_delta_by_material,
    tensile_strength_by_material,
    viscosity_by_material,
    youngs_modulus_by_material,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/records")
async def list_records(params: RecordQueryParams = Depends()):
    return await records_response(params)


@router.get("/conductivity/by-element")
async def conductivity_by_element(params: AnalyticsQueryParams = Depends()):
    return await by_element(params)


@router.get("/conductivity/by-method")
async def conductivity_by_method(params: AnalyticsQueryParams = Depends()):
    return await by_method(params)


@router.get("/conductivity/by-temperature")
async def conductivity_by_temperature(params: AnalyticsQueryParams = Depends()):
    return await by_temperature(params)


@router.get("/properties")
async def list_property_records(
    property_name: str | None = None,
    confidence_min: float = 0.0,
    status: str | None = None,
    page: int = 1,
    page_size: int = 100,
):
    return await property_records_response(property_name, confidence_min, status, page, page_size)


@router.get("/properties/conductivity/by-material")
async def property_conductivity_by_material(confidence_min: float = 0.0):
    return await conductivity_by_material(confidence_min)


@router.get("/properties/conductivity/by-element")
async def property_conductivity_by_element_route(metric: str = "avg", confidence_min: float = 0.0):
    return await property_conductivity_by_element(metric, confidence_min)


@router.get("/properties/elements/frequency")
async def property_element_frequency(confidence_min: float = 0.0):
    return await element_frequency(confidence_min)


@router.get("/properties/electrochemical-window/by-material")
async def property_electrochemical_window_by_material(confidence_min: float = 0.0):
    return await electrochemical_window_by_material(confidence_min)


# ── Thermal conductive polymer analytics ──────────────────────────────

@router.get("/thermal-conductive/records")
async def thermal_conductive_records(
    category: str | None = None,
    property_name: str | None = None,
    confidence_min: float = 0.0,
    status: str | None = None,
    page: int = 1,
    page_size: int = 100,
):
    return await thermal_records_response(category, property_name, confidence_min, status, page, page_size)


# Tab 1: 导热材料原料
@router.get("/thermal-conductive/filler-types")
async def thermal_filler_types(confidence_min: float = 0.0):
    return await filler_types(confidence_min)


@router.get("/thermal-conductive/filler-frequency")
async def thermal_filler_frequency(confidence_min: float = 0.0, top_n: int = 20):
    return await filler_frequency(confidence_min, top_n)


@router.get("/thermal-conductive/filler-content-vs-conductivity")
async def thermal_filler_content_vs_conductivity(confidence_min: float = 0.0):
    return await filler_content_vs_conductivity(confidence_min)


# Tab 2: 导热率/热阻
@router.get("/thermal-conductive/conductivity/by-filler")
async def thermal_conductivity_by_filler(confidence_min: float = 0.0, top_n: int = 20):
    return await conductivity_by_filler(confidence_min, top_n)


@router.get("/thermal-conductive/conductivity/by-matrix")
async def thermal_conductivity_by_matrix(confidence_min: float = 0.0, top_n: int = 20):
    return await conductivity_by_matrix(confidence_min, top_n)


@router.get("/thermal-conductive/conductivity/distribution")
async def thermal_conductivity_distribution(confidence_min: float = 0.0, bins: int = 15):
    return await conductivity_distribution(confidence_min, bins)


# Tab 3: 流变模量/黏度
@router.get("/thermal-conductive/viscosity/by-material")
async def thermal_viscosity_by_material(confidence_min: float = 0.0, top_n: int = 20):
    return await viscosity_by_material(confidence_min, top_n)


@router.get("/thermal-conductive/storage-modulus/by-material")
async def thermal_storage_modulus_by_material(confidence_min: float = 0.0, top_n: int = 20):
    return await storage_modulus_by_material(confidence_min, top_n)


@router.get("/thermal-conductive/tan-delta/by-material")
async def thermal_tan_delta_by_material(confidence_min: float = 0.0, top_n: int = 20):
    return await tan_delta_by_material(confidence_min, top_n)


# Tab 4: 力学性质
@router.get("/thermal-conductive/tensile-strength/by-material")
async def thermal_tensile_strength_by_material(confidence_min: float = 0.0, top_n: int = 20):
    return await tensile_strength_by_material(confidence_min, top_n)


@router.get("/thermal-conductive/youngs-modulus/by-material")
async def thermal_youngs_modulus_by_material(confidence_min: float = 0.0, top_n: int = 20):
    return await youngs_modulus_by_material(confidence_min, top_n)


@router.get("/thermal-conductive/impact-strength/by-material")
async def thermal_impact_strength_by_material(confidence_min: float = 0.0, top_n: int = 20):
    return await impact_strength_by_material(confidence_min, top_n)
