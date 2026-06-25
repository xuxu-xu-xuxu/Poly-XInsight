from backend.services.entity_mining import extract_chunk_entities, unique_entity_records


def test_extracts_compact_entities_from_solid_electrolyte_chunk():
    text = (
        "LLZO garnet electrolyte shows high ionic conductivity measured by EIS. "
        "The electrochemical window was evaluated by LSV."
    )

    records = extract_chunk_entities(
        paper_id="paper-1",
        text=text,
        heading="Results",
        chunk_index=4,
    )

    labels = {(record["entity_type"], record["attributes"]["kind"]) for record in records}

    assert ("LLZO", "material") in labels
    assert ("garnet", "material_family") in labels
    assert ("ionic conductivity", "property") in labels
    assert ("electrochemical window", "property") in labels
    assert ("EIS", "method") in labels
    assert ("LSV", "method") in labels
    assert records[0]["attributes"]["source"] == "entity_mining"
    assert records[0]["attributes"]["source_chunk_id"] == "paper-1_4"


def test_deduplicates_entities_per_paper_label_and_kind():
    text = "LLZO was measured by EIS. LLZO impedance spectra confirmed the LLZO result."

    records = extract_chunk_entities("paper-1", text, "Results", 1)
    deduped = unique_entity_records(records)

    llzo_records = [
        record for record in deduped
        if record["paper_id"] == "paper-1" and record["entity_type"] == "LLZO"
    ]

    assert len(llzo_records) == 1


def test_rejects_formula_tokens_with_sentence_tail_words():
    text = "O2.Although the method worked, Li2SiO4-contained samples were excluded."

    records = extract_chunk_entities("paper-2", text, "Results", 1)

    assert records == []


def test_rejects_unbalanced_formula_tokens():
    records = extract_chunk_entities("paper-3", "The LiI(001 surface was discussed.", "Results", 1)

    assert records == []
