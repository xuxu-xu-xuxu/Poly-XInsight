from backend.services.chunking import chunk_sections
from backend.services.paper_structure import split_markdown_sections


def test_split_markdown_sections_keeps_core_sections_and_drops_references():
    markdown = """# A Solid Electrolyte Paper

Abstract
Fast lithium transport is observed.

## Introduction
Solid electrolytes need stable interfaces.

Experimental
Cells were assembled with LLZO pellets.

Figure 1. Ionic conductivity comparison.

References
[1] Noise that should not be embedded.
"""

    sections = split_markdown_sections(markdown, document_title="A Solid Electrolyte Paper")

    assert [section["kind"] for section in sections] == [
        "abstract",
        "introduction",
        "methods",
        "figure",
    ]
    assert sections[0]["heading"] == "Abstract"
    assert sections[-1]["content"] == "Figure 1. Ionic conductivity comparison."
    assert all("Noise" not in section["content"] for section in sections)


def test_chunk_sections_adds_light_context_and_chunk_type():
    sections = [
        {
            "heading": "Results and Discussion",
            "kind": "results",
            "content": "Ionic conductivity increased after interface modification. " * 12,
            "document_title": "A Solid Electrolyte Paper",
        }
    ]

    chunks = chunk_sections(sections, chunk_size=180, overlap=30)

    assert len(chunks) > 1
    assert chunks[0]["chunk_type"] == "results"
    assert chunks[0]["heading"] == "Results and Discussion"
    assert chunks[0]["text"].startswith("Title: A Solid Electrolyte Paper\nSection: Results and Discussion")
    assert "Ionic conductivity increased" in chunks[0]["text"]
