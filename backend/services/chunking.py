import re
from typing import List


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    sentences = _split_sentences(text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) <= chunk_size:
            current += sent
        else:
            if current:
                chunks.append(current.strip())
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = overlap_text + sent
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _chunk_context_header(section: dict) -> str:
    parts = []
    title = (section.get("document_title") or "").strip()
    heading = (section.get("heading") or "").strip()
    if title:
        parts.append(f"Title: {title}")
    if heading:
        parts.append(f"Section: {heading}")
    return "\n".join(parts)


def chunk_sections(sections: list[dict], chunk_size: int = 512, overlap: int = 64) -> list[dict]:
    result = []
    for sec in sections:
        if sec.get("kind") == "references":
            continue
        sec_chunks = chunk_text(sec["content"], chunk_size, overlap)
        for i, c in enumerate(sec_chunks):
            header = _chunk_context_header(sec)
            text = f"{header}\n\n{c}" if header else c
            result.append({
                "text": text,
                "heading": sec["heading"],
                "section": sec.get("heading", ""),
                "chunk_type": sec.get("kind", "body"),
                "chunk_index": i,
                "token_count": max(1, len(text) // 4),
            })
    return result


def _split_sentences(text: str) -> List[str]:
    pattern = re.compile(r"(?<=[。！？!?])\s*|(?<=[.!?])\s+|\n{2,}")
    parts = pattern.split(text)
    result = []
    for part in parts:
        if part.strip():
            result.append(part)
    if not result:
        result = [text]
    return result
