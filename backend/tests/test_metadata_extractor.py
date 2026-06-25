from backend.services.metadata_extractor import extract_document_metadata


def test_extracts_title_authors_year_journal_and_abstract_from_pdf_text_head():
    text = """Review
Solid-state lithium batteries: Safety and prospects
Yong Guo a,1, Shichao Wu a,b,c,d,1,*, Yan-Bing He e, Feiyu Kang e, Liquan Chen f, Hong Li f,*,
Quan-Hong Yang a,b,c,*
a Nanoyang Group, State Key Laboratory of Chemical Engineering, Tianjin University, China
H I G H L I G H T S
A R T I C L E I N F O
Keywords:
Solid-state lithium batteries
A B S T R A C T
Solid-state lithium batteries are flourishing due to their excellent potential energy density.
Substantial efforts have been made to improve their electrochemical performance.
1. Introduction
Developing batteries with high energy density and safety is essential.
Contents lists available at ScienceDirect
eScience 2 (2022) 138-163
"""

    metadata = extract_document_metadata(
        text,
        pdf_metadata={"title": "092d121f42094789839290482cc2b5a5_1-s2.0-S2667141722000209-main.pdf"},
        filename="092d121f42094789839290482cc2b5a5_1-s2.0-S2667141722000209-main.pdf",
    )

    assert metadata["title"] == "Solid-state lithium batteries: Safety and prospects"
    assert metadata["authors"].startswith("Yong Guo, Shichao Wu, Yan-Bing He")
    assert metadata["year"] == 2022
    assert metadata["journal"] == "eScience"
    assert metadata["abstract"].startswith("Solid-state lithium batteries are flourishing")


def test_uses_clean_pdf_metadata_before_filename_fallback():
    metadata = extract_document_metadata(
        "Short body without a visible title.",
        pdf_metadata={"title": "A Real Paper Title", "authors": "Jane Doe"},
        filename="hash_reference.pdf",
    )

    assert metadata["title"] == "A Real Paper Title"
    assert metadata["authors"] == "Jane Doe"
