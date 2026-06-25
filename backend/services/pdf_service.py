import hashlib
import uuid
import os

from backend.services.paper_structure import split_markdown_sections
from backend.services.metadata_extractor import extract_document_metadata

_converter = None

def _get_converter():
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter
        _converter = DocumentConverter()
    return _converter

def compute_paper_id(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()[:16]

def parse_pdf(file_path: str) -> dict:
    try:
        converter = _get_converter()
        result = converter.convert(file_path)
        markdown_text = result.document.export_to_markdown()
        tables = _extract_tables_from_doc(result)
    except Exception:
        markdown_text = _extract_text_pymupdf(file_path)
        tables = []
    markdown_text = _sanitize_text(markdown_text)
    pdf_metadata = _extract_metadata(file_path)
    metadata = extract_document_metadata(
        markdown_text,
        pdf_metadata=pdf_metadata,
        filename=os.path.basename(file_path),
    )
    sections = split_markdown_sections(markdown_text, document_title=metadata.get("title", ""))
    return {
        "paper_id": compute_paper_id(file_path),
        "metadata": metadata,
        "full_text": markdown_text,
        "sections": sections,
        "tables": tables,
    }

def _extract_text_pymupdf(file_path: str) -> str:
    import fitz
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return _sanitize_text(text)

def _sanitize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\x00", "")
    return "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)

def _extract_metadata(file_path: str) -> dict:
    import fitz
    doc = fitz.open(file_path)
    meta = doc.metadata
    first_page = doc[0].get_text()[:1000] if doc.page_count > 0 else ""
    doc.close()
    title = meta.get("title", "") or (first_page.split("\n")[0] if first_page else "")
    author = meta.get("author", "")
    return {"title": _sanitize_text(title).strip(), "authors": _sanitize_text(author).strip()}

def _split_by_sections(text: str) -> list[dict]:
    return split_markdown_sections(text)

def _extract_tables_from_doc(result) -> list[dict]:
    tables = []
    for table in result.document.tables:
        if hasattr(table, "export_to_dataframe"):
            df = table.export_to_dataframe()
            tables.append(df.to_dict(orient="records"))
    return tables

def save_upload(file_content: bytes, filename: str, upload_dir: str) -> str:
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_content)
    return file_path


async def save_upload_stream(upload_file, upload_dir: str) -> str:
    """Stream upload to disk in 4MB chunks — no memory bloat for large files."""
    os.makedirs(upload_dir, exist_ok=True)
    original_name = upload_file.filename or "upload"
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}_{original_name}")
    with open(file_path, "wb") as f:
        while chunk := await upload_file.read(4 * 1024 * 1024):
            f.write(chunk)
    return file_path
