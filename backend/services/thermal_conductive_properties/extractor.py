import re
from typing import Optional

# ─── Symbol normalization ────────────────────────────────────────────

def _normalize_symbols(text: str) -> str:
    return (text or "").replace("×", "x").replace("✕", "x") \
        .replace("−", "-").replace("‐", "-").replace("‑", "-") \
        .replace("‒", "-").replace("–", "-").replace("—", "-") \
        .replace("·", " ").replace("∙", " ").replace("°C", "degC") \
        .replace("℃", "degC").replace("μ", "u").replace("µ", "u")

# ─── Number parsing ──────────────────────────────────────────────────

def _to_float(raw: Optional[str]) -> Optional[float]:
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

# ─── Material name normalization ──────────────────────────────────────

MATERIAL_NORMALIZE = {
    # Element symbols → full name (lowercase canonical)
    "Ag": "silver", "silver": "silver",
    "Al": "aluminum", "aluminum": "aluminum",
    "Cu": "copper", "copper": "copper",
    "Ni": "nickel", "nickel": "nickel",
    "Au": "gold", "gold": "gold",
    "Fe": "iron", "iron": "iron",
    "Zn": "zinc", "ZnO": "zinc oxide",
    # Graphene variants
    "graphene": "graphene", "Graphene": "graphene",
    "graphene oxide": "graphene oxide", "GO": "graphene oxide",
    "reduced graphene oxide": "reduced graphene oxide", "rGO": "reduced graphene oxide",
    "graphene nanoplatelet": "graphene nanoplatelet", "GNP": "graphene nanoplatelet",
    "GNPs": "graphene nanoplatelet",
    # Carbon fillers
    "CNT": "carbon nanotube", "CNTs": "carbon nanotube",
    "MWCNT": "carbon nanotube", "MWCNTs": "carbon nanotube",
    "SWCNT": "carbon nanotube", "SWCNTs": "carbon nanotube",
    "carbon nanotube": "carbon nanotube",
    "multi-walled carbon nanotube": "carbon nanotube",
    "single-walled carbon nanotube": "carbon nanotube",
    "carbon fiber": "carbon fiber", "carbon fibre": "carbon fiber",
    "carbon black": "carbon black", "CB": "carbon black",
    "graphite": "graphite", "expanded graphite": "expanded graphite", "EG": "expanded graphite",
    "exfoliated graphite": "expanded graphite",
    # Ceramic fillers
    "BN": "boron nitride", "h-BN": "boron nitride", "hBN": "boron nitride",
    "c-BN": "boron nitride", "cBN": "boron nitride",
    "boron nitride": "boron nitride", "hexagonal boron nitride": "boron nitride",
    "AlN": "aluminum nitride", "aluminum nitride": "aluminum nitride",
    "Al2O3": "alumina", "alumina": "alumina", "aluminium oxide": "alumina",
    "SiC": "silicon carbide", "silicon carbide": "silicon carbide",
    "SiO2": "silica", "silica": "silica",
    "Si3N4": "silicon nitride", "silicon nitride": "silicon nitride",
    "MgO": "magnesium oxide", "magnesium oxide": "magnesium oxide",
    "zinc oxide": "zinc oxide",
    # Other
    "diamond": "diamond", "nanodiamond": "diamond", "ND": "diamond",
    "MXene": "MXene", "Ti3C2": "MXene", "Ti3C2Tx": "MXene",
    "glass fiber": "glass fiber", "glass fibre": "glass fiber", "GF": "glass fiber",
    # Matrix normalization
    "epoxy": "epoxy", "epoxy resin": "epoxy", "E51": "epoxy", "DGEBA": "epoxy",
    "polyimide": "polyimide", "PI": "polyimide",
    "silicone": "silicone", "PDMS": "silicone",
    "polyurethane": "polyurethane", "PU": "polyurethane",
    "PEEK": "PEEK",
    "polyamide": "polyamide", "nylon": "polyamide", "PA": "polyamide", "PA6": "polyamide", "PA66": "polyamide",
    "polypropylene": "polypropylene", "PP": "polypropylene",
    "polyethylene": "polyethylene", "PE": "polyethylene",
}

FILLER_CANONICAL_ORDER = [
    "boron nitride", "aluminum nitride", "alumina", "silicon carbide", "silica",
    "silicon nitride", "magnesium oxide", "zinc oxide",
    "graphene", "graphene oxide", "reduced graphene oxide", "graphene nanoplatelet",
    "carbon nanotube", "carbon fiber", "carbon black", "graphite", "expanded graphite",
    "diamond", "MXene", "silver", "aluminum", "copper", "nickel", "iron",
    "glass fiber",
]


def _normalize_material(name: str) -> str:
    """Normalize filler/matrix name to canonical form. Case-insensitive + synonyms."""
    if not name or name == "unknown":
        return name
    # Direct match in map (case-sensitive first, then case-insensitive)
    if name in MATERIAL_NORMALIZE:
        return MATERIAL_NORMALIZE[name]
    lower = name.lower()
    for key, val in MATERIAL_NORMALIZE.items():
        if key.lower() == lower:
            return val
    # If starts with lowercase, try title-casing
    if name[0].islower():
        titled = name[0].upper() + name[1:]
        if titled in MATERIAL_NORMALIZE:
            return MATERIAL_NORMALIZE[titled]
    return name


def _normalize_filler(name: str) -> str:
    canonical = _normalize_material(name)
    # If canonical not in filler list, keep original but lowercase
    if canonical not in FILLER_CANONICAL_ORDER and canonical.lower() not in [f.lower() for f in FILLER_CANONICAL_ORDER]:
        return canonical
    # Find the correctly-cased canonical form
    for f in FILLER_CANONICAL_ORDER:
        if f.lower() == canonical.lower():
            return f
    return canonical


# ─── Filler / Matrix recognition ─────────────────────────────────────

FILLER_NAMES = {
    "BN", "h-BN", "hBN", "c-BN", "cBN", "boron nitride", "hexagonal boron nitride",
    "AlN", "aluminum nitride", "Al2O3", "alumina", "aluminium oxide",
    "SiC", "silicon carbide", "MgO", "magnesium oxide", "ZnO", "zinc oxide",
    "SiO2", "silica", "Si3N4", "silicon nitride", "BeO", "beryllium oxide",
    "graphene", "GO", "rGO", "graphite", "graphite oxide", "reduced graphene oxide",
    "graphene oxide", "graphene nanoplatelet", "GNP", "GNPs",
    "CNT", "CNTs", "MWCNT", "MWCNTs", "SWCNT", "SWCNTs",
    "carbon nanotube", "multi-walled carbon nanotube", "single-walled carbon nanotube",
    "carbon fiber", "carbon fibre", "carbon black", "CB",
    "diamond", "nanodiamond", "ND",
    "Cu", "copper", "Ag", "silver", "Al", "aluminum", "Ni", "nickel",
    "MXene", "Ti3C2", "Ti3C2Tx",
    "expanded graphite", "EG", "exfoliated graphite",
    "glass fiber", "glass fibre", "GF",
}

FILLER_TYPE_MAP = {
    # Ceramic
    "boron nitride": "ceramic", "aluminum nitride": "ceramic",
    "alumina": "ceramic", "silicon carbide": "ceramic",
    "magnesium oxide": "ceramic", "zinc oxide": "ceramic",
    "silica": "ceramic", "silicon nitride": "ceramic",
    "beryllium oxide": "ceramic",
    # Carbon
    "graphene": "carbon", "graphene oxide": "carbon",
    "reduced graphene oxide": "carbon", "graphene nanoplatelet": "carbon",
    "carbon nanotube": "carbon", "carbon fiber": "carbon",
    "carbon black": "carbon", "graphite": "carbon",
    "expanded graphite": "carbon", "diamond": "carbon",
    # Metal
    "silver": "metal", "aluminum": "metal", "copper": "metal",
    "nickel": "metal", "iron": "metal",
    # Other
    "MXene": "ceramic", "glass fiber": "ceramic",
}

MATRIX_NAMES = {
    "epoxy", "epoxy resin", "E51", "E44", "DGEBA",
    "polyimide", "PI",
    "silicone", "PDMS", "polydimethylsiloxane",
    "polyurethane", "PU",
    "PEEK", "polyetheretherketone",
    "PA", "PA6", "PA66", "polyamide", "nylon",
    "PP", "polypropylene",
    "PE", "polyethylene", "LDPE", "HDPE", "UHMWPE",
    "PS", "polystyrene",
    "PVDF", "polyvinylidene fluoride",
    "PMMA", "polymethyl methacrylate",
    "PC", "polycarbonate",
    "PVA", "polyvinyl alcohol",
    "ABS",
    "PET",
    "PPS", "polyphenylene sulfide",
    "PTFE", "polytetrafluoroethylene",
    "PLA", "polylactic acid",
    "PCL", "polycaprolactone",
    "SBR", "styrene-butadiene rubber",
    "NR", "natural rubber",
    "SBS", "styrene-butadiene-styrene",
    "SEBS",
}

_filler_pattern = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in sorted(FILLER_NAMES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

_matrix_pattern = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in sorted(MATRIX_NAMES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

_filler_content_pattern = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>wt%|vol%|w/%|weight%|volume%|wt\.?\s*%|vol\.?\s*%|phr)",
    re.IGNORECASE,
)

_particle_size_pattern = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>nm|μm|um|mm|micron|microns|nanometers|micrometers)",
    re.IGNORECASE,
)

_surface_treatment_pattern = re.compile(
    r"(?:surface\s+(?:treatment|modification|functionalization)|treated\s+with|modified\s+with"
    r"|functionalized\s+with|silane|coupling\s+agent|KH[- ]?\d+|APTES|OTS|PDA|dopamine)\b"
    r"[^.;]{10,120}(?P<detail>(?:silane|APTES|KH[- ]?\d+|dopamine|PDA|polydopamine|"
    r"OTS|stearic\s*acid|oleic\s*acid|titanate|zirconate|plasma|UV|ozone))",
    re.IGNORECASE,
)

# ─── Thermal property patterns ────────────────────────────────────────

_tc_pattern = re.compile(
    r"(?:thermal\s+conductivity|TC|κ|kappa|λ|lambda|k\s*[=:≈]|\bTC\b)\s*"
    r"(?:[^.;]{0,80})?"
    r"(?P<value>[+-]?\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?|10\s*\^?\s*[-+]?\s*\d+)"
    r"\s*(?P<unit>"
    r"W\s*(?:/|·|\*)\s*(?:m|meter)\s*(?:·|/|\*|\s)\s*K|"
    r"W\s*m\^-1\s*K\^-1|W\s*m\s*-1\s*K\s*-1|"
    r"W\s+m\s*-1\s*K\s*-1|"
    r"W/(?:m·K|mK|m-K|m\-K)"
    r")",
    re.IGNORECASE,
)

_tc_bare_pattern = re.compile(
    r"(?P<value>[+-]?\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>"
    r"W\s*(?:/|·|\*)\s*(?:m|meter)\s*(?:·|/|\*|\s)\s*K|"
    r"W\s*m\^-1\s*K\^-1|W\s*m\s*-1\s*K\s*-1|"
    r"W\s+m\s*-1\s*K\s*-1|"
    r"W/(?:m·K|mK|m-K|m\-K)"
    r")",
    re.IGNORECASE,
)

_thermal_resistance_pattern = re.compile(
    r"(?:thermal\s+resistance|ITR|Rth|R\s*th|R\s*TIM|R\s*c)\s*"
    r"(?:[^.;]{0,60})?"
    r"(?P<value>\d+(?:\.\d+)?)"
    r"\s*(?P<unit>"
    r"K\s*(?:/|\·)\s*W|"
    r"K\s*\·\s*m\^2\s*(?:/|\·)\s*W|"
    r"K\s*m\^2\s*W\^-1|K\s*m\^2\s*W\s*-1|"
    r"K/W|K\s*W\^-1|K\s*W\s*-1|"
    r"mm\^2\s*K\s*W\^-1|mm\^2\s*K\s*W\s*-1|mm2\s*K\s*W\^-1|mm2\s*K\s*W\s*-1|"
    r"m\^2\s*K\s*W\^-1|m\^2\s*K\s*W\s*-1|m2\s*K\s*W\^-1|m2\s*K\s*W\s*-1|"
    r"m2\s*K\s*W|m\^2\s*K\s*W"
    r")",
    re.IGNORECASE,
)

_diffusivity_pattern = re.compile(
    r"(?:thermal\s+diffusivity|α|alpha|a)\s*"
    r"(?:[^.;]{0,40})?"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>"
    r"mm\^2\s*(?:/|\·)\s*s|mm2/s|"
    r"m\^2\s*(?:/|\·)\s*s|m2/s|"
    r"mm\^2\s*s\^-1|mm\^2\s*s\s*-1|mm2\s*s\^-1|mm2\s*s\s*-1|"
    r"m\^2\s*s\^-1|m\^2\s*s\s*-1|m2\s*s\^-1|m2\s*s\s*-1"
    r")",
    re.IGNORECASE,
)

_cte_pattern = re.compile(
    r"(?:CTE|coefficient\s+of\s+thermal\s+expansion|thermal\s+expansion\s+coefficient)\s*"
    r"(?:[^.;]{0,40})?"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ppm\s*(?:/|\·|per)\s*K|10\^-6\s*(?:/|\·)\s*K|ppm/K|ppm\s*K\^-1)",
    re.IGNORECASE,
)

# ─── Rheological property patterns ────────────────────────────────────

_viscosity_pattern = re.compile(
    r"(?:(?:complex|shear|apparent|dynamic|intrinsic)\s+)?"
    r"(?:viscosity|η|eta)\s*"
    r"(?:[^.;]{0,40})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>Pa\s*(?:·|\.|s)\s*s|Pa·s|Pa\.s|cP|mPa\s*(?:·|\.|s)\s*s|mPa·s|poise)",
    re.IGNORECASE,
)

_storage_modulus_pattern = re.compile(
    r"(?:storage\s+modulus|G\s*'|G\')\s*"
    r"(?:[^.;]{0,40})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

_loss_modulus_pattern = re.compile(
    r"(?:loss\s+modulus|G\s*\"|G\")\s*"
    r"(?:[^.;]{0,40})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

_tan_delta_pattern = re.compile(
    r"(?:tan\s*(?:δ|delta)|loss\s+factor|damping\s+factor|tanδ|tand)\s*"
    r"(?:[^.;]{0,30})?"
    r"(?P<value>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

_yield_stress_pattern = re.compile(
    r"(?:yield\s+stress|τ\s*y|sigma\s*y|σ\s*y)\s*"
    r"(?:[^.;]{0,40})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

# ─── Mechanical property patterns ─────────────────────────────────────

_tensile_strength_pattern = re.compile(
    r"(?:tensile\s+strength|UTS|σ\s*t|sigma\s*t)\s*"
    r"(?:[^.;]{0,50})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

_youngs_modulus_pattern = re.compile(
    r"(?:Young\s*'?s?\s+modulus|elastic\s+modulus|E\s*[=:≈]|tensile\s+modulus)\s*"
    r"(?:[^.;]{0,50})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

_elongation_pattern = re.compile(
    r"(?:elongation\s+at\s+break|elongation|ε\s*b|epsilon\s*b|strain\s+at\s+break|breaking\s+elongation)\s*"
    r"(?:[^.;]{0,50})?"
    r"(?P<value>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

_flexural_strength_pattern = re.compile(
    r"(?:flexural\s+strength|bending\s+strength|σ\s*f|sigma\s*f|three-point\s+bending\s+strength)\s*"
    r"(?:[^.;]{0,50})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

_flexural_modulus_pattern = re.compile(
    r"(?:flexural\s+modulus|bending\s+modulus|E\s*f)\s*"
    r"(?:[^.;]{0,50})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

_impact_strength_pattern = re.compile(
    r"(?:impact\s+strength|Izod|Charpy|notched\s+impact)\s*"
    r"(?:[^.;]{0,50})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>kJ\s*(?:/|\·|per)\s*m\^?2|kJ/m2|kJ/m\^2|J/m|J\s*(?:/|\·)\s*m)",
    re.IGNORECASE,
)

_hardness_pattern = re.compile(
    r"(?:hardness|Shore)\s*"
    r"(?:[^.;]{0,30})?"
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?:(?P<unit>Shore\s*(?:A|D)|shore\s*(?:A|D)|HA|HD|HV|Mohs)\b)?",
    re.IGNORECASE,
)

_compressive_strength_pattern = re.compile(
    r"(?:compressive\s+strength|compression\s+strength|σ\s*c|sigma\s*c)\s*"
    r"(?:[^.;]{0,50})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

_shear_strength_pattern = re.compile(
    r"(?:shear\s+strength|τ|tau|interlaminar\s+shear|ILSS)\s*"
    r"(?:[^.;]{0,50})?"
    r"(?P<value>\d+(?:\.\d+)?(?:\s*(?:×|x)\s*10\s*\^?\s*[-+]?\s*\d+)?)"
    r"\s*(?P<unit>GPa|MPa|kPa|Pa)\b",
    re.IGNORECASE,
)

# ─── Temperature ──────────────────────────────────────────────────────

_temp_pattern = re.compile(
    r"(?P<temp>\d+(?:\.\d+)?)\s*(?P<unit>K|°C|degC|degrees?\s*C|Celsius)",
    re.IGNORECASE,
)

# ─── Frequency ────────────────────────────────────────────────────────

_freq_pattern = re.compile(
    r"(?:at|@)\s*(?P<freq>\d+(?:\.\d+)?)\s*(?P<unit>Hz|kHz|MHz|rad\s*(?:/|\·)\s*s)",
    re.IGNORECASE,
)

# ─── Confidence helpers ───────────────────────────────────────────────

CONFIDENCE_HIGH = 0.82
CONFIDENCE_MEDIUM = 0.60
CONFIDENCE_LOW = 0.40


# ─── Unit normalizers ─────────────────────────────────────────────────

def _normalize_unit(raw_unit: Optional[str]) -> str:
    if not raw_unit:
        return ""
    return _normalize_symbols(raw_unit).replace(" ", "").replace("·", "").replace("·", "")


def _categorize_filler_type(filler_name: str) -> Optional[str]:
    for name, ftype in sorted(FILLER_TYPE_MAP.items(), key=lambda x: -len(x[0])):
        if filler_name.lower() == name.lower():
            return ftype
    return None


# ─── Context scanners ─────────────────────────────────────────────────

def _find_fillers(text: str) -> list[str]:
    """Find all filler names in text, return sorted by frequency (normalized)."""
    found: dict[str, int] = {}
    for match in _filler_pattern.finditer(_normalize_symbols(text)):
        name = match.group(1).strip()
        canonical = _normalize_filler(name)
        found[canonical] = found.get(canonical, 0) + 1
    return [name for name, _ in sorted(found.items(), key=lambda x: -x[1])]


def _find_matrices(text: str) -> list[str]:
    """Find all matrix names in text, return sorted by frequency (normalized)."""
    found: dict[str, int] = {}
    for match in _matrix_pattern.finditer(_normalize_symbols(text)):
        name = match.group(1).strip()
        canonical = _normalize_material(name)
        found[canonical] = found.get(canonical, 0) + 1
    return [name for name, _ in sorted(found.items(), key=lambda x: -x[1])]


def _find_filler_content(text: str) -> list[dict]:
    results = []
    for match in _filler_content_pattern.finditer(_normalize_symbols(text)):
        val = _to_float(match.group("value"))
        if val is None or val <= 0 or val > 100:
            continue
        results.append({"value": val, "unit": match.group("unit").strip()})
    return results


def _nearest_filler_content(contents: list[dict], position: int, text: str) -> Optional[dict]:
    if not contents:
        return None
    best = contents[0]
    best_dist = float("inf")
    for fc in contents:
        match_pos = text.lower().find(f"{fc['value']} {fc['unit']}")
        if match_pos < 0:
            match_pos = text.lower().find(f"{fc['value']}{fc['unit']}")
        if match_pos >= 0:
            dist = abs(match_pos - position)
            if dist < best_dist:
                best_dist = dist
                best = fc
    return best if best_dist < 600 else None


def _nearest_temperature(text: str, position: int) -> tuple[Optional[float], Optional[str]]:
    best_temp, best_unit, best_dist = None, None, float("inf")
    for match in _temp_pattern.finditer(_normalize_symbols(text)):
        dist = abs(match.start() - position)
        if dist < best_dist and dist < 400:
            best_dist = dist
            best_temp = _to_float(match.group("temp"))
            best_unit = match.group("unit").strip()
    return best_temp, best_unit


def _nearest_frequency(text: str, position: int) -> Optional[float]:
    best_freq, best_dist = None, float("inf")
    for match in _freq_pattern.finditer(_normalize_symbols(text)):
        dist = abs(match.start() - position)
        if dist < best_dist and dist < 300:
            best_dist = dist
            best_freq = _to_float(match.group("freq"))
    return best_freq


def _in_context(text: str, position: int, keywords: list[str], window: int = 200) -> bool:
    """Check if any keyword appears near position."""
    begin = max(0, position - window)
    end = min(len(text), position + window)
    snippet = text[begin:end].lower()
    return any(kw.lower() in snippet for kw in keywords)


# ─── Base record builder ──────────────────────────────────────────────

def _base_record(
    paper_id: str,
    text: str,
    heading: str,
    chunk_index: int,
    property_category: str,
    property_name: str,
    position: int,
) -> dict:
    fillers = _find_fillers(text)
    matrices = _find_matrices(text)
    contents = _find_filler_content(text)
    temp_val, temp_unit = _nearest_temperature(text, position)
    freq = _nearest_frequency(text, position)
    content = _nearest_filler_content(contents, position, text)
    surface_treatments = _surface_treatment_pattern.findall(_normalize_symbols(text))
    particle_sizes = _particle_size_pattern.findall(_normalize_symbols(text))

    primary_filler = fillers[0] if fillers else "unknown"
    primary_matrix = matrices[0] if matrices else None

    return {
        "paper_id": paper_id,
        "filler_name": primary_filler,
        "filler_type": _categorize_filler_type(primary_filler),
        "matrix_name": primary_matrix,
        "filler_content": content["value"] if content else None,
        "filler_content_unit": content["unit"] if content else None,
        "particle_size": f"{particle_sizes[0][0]} {particle_sizes[0][1]}" if particle_sizes else None,
        "surface_treatment": surface_treatments[0] if surface_treatments else None,
        "property_category": property_category,
        "property_name": property_name,
        "method": "unknown",
        "condition_text": heading or "",
        "evidence_text": text[max(0, position - 260): min(len(text), position + 420)].strip(),
        "source_chunk_id": f"{paper_id}_{chunk_index}",
        "confidence": CONFIDENCE_MEDIUM,
        "status": "candidate",
        "temperature_value": temp_val,
        "temperature_unit": temp_unit,
        "frequency": freq,
    }


# ─── Property extractors ──────────────────────────────────────────────

def _thermal_records(paper_id: str, text: str, heading: str, chunk_index: int) -> list[dict]:
    records = []
    norm = _normalize_symbols(text)

    # Thermal conductivity
    for match in _tc_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        unit_str = match.group("unit")
        if val is None or val <= 0 or val > 5000:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "thermal", "thermal_conductivity", match.start())
        rec["value"] = val
        rec["unit"] = "W/(m·K)"
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    # Bare TC pattern (without "thermal conductivity" prefix) — use context to verify
    for match in _tc_bare_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0 or val > 5000:
            continue
        in_ctx = _in_context(text, match.start(), ["thermal conduct", "TC ", "W/mK", "W/(m·K)"], 180)
        if not in_ctx:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "thermal", "thermal_conductivity", match.start())
        rec["value"] = val
        rec["unit"] = "W/(m·K)"
        rec["confidence"] = CONFIDENCE_MEDIUM
        records.append(rec)

    # Thermal resistance
    for match in _thermal_resistance_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "thermal", "thermal_resistance", match.start())
        rec["value"] = val
        rec["unit"] = _normalize_unit(match.group("unit"))
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    # Thermal diffusivity
    for match in _diffusivity_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "thermal", "thermal_diffusivity", match.start())
        rec["value"] = val
        rec["unit"] = _normalize_unit(match.group("unit"))
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    # CTE
    for match in _cte_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0 or val > 10000:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "thermal", "cte", match.start())
        rec["value"] = val
        rec["unit"] = "ppm/K"
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    return records


def _rheological_records(paper_id: str, text: str, heading: str, chunk_index: int) -> list[dict]:
    records = []
    norm = _normalize_symbols(text)

    # Complex/Shear viscosity
    for match in _viscosity_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0:
            continue
        is_complex = "complex" in text[max(0, match.start()-100): match.start()].lower()
        is_shear = "shear" in text[max(0, match.start()-100): match.start()].lower()
        if is_complex:
            pname = "complex_viscosity"
        elif is_shear:
            pname = "shear_viscosity"
        else:
            pname = "complex_viscosity"  # default
        rec = _base_record(paper_id, text, heading, chunk_index, "rheological", pname, match.start())
        rec["value"] = val
        rec["unit"] = _normalize_unit(match.group("unit"))
        rec["confidence"] = CONFIDENCE_HIGH if (is_complex or is_shear) else CONFIDENCE_MEDIUM
        records.append(rec)

    # Storage modulus G'
    for match in _storage_modulus_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "rheological", "storage_modulus", match.start())
        rec["value"] = val
        rec["unit"] = match.group("unit").strip()
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    # Loss modulus G"
    for match in _loss_modulus_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "rheological", "loss_modulus", match.start())
        rec["value"] = val
        rec["unit"] = match.group("unit").strip()
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    # Tan delta
    for match in _tan_delta_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0 or val > 100:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "rheological", "tan_delta", match.start())
        rec["value"] = val
        rec["unit"] = ""
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    # Yield stress
    for match in _yield_stress_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0:
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "rheological", "yield_stress", match.start())
        rec["value"] = val
        rec["unit"] = match.group("unit").strip()
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    return records


def _mechanical_records(paper_id: str, text: str, heading: str, chunk_index: int) -> list[dict]:
    records = []
    norm = _normalize_symbols(text)

    extractors = [
        (_tensile_strength_pattern, "tensile_strength"),
        (_youngs_modulus_pattern, "youngs_modulus"),
        (_elongation_pattern, "elongation_at_break"),
        (_flexural_strength_pattern, "flexural_strength"),
        (_flexural_modulus_pattern, "flexural_modulus"),
        (_impact_strength_pattern, "impact_strength"),
        (_hardness_pattern, "hardness"),
        (_compressive_strength_pattern, "compressive_strength"),
        (_shear_strength_pattern, "shear_strength"),
    ]

    for pattern, pname in extractors:
        for match in pattern.finditer(norm):
            val = _to_float(match.group("value"))
            if val is None or val <= 0:
                continue
            # Sanity bounds for each property type
            if pname == "tensile_strength" and val > 20000:
                continue
            if pname == "youngs_modulus" and val > 1000:
                continue
            if pname in ("flexural_strength", "compressive_strength", "shear_strength") and val > 10000:
                continue
            if pname == "elongation_at_break" and val > 2000:
                continue
            if pname == "impact_strength" and val > 10000:
                continue

            rec = _base_record(paper_id, text, heading, chunk_index, "mechanical", pname, match.start())
            rec["value"] = val
            unit_raw = match.groupdict().get("unit")
            rec["unit"] = _normalize_unit(unit_raw) if unit_raw else ""
            rec["confidence"] = CONFIDENCE_HIGH
            records.append(rec)

    return records


def _composition_records(paper_id: str, text: str, heading: str, chunk_index: int) -> list[dict]:
    """Extract filler content as standalone compositional records."""
    records = []
    norm = _normalize_symbols(text)

    for match in _filler_content_pattern.finditer(norm):
        val = _to_float(match.group("value"))
        if val is None or val <= 0 or val > 100:
            continue
        unit_str = match.group("unit").strip()
        # Only create composition records if filler context exists nearby
        if not _in_context(text, match.start(), ["filler", "loading", "content", "filled", "composite", "wt%", "vol%"], 150):
            continue
        rec = _base_record(paper_id, text, heading, chunk_index, "composition", "filler_content", match.start())
        rec["value"] = val
        rec["unit"] = unit_str
        rec["confidence"] = CONFIDENCE_HIGH
        records.append(rec)

    return records


# ─── Main entry point ─────────────────────────────────────────────────

def extract_thermal_conductive_candidates(
    paper_id: str,
    text: str,
    heading: str = "",
    chunk_index: int = 0,
) -> list[dict]:
    """Extract all thermal conductive polymer property candidates from a text chunk."""
    records = [
        *_thermal_records(paper_id, text, heading, chunk_index),
        *_rheological_records(paper_id, text, heading, chunk_index),
        *_mechanical_records(paper_id, text, heading, chunk_index),
        *_composition_records(paper_id, text, heading, chunk_index),
    ]
    # Filter: keep records that have at least a filler or matrix identified
    return [
        r for r in records
        if r.get("filler_name") != "unknown" or r.get("matrix_name")
    ]
