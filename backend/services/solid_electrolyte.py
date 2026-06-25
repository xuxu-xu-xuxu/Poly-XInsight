import json
import re
from statistics import median

from sqlalchemy import delete, select

from backend.config import get_settings
from backend.llm import get_llm_client
from backend.models.database import SolidElectrolyteRecord, get_db

METHODS = {"experiment", "aimd", "ml_potential_md", "other_computation", "unknown"}
VALID_ELEMENTS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn",
}

EXTRACT_PROMPT = """You extract structured solid-electrolyte conductivity data.
Return only a JSON array. Each item must have:
material_formula, conductivity_value, conductivity_unit, temperature_value,
temperature_unit, method, method_detail, is_crystalline, crystallinity,
evidence_text, page_or_section, confidence.

Method enum:
- experiment
- aimd
- ml_potential_md
- other_computation
- unknown

Rules:
- Extract only solid-electrolyte ionic conductivity records explicitly supported by text.
- Do not invent values.
- Keep the original formula and evidence text.
- crystallinity must be crystalline, polycrystalline, amorphous, glassy, or unknown.
- is_crystalline should be true for crystalline/polycrystalline, false for amorphous/glassy, null for unknown.

Text:
{text}
"""


def normalize_formula(formula: str) -> str:
    return re.sub(r"\s+", "", formula or "")


def is_plausible_formula(formula: str) -> bool:
    normalized = normalize_formula(formula)
    if not normalized or normalized.lower() == "unknown":
        return False
    if len(normalized) < 4:
        return False
    # Bare all-caps tokens are commonly abbreviations like ISC rather than formulas.
    if re.fullmatch(r"[A-Z]{2,}", normalized):
        return False
    if not re.search(r"\d", normalized):
        return False
    tokens = re.findall(r"[A-Z][a-z]?", normalized)
    return len(tokens) >= 2 and all(token in VALID_ELEMENTS for token in tokens)


def extract_elements(formula: str) -> list[str]:
    return sorted({token for token in re.findall(r"[A-Z][a-z]?", formula or "") if token in VALID_ELEMENTS})


def normalize_conductivity(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    unit_l = (unit or "S/cm").lower().replace(" ", "").replace("·", "").replace("⋅", "")
    if "ms/cm" in unit_l or "mscm" in unit_l or unit_l.endswith("ms") or "mscm-1" in unit_l:
        return value / 1000
    if "us/cm" in unit_l or "μs/cm" in unit_l or "µs/cm" in unit_l or "uscm" in unit_l:
        return value / 1_000_000
    if "s/m" in unit_l:
        return value / 100
    # "S/cm" or "Scm-1" → return as-is
    return value


def normalize_temperature(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    unit_l = (unit or "K").lower()
    if "c" in unit_l or "℃" in unit_l or "°c" in unit_l:
        return value + 273.15
    return value


def classify_method(text: str) -> tuple[str, str]:
    lower = text.lower()
    if "machine learning potential" in lower or "ml potential" in lower or "mlp" in lower:
        return "ml_potential_md", "machine learning potential molecular dynamics"
    if "aimd" in lower or "ab initio molecular dynamics" in lower:
        return "aimd", "ab initio molecular dynamics"
    if "experiment" in lower or "measured" in lower or "eis" in lower or "impedance" in lower:
        return "experiment", "experimental measurement"
    if "molecular dynamics" in lower or "simulation" in lower or "computed" in lower:
        return "other_computation", "computational estimate"
    return "unknown", ""


def classify_crystallinity(text: str) -> tuple[bool | None, str]:
    lower = text.lower()
    if "amorphous" in lower:
        return False, "amorphous"
    if "glassy" in lower or "glass ceramic" in lower or "glass-ceramic" in lower:
        return False, "glassy"
    if "polycrystalline" in lower or "poly-crystalline" in lower:
        return True, "polycrystalline"
    if "crystalline" in lower or "single crystal" in lower or "crystal structure" in lower:
        return True, "crystalline"
    if "晶体" in text or "结晶" in text:
        return True, "crystalline"
    if "非晶" in text or "玻璃态" in text:
        return False, "amorphous"
    return None, "unknown"


def find_candidate_windows(text: str, window: int = 700) -> list[str]:
    keywords = [
        "conductivity", "ionic conductivity", "S/cm", "mS/cm", "μS/cm", "µS/cm",
        "S cm", "S·cm", "σ", "ionic conductor",
        "AIMD", "molecular dynamics", "machine learning potential", "experiment",
        "impedance", "EIS", "electrolyte", "电导率", "离子电导率", "电解质",
    ]
    windows = []
    seen = set()
    lower = text.lower()
    for keyword in keywords:
        start = 0
        key = keyword.lower()
        while True:
            idx = lower.find(key, start)
            if idx < 0:
                break
            begin = max(0, idx - window // 2)
            end = min(len(text), idx + window // 2)
            snippet = text[begin:end].strip()
            sig = snippet[:80]
            if sig not in seen:
                seen.add(sig)
                windows.append(snippet)
            start = idx + len(key)
    return windows[:30]


def _to_float(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return float(raw.replace("×", "e").replace("x", "e").replace("X", "e"))
    except ValueError:
        return None


def _legacy_regex_extract_records(text: str) -> list[dict]:
    records = []
    windows = find_candidate_windows(text)
    cond_pattern = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?(?:\s*[xX×]\s*10\^?-?\d+|[eE][+-]?\d+)?)\s*(?P<unit>[mμµu]?S\s*/\s*cm|S\s*/\s*m)",
        re.I,
    )
    temp_pattern = re.compile(r"(?P<temp>\d+(?:\.\d+)?)\s*(?P<tunit>K|°C|℃|C)\b", re.I)
    formula_pattern = re.compile(r"\b(?:Li|Na|K|Ag|Cu|Mg|Ca|Ba|Sr|La|Zr|Ta|Nb|P|S|O|Cl|Br|I|Ge|Si|Al|Ga|Ti|Sn|Y|Sc|Hf|W|Mo)(?:[A-Z][a-z]?|\d|\.|\(|\)|x|y|-){2,}\b")

    for window in windows:
        cond = cond_pattern.search(window)
        if not cond:
            continue
        formulas = formula_pattern.findall(window)
        formula = formulas[0] if formulas else "unknown"
        temp = temp_pattern.search(window)
        method, method_detail = classify_method(window)
        is_crystalline, crystallinity = classify_crystallinity(window)
        value = _to_float(re.sub(r"\s+", "", cond.group("value")))
        unit = cond.group("unit").replace(" ", "")
        temp_value = _to_float(temp.group("temp")) if temp else None
        temp_unit = temp.group("tunit") if temp else None
        confidence = 0.78 if formula != "unknown" and temp else 0.65 if formula != "unknown" else 0.45
        records.append({
            "material_formula": formula,
            "conductivity_value": value,
            "conductivity_unit": unit,
            "temperature_value": temp_value,
            "temperature_unit": temp_unit,
            "method": method,
            "method_detail": method_detail,
            "is_crystalline": is_crystalline,
            "crystallinity": crystallinity,
            "evidence_text": window[:1200],
            "page_or_section": "",
            "confidence": confidence,
        })
    return records


def regex_extract_records(text: str) -> list[dict]:
    records = []
    windows = find_candidate_windows(text)
    cond_pattern = re.compile(
        r"(?P<value>[+-]?\d+(?:\.\d+)?(?:\s*[xX×]\s*10\^?-?\d+|[eE][+-]?\d+)?)"
        r"\s*(?P<unit>[mμµu]?S\s*/\s*cm|S\s*/\s*m|"
        r"S\s*[·⋅.\s]?\s*cm\s*[-−–]\s*1|"
        r"S\s*[·⋅.\s]?\s*cm\s*[-−–]\s*[23])",
        re.I,
    )
    temp_pattern = re.compile(
        r"(?P<temp>\d+(?:\.\d+)?)\s*(?P<tunit>K|°C|℃)\b|(?P<ctemp>\d+(?:\.\d+)?)\s+C\b",
        re.I,
    )
    formula_pattern = re.compile(
        r"\b(?=[A-Za-z0-9().,+\-]*\d)"
        r"(?:Li|Na|K|Ag|Cu|Mg|Ca|Ba|Sr|La|Zr|Ta|Nb|"
        r"P|S|O|Cl|Br|I|Ge|Si|Al|Ga|Ti|Sn|Y|Sc|Hf|W|Mo|"
        r"Zn|Fe|Mn|Ni|Co|Cr|V|Sb|Te|Bi|Pb|Cd|In|Ce|Pr|Nd|Sm|Eu|Gd)"
        r"(?:[A-Z][a-z]?|\d|\.\d*|\(|\)|x|y|,|\+|-){2,}\b"
    )

    for window in windows:
        cond = cond_pattern.search(window)
        if not cond:
            continue
        formulas = [f for f in formula_pattern.findall(window) if is_plausible_formula(f)]
        formula = formulas[0] if formulas else "unknown"
        temp = temp_pattern.search(window)
        method, method_detail = classify_method(window)
        is_crystalline, crystallinity = classify_crystallinity(window)
        value = _to_float(re.sub(r"\s+", "", cond.group("value")))
        raw_unit = cond.group("unit").replace(" ", "").replace("·", "").replace("⋅", "")
        # Normalize unit: "Scm-1" → "S/cm", "S cm-1" → "S/cm"
        if raw_unit.endswith("-1") and "/" not in raw_unit:
            unit = raw_unit[:-2] + "/cm"
        elif raw_unit.endswith("-2") and "/" not in raw_unit:
            unit = "S/cm"
        else:
            unit = raw_unit
        temp_value = _to_float(temp.group("temp") or temp.group("ctemp")) if temp else None
        temp_unit = temp.group("tunit") if temp and temp.group("tunit") else "C" if temp and temp.group("ctemp") else None
        confidence = 0.78 if formula != "unknown" and temp else 0.65 if formula != "unknown" else 0.45
        records.append({
            "material_formula": formula,
            "conductivity_value": value,
            "conductivity_unit": unit,
            "temperature_value": temp_value,
            "temperature_unit": temp_unit,
            "method": method,
            "method_detail": method_detail,
            "is_crystalline": is_crystalline,
            "crystallinity": crystallinity,
            "evidence_text": window[:1200],
            "page_or_section": "",
            "confidence": confidence,
        })
    return records


async def llm_extract_records(text: str) -> list[dict]:
    settings = get_settings()
    if not settings.llm_api_key or settings.llm_api_key.startswith("your-"):
        return []
    snippets = "\n\n---\n\n".join(find_candidate_windows(text)[:12])
    if not snippets:
        return []
    llm = get_llm_client()
    response = await llm.chat([{"role": "user", "content": EXTRACT_PROMPT.format(text=snippets[:12000])}])
    cleaned = response.strip()
    # Remove markdown code fences
    for prefix in ["```json", "```"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    for suffix in ["```"]:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-len(suffix)].strip()
    # Fallback: extract JSON array via regex if direct parse fails
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                pass
    return []


def normalize_record(raw: dict, paper_id: str) -> dict:
    formula = str(raw.get("material_formula") or "unknown")
    method = str(raw.get("method") or "unknown").lower()
    if method not in METHODS:
        method = "unknown"
    conductivity_value = raw.get("conductivity_value")
    temperature_value = raw.get("temperature_value")
    try:
        conductivity_value = float(conductivity_value) if conductivity_value is not None else None
    except (TypeError, ValueError):
        conductivity_value = None
    try:
        temperature_value = float(temperature_value) if temperature_value is not None else None
    except (TypeError, ValueError):
        temperature_value = None
    confidence = raw.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5
    normalized = normalize_formula(formula)
    crystallinity = str(raw.get("crystallinity") or "unknown").lower()
    if crystallinity not in {"crystalline", "polycrystalline", "amorphous", "glassy", "unknown"}:
        crystallinity = "unknown"
    raw_is_crystalline = raw.get("is_crystalline")
    if isinstance(raw_is_crystalline, bool):
        is_crystalline = raw_is_crystalline
    elif crystallinity in {"crystalline", "polycrystalline"}:
        is_crystalline = True
    elif crystallinity in {"amorphous", "glassy"}:
        is_crystalline = False
    else:
        is_crystalline, crystallinity_guess = classify_crystallinity(str(raw.get("evidence_text") or ""))
        if crystallinity == "unknown":
            crystallinity = crystallinity_guess
    return {
        "paper_id": paper_id,
        "material_formula": formula,
        "normalized_formula": normalized,
        "elements": extract_elements(normalized),
        "conductivity_value": conductivity_value,
        "conductivity_unit": raw.get("conductivity_unit"),
        "conductivity_s_cm": normalize_conductivity(conductivity_value, raw.get("conductivity_unit")),
        "temperature_value": temperature_value,
        "temperature_unit": raw.get("temperature_unit"),
        "temperature_k": normalize_temperature(temperature_value, raw.get("temperature_unit")),
        "method": method,
        "method_detail": raw.get("method_detail") or "",
        "is_crystalline": is_crystalline,
        "crystallinity": crystallinity,
        "evidence_text": raw.get("evidence_text") or "",
        "page_or_section": raw.get("page_or_section") or "",
        "confidence": confidence,
    }


async def extract_solid_electrolyte_records(paper_id: str, paper_text: str, replace: bool = True) -> dict:
    raw_records = await llm_extract_records(paper_text)
    raw_records.extend(regex_extract_records(paper_text))
    records = [normalize_record(r, paper_id) for r in raw_records]
    records = [r for r in records if r["conductivity_s_cm"] is not None and r["evidence_text"]]
    records = [r for r in records if is_plausible_formula(r["normalized_formula"])]
    deduped: dict[tuple[str, float | None, float | None, str], dict] = {}
    for record in records:
        key = (
            record["normalized_formula"],
            record["conductivity_s_cm"],
            record["temperature_k"],
            record["method"],
        )
        if key not in deduped or record["confidence"] > deduped[key]["confidence"]:
            deduped[key] = record
    records = list(deduped.values())

    async for db in get_db():
        if replace:
            await db.execute(delete(SolidElectrolyteRecord).where(SolidElectrolyteRecord.paper_id == paper_id))
        for record in records:
            db.add(SolidElectrolyteRecord(**record))
        await db.commit()
        break
    return {"paper_id": paper_id, "record_count": len(records)}


def aggregate_by_element(records: list[SolidElectrolyteRecord], metric: str = "avg") -> list[dict]:
    grouped: dict[str, list[float]] = {}
    for record in records:
        for element in record.elements or []:
            if record.conductivity_s_cm is not None:
                grouped.setdefault(element, []).append(record.conductivity_s_cm)
    rows = []
    for element, values in grouped.items():
        value = median(values) if metric == "median" else sum(values) / len(values)
        rows.append({"element": element, "conductivity_s_cm": value, "count": len(values)})
    return sorted(rows, key=lambda r: r["conductivity_s_cm"], reverse=True)
