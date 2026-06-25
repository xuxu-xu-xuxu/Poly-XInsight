from backend.services.classify_service import _build_cluster_documents


def test_build_cluster_documents_uses_title_and_full_text_when_abstract_missing():
    rows = [
        ("paper-1", "Halide electrolyte design", "", "The full text discusses lattice softness and conductivity."),
        ("paper-2", "LLZO densification", None, "Dense pellets were obtained after sintering."),
    ]

    papers = _build_cluster_documents(rows)

    assert len(papers) == 2
    assert papers[0]["cluster_text"].startswith("Halide electrolyte design")
    assert "lattice softness" in papers[0]["cluster_text"]
    assert papers[1]["cluster_text"].startswith("LLZO densification")


def test_build_cluster_documents_skips_rows_without_any_clusterable_text():
    rows = [
        ("paper-1", "", "", ""),
        ("paper-2", None, None, None),
    ]

    assert _build_cluster_documents(rows) == []
