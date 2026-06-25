import re

HEADING_KINDS = [
    ("abstract", re.compile(r"^abstract$", re.IGNORECASE)),
    ("introduction", re.compile(r"^(introduction|background)$", re.IGNORECASE)),
    ("methods", re.compile(r"^(experimental|experiment|methods?|materials and methods|methodology)$", re.IGNORECASE)),
    ("results", re.compile(r"^(results?|discussion|results and discussion|discussion and results)$", re.IGNORECASE)),
    ("conclusion", re.compile(r"^(conclusions?|summary|outlook)$", re.IGNORECASE)),
    ("references", re.compile(r"^(references?|bibliography)$", re.IGNORECASE)),
    ("acknowledgement", re.compile(r"^(acknowledgements?|acknowledgments?)$", re.IGNORECASE)),
]

CAPTION_PATTERN = re.compile(r"^(fig\.?|figure|table)\s+\d+[\.: ]", re.IGNORECASE)
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,4})\s+(.+?)\s*$")
NUMBER_PREFIX_PATTERN = re.compile(r"^\s*\d+(\.\d+)*[\.)]?\s+")


def _collapse_spaced_letters(value: str) -> str:
    """Collapse spaced-out letters like 'F I G U R E 1' -> 'FIGURE 1'."""
    tokens = value.split()
    if len(tokens) >= 3 and all(len(t) == 1 and t.isalpha() or t.isdigit() for t in tokens):
        return "".join(tokens)
    return value


def _clean_heading(value: str) -> str:
    value = value.strip().strip("#").strip()
    value = _collapse_spaced_letters(value)
    value = NUMBER_PREFIX_PATTERN.sub("", value)
    value = value.strip(" :-\t")
    return re.sub(r"\s+", " ", value)


def _heading_kind(value: str) -> str | None:
    normalized = _clean_heading(value)
    for kind, pattern in HEADING_KINDS:
        if pattern.match(normalized):
            return kind
    return None


def _looks_like_plain_heading(value: str) -> bool:
    cleaned = _clean_heading(value)
    if not cleaned or len(cleaned) > 96:
        return False
    if cleaned.endswith("."):
        return False

    # Standard academic heading
    if _heading_kind(cleaned) is not None:
        return True

    # All-caps line (e.g., "FUNDAMENTALS ON TIM", "SUMMARY AND OUTLOOK")
    if cleaned == cleaned.upper() and len(cleaned) >= 4:
        return True

    # Numbered heading like "2.2.1 Thermal conductivity" or "2 Fundamentals on TIM"
    # Exclude data lines like "11.78 W m−1 K−1" by requiring a word after the number
    raw_collapsed = _collapse_spaced_letters(value.strip())
    if re.match(r'^\d+(\.\d+)*\s+[A-Z][a-z]{2,}', raw_collapsed):
        return True

    # Exclude lines with measurement unit patterns (data, not headings)
    unit_pattern = re.compile(
        r'\b(W\s*m\^-1|W\s*m\s*-1|mm2\s*K\s*W|m2\s*K\s*W|GPa|MPa|wt%|vol%|S/cm|kJ/m)\b',
        re.IGNORECASE
    )
    if unit_pattern.search(cleaned):
        return False

    # Title-case subheading like "Interfacial thermal resistance" (short, no period)
    if len(cleaned) <= 60 and not cleaned.endswith("."):
        words = cleaned.split()
        if len(words) >= 2 and all(w[0].isupper() if w[0].isalpha() else True for w in words[:3]):
            return True

    return False


def _append_section(
    sections: list[dict],
    heading: str,
    kind: str,
    lines: list[str],
    document_title: str,
) -> None:
    content = "\n".join(lines).strip()
    if not content or kind in {"references", "acknowledgement"}:
        return
    sections.append({
        "heading": heading or kind.title(),
        "kind": kind,
        "content": content,
        "document_title": document_title,
    })


def split_markdown_sections(markdown_text: str, document_title: str = "") -> list[dict]:
    sections: list[dict] = []
    current_heading = "Full text"
    current_kind = "body"
    current_lines: list[str] = []

    for raw_line in (markdown_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            if current_lines:
                current_lines.append("")
            continue

        markdown_heading = MARKDOWN_HEADING_PATTERN.match(line)
        heading_text = _clean_heading(markdown_heading.group(2)) if markdown_heading else ""
        heading_kind = _heading_kind(heading_text) if heading_text else None
        is_plain_heading = False

        if not markdown_heading and _looks_like_plain_heading(line):
            heading_text = _clean_heading(line)
            heading_kind = _heading_kind(heading_text)
            is_plain_heading = True

        if heading_text and (heading_kind or markdown_heading or is_plain_heading):
            if current_lines:
                _append_section(sections, current_heading, current_kind, current_lines, document_title)
            current_heading = heading_text
            current_kind = heading_kind or "body"
            current_lines = []
            continue

        if CAPTION_PATTERN.match(line):
            if current_lines:
                _append_section(sections, current_heading, current_kind, current_lines, document_title)
                current_lines = []
            caption_kind = "table" if line.lower().startswith("table") else "figure"
            _append_section(sections, caption_kind.title(), caption_kind, [line], document_title)
            continue

        current_lines.append(line)

    if current_lines:
        _append_section(sections, current_heading, current_kind, current_lines, document_title)

    if not sections and markdown_text.strip():
        sections.append({
            "heading": "Full text",
            "kind": "body",
            "content": markdown_text.strip(),
            "document_title": document_title,
        })
    return sections
