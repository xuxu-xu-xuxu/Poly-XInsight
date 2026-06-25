import os
import re

NOISE_LINES = {
    "review",
    "article",
    "research article",
    "contents lists available at sciencedirect",
    "highlights",
    "h i g h l i g h t s",
    "graphical abstract",
    "g r a p h i c a l a b s t r a c t",
    "article info",
    "a r t i c l e i n f o",
    "keywords",
    "abstract",
    "a b s t r a c t",
}


def _compact_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _clean_filename_title(filename: str) -> str:
    base = os.path.basename(filename or "")
    base = re.sub(r"\.pdf$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"^[0-9a-f]{16,}[_-]+", "", base, flags=re.IGNORECASE)
    return _compact_spaces(base.replace("_", " ").replace("-", " "))


def _is_bad_title(value: str) -> bool:
    title = _compact_spaces(value)
    lower = title.lower()
    if not title or len(title) < 8 or len(title) > 240:
        return True
    if lower in NOISE_LINES:
        return True
    if lower.endswith(".pdf") or "reference.pdf" in lower:
        return True
    if re.search(r"[0-9a-f]{16,}", lower):
        return True
    if len(re.findall(r"[A-Za-z][A-Za-z-]+", title)) < 3:
        return True
    return False


def _candidate_lines(text: str, max_lines: int = 80) -> list[str]:
    lines = []
    for line in (text or "").splitlines():
        cleaned = _compact_spaces(line.strip("# "))
        if cleaned:
            lines.append(cleaned)
        if len(lines) >= max_lines:
            break
    return lines


def _find_title(lines: list[str], pdf_title: str, filename: str) -> tuple[str, int | None]:
    if not _is_bad_title(pdf_title):
        return _compact_spaces(pdf_title), None

    for index, line in enumerate(lines):
        lower = line.lower()
        if lower in NOISE_LINES:
            continue
        if lower.startswith(("http://", "https://", "doi:", "keywords:")):
            continue
        if "@" in line or "university" in lower or "institute" in lower:
            continue
        if not _is_bad_title(line):
            return line, index

    fallback = _clean_filename_title(filename)
    return fallback or "Untitled paper", None


def _clean_authors(value: str) -> str:
    value = re.sub(r"\*+", "", value)
    value = re.sub(r"\s+[a-z](?:,[a-z0-9]+)*(?:,\d+)?", "", value)
    value = re.sub(r"\b\d+\b", "", value)
    value = value.replace(",,", ",")
    value = _compact_spaces(value)
    return value.strip(" ,")


def _find_authors(lines: list[str], title_index: int | None, pdf_authors: str) -> str:
    if pdf_authors and len(pdf_authors.strip()) > 3:
        return _compact_spaces(pdf_authors)
    if title_index is None:
        return ""

    author_lines = []
    for line in lines[title_index + 1 : title_index + 5]:
        lower = line.lower()
        if lower in NOISE_LINES:
            break
        if lower.startswith(("a ", "b ", "c ", "department", "school", "institute", "university")):
            break
        if "@" in line or "doi.org" in lower:
            break
        author_lines.append(line)
    return _clean_authors(" ".join(author_lines))


def _find_journal_year(text: str) -> tuple[str, int | None]:
    head = text[:8000]
    journal_match = re.search(r"\b([A-Za-z][A-Za-z .&-]{2,80})\s+\d+\s*\(((?:19|20)\d{2})\)", head)
    if journal_match:
        return _compact_spaces(journal_match.group(1)), int(journal_match.group(2))

    year_match = re.search(r"(?:©|copyright|available online|accepted|received)[^\n]{0,80}\b((?:19|20)\d{2})\b", head, re.IGNORECASE)
    if year_match:
        return "", int(year_match.group(1))
    return "", None


def _find_abstract(lines: list[str]) -> str:
    start = None
    for index, line in enumerate(lines):
        if line.lower() in {"abstract", "a b s t r a c t"}:
            start = index + 1
            break
    if start is None:
        return ""

    body = []
    for line in lines[start:]:
        lower = line.lower()
        if re.match(r"^\d+\.?\s+(introduction|background)", lower):
            break
        if lower in {"introduction", "1. introduction", "references"}:
            break
        if lower in NOISE_LINES and lower not in {"keywords"}:
            continue
        body.append(line)
        if len(" ".join(body)) > 1800:
            break
    return _compact_spaces(" ".join(body))


def extract_document_metadata(
    full_text: str,
    pdf_metadata: dict | None = None,
    filename: str = "",
) -> dict:
    pdf_metadata = pdf_metadata or {}
    lines = _candidate_lines(full_text)
    title, title_index = _find_title(lines, pdf_metadata.get("title", ""), filename)
    authors = _find_authors(lines, title_index, pdf_metadata.get("authors", "") or pdf_metadata.get("author", ""))
    journal, year = _find_journal_year(full_text)
    abstract = _find_abstract(lines)

    return {
        "title": title,
        "authors": authors or None,
        "year": year,
        "journal": journal or None,
        "abstract": abstract or None,
    }
