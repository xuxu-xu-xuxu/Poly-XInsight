from backend.services.chunking import chunk_text, chunk_sections

def test_chunk_text_basic():
    text = "This is sentence one. This is sentence two. " * 50
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 220

def test_chunk_text_short_input():
    text = "Short text."
    chunks = chunk_text(text, chunk_size=512, overlap=64)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."

def test_chunk_sections_preserves_heading():
    sections = [
        {"heading": "Introduction", "content": "Content of intro. More content."},
        {"heading": "Methods", "content": "Method details here."},
    ]
    chunks = chunk_sections(sections, chunk_size=100, overlap=10)
    intro_chunks = [c for c in chunks if c["heading"] == "Introduction"]
    assert len(intro_chunks) >= 1
    for c in chunks:
        assert "heading" in c
        assert "chunk_index" in c

def test_empty_text():
    chunks = chunk_text("", chunk_size=512, overlap=64)
    assert chunks == []
