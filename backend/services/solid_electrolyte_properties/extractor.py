import re

VALID_ELEMENTS = {
    "H", "Li", "Be", "B", "C", "N", "O", "F", "Na", "Mg", "Al", "Si", "P", "S", "Cl",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge",
    "As", "Se", "Br", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Ag", "Cd", "In", "Sn", "Sb",
    "Te", "I", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho",
    "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Pb", "Bi",
}

ABBR_FORMULAS = {
    "LLZO": "Li7La3Zr2O12",
    "LGPS": "Li10GeP2S12",
    "LAGP": "Li1.5Al0.5Ge1.5P3O12",
    "LATP": "Li1.3Al0.3Ti1.7P3O12",
    "LIPON": "LiPON",
    "NASICON": "Na3Zr2Si2PO12",
}

FORMULA_OR_ABBR_PATTERN = re.compile(
    r"\b(LLZO|LGPS|LAGP|LATP|LIPON|NASICON|"
    r"(?:Li|Na|K|Ag|Mg|Ca|Ba|Sr|La|Zr|Ta|Nb|P|S|O|Cl|Br|I|Ge|Si|Al|Ga|Ti|Sn|Y|Sc|Hf|W|Mo|Zn|Fe|Mn|Ni|Co|Cr|V|Sb|Te|Bi|Pb|Cd|In|Ce|Pr|Nd|Sm|Eu|Gd)"
    r"[A-Za-z0-9().,+\-]{2,})\b"
)

CONDUCTIVITY_PATTERN = re.compile(
    r"(?P<value>[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:\s*(?:x|X|\*)\s*10\s*\^?\s*[-+]?\s*\d+|[eE][-+]?\d+)?|10\s*\^?\s*[-+]?\s*\d+)"
    r"\s*(?P<unit>[mu]?S\s*(?:/|\s)?\s*cm\s*(?:[-^]?\s*1)?|S\s*/\s*m)",
    re.IGNORECASE,
)

TEMP_PATTERN = re.compile(r"(?P<temp>\d+(?:\.\d+)?)\s*(?P<unit>K|C|degC|degrees? C)\b", re.IGNORECASE)

RANGE_WINDOW_PATTERN = re.compile(
    r"(?P<low>\d+(?:\.\d+)?)\s*(?:-|to)\s*(?P<high>\d+(?:\.\d+)?)\s*V",
    re.IGNORECASE,
)

UP_TO_WINDOW_PATTERN = re.compile(
    r"(?:stable|stability|window|oxidation|up to)[^\n.;]{0,80}?(?P<high>\d+(?:\.\d+)?)\s*V",
    re.IGNORECASE,
)


def _normalize_symbols(text: str) -> str:
    return (
        (text or "")
        .replace("\u00d7", "x")
        .replace("\u2715", "x")
        .replace("\u2212", "-")
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00b7", " ")
        .replace("\u2219", " ")
        .replace("\u00b0C", "degC")
        .replace("\u2103", "degC")
        .replace("\u03bc", "u")
        .replace("\u00b5", "u")
    )


def _to_float(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        cleaned = re.sub(r"\s+", "", _normalize_symbols(raw))
        if re.fullmatch(r"10\^?[-+]?\d+", cleaned):
            exponent = re.sub(r"^10\^?", "", cleaned)
            return 10 ** int(exponent)
        if "x10" in cleaned.lower():
            base, exponent = re.split(r"x10\^?", cleaned, flags=re.IGNORECASE)
            return float(base) * (10 ** int(exponent))
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _raw_scientific_base(raw: str | None) -> float | None:
    if not raw:
        return None
    cleaned = re.sub(r"\s+", "", _normalize_symbols(raw))
    if "x10" in cleaned.lower():
        return _to_float(re.split(r"x10\^?", cleaned, flags=re.IGNORECASE)[0])
    return _to_float(raw)


def _normalize_conductivity_unit(unit: str) -> str:
    cleaned = _normalize_symbols(unit or "").replace(" ", "")
    cleaned = cleaned.replace("cm-1", "cm").replace("cm^1", "cm").replace("cm1", "cm")
    cleaned = cleaned.replace("Scm", "S/cm")
    if cleaned.lower().startswith("ms"):
        return "mS/cm"
    if cleaned.lower().startswith("us"):
        return "uS/cm"
    if "S/m" in cleaned:
        return "S/m"
    return "S/cm"


def _conductivity_to_s_cm(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    if unit == "mS/cm":
        return value / 1000
    if unit == "uS/cm":
        return value / 1_000_000
    if unit == "S/m":
        return value / 100
    return value


def _elements(formula: str) -> list[str]:
    return [token for token in re.findall(r"[A-Z][a-z]?", formula or "") if token in VALID_ELEMENTS]


def _clean_material(token: str) -> str:
    cleaned = (token or "").strip().strip(".,;:)]}")
    cleaned = re.sub(r"(?:\.?(?:This|The|It|These|Such|In|At|For))$", "", cleaned)
    return cleaned.strip().strip(".,;:)]}")


def _normalized_formula(material: str) -> str:
    if material in ABBR_FORMULAS:
        return ABBR_FORMULAS[material]
    return re.sub(r"\s+", "", material or "")


def _is_plausible_material(material: str) -> bool:
    if not material or material.lower() == "unknown":
        return False
    if material in ABBR_FORMULAS:
        return True
    if material == "Lithium-Ion":
        return False
    if not re.search(r"\d", material):
        return False
    tokens = re.findall(r"[A-Z][a-z]?", material)
    allowed_placeholders = {"A", "M", "X", "Y"}
    if any(token not in VALID_ELEMENTS and token not in allowed_placeholders for token in tokens):
        return False
    return len({token for token in tokens if token in VALID_ELEMENTS}) >= 2


def _find_material(text: str, position: int = 0) -> str:
    begin = max(0, position - 240)
    end = min(len(text), position + 240)
    window = _normalize_symbols(text[begin:end])
    matches = []
    for match in FORMULA_OR_ABBR_PATTERN.finditer(window):
        material = _clean_material(match.group(1))
        if _is_plausible_material(material):
            matches.append((match.start(), material))
    if not matches:
        return "unknown"
    relative_position = position - begin
    before = [item for item in matches if item[0] <= relative_position]
    return (before[-1] if before else matches[0])[1]


def _temperature(text: str, position: int = 0) -> tuple[float | None, str | None]:
    normalized_text = _normalize_symbols(text)
    begin = max(0, position - 120)
    end = min(len(normalized_text), position + 120)
    match = TEMP_PATTERN.search(normalized_text[begin:end])
    if not match:
        return None, None
    return _to_float(match.group("temp")), match.group("unit")


def _base_record(
    paper_id: str,
    text: str,
    heading: str,
    chunk_index: int,
    property_name: str,
    position: int,
) -> dict:
    material = _find_material(text, position)
    return {
        "paper_id": paper_id,
        "material_name": material,
        "normalized_formula": _normalized_formula(material) if material != "unknown" else "",
        "property_name": property_name,
        "method": "unknown",
        "condition_text": heading or "",
        "evidence_text": text[max(0, position - 260): min(len(text), position + 420)].strip(),
        "source_chunk_id": f"{paper_id}_{chunk_index}",
        "confidence": 0.78 if material != "unknown" else 0.52,
        "status": "candidate",
    }


def _conductivity_records(paper_id: str, text: str, heading: str, chunk_index: int) -> list[dict]:
    records = []
    normalized_text = _normalize_symbols(text)
    for match in CONDUCTIVITY_PATTERN.finditer(normalized_text):
        context = normalized_text[max(0, match.start() - 140): min(len(normalized_text), match.end() + 140)].lower()
        material = _find_material(text, match.start())
        if material == "unknown" and not any(term in context for term in ("conduct", "sigma", "\u03c3", "impedance", "eis")):
            continue
        value = _to_float(match.group("value"))
        unit = _normalize_conductivity_unit(match.group("unit"))
        converted = _conductivity_to_s_cm(value, unit)
        if converted is None or converted <= 0 or converted > 10:
            continue
        temp_value, temp_unit = _temperature(text, match.start())
        record = _base_record(paper_id, text, heading, chunk_index, "ionic_conductivity", match.start())
        record.update({
            "value": converted,
            "value_max": None,
            "unit": "S/cm",
            "raw_value": _raw_scientific_base(match.group("value")),
            "raw_unit": unit,
            "temperature_value": temp_value,
            "temperature_unit": temp_unit,
        })
        records.append(record)
    return records


def _window_records(paper_id: str, text: str, heading: str, chunk_index: int) -> list[dict]:
    records = []
    normalized_text = _normalize_symbols(text)
    for match in RANGE_WINDOW_PATTERN.finditer(normalized_text):
        record = _base_record(paper_id, text, heading, chunk_index, "electrochemical_window", match.start())
        record.update({
            "value": _to_float(match.group("low")),
            "value_max": _to_float(match.group("high")),
            "unit": "V",
            "raw_value": None,
            "raw_unit": "V",
            "temperature_value": None,
            "temperature_unit": None,
        })
        records.append(record)

    if records:
        return records

    for match in UP_TO_WINDOW_PATTERN.finditer(normalized_text):
        record = _base_record(paper_id, text, heading, chunk_index, "electrochemical_window", match.start())
        record.update({
            "value": None,
            "value_max": _to_float(match.group("high")),
            "unit": "V",
            "raw_value": None,
            "raw_unit": "V",
            "temperature_value": None,
            "temperature_unit": None,
        })
        records.append(record)
    return records


def extract_property_candidates(
    paper_id: str,
    text: str,
    heading: str = "",
    chunk_index: int = 0,
) -> list[dict]:
    records = [
        *_conductivity_records(paper_id, text, heading, chunk_index),
        *_window_records(paper_id, text, heading, chunk_index),
    ]
    return [record for record in records if record["normalized_formula"]]
