from backend.services.solid_electrolyte_properties.extractor import extract_property_candidates
from backend.services.solid_electrolyte_properties.analytics import (
    element_frequency_rows,
    conductivity_by_element_rows,
)


def test_extracts_conductivity_and_electrochemical_window_candidates():
    text = (
        "The LLZO solid electrolyte delivered an ionic conductivity of "
        "1.2 x 10-3 S cm-1 at 25 C. The electrochemical stability window "
        "was 0-5.0 V versus Li/Li+."
    )

    records = extract_property_candidates(
        paper_id="paper-1",
        text=text,
        heading="Results",
        chunk_index=3,
    )

    conductivity = [record for record in records if record["property_name"] == "ionic_conductivity"]
    window = [record for record in records if record["property_name"] == "electrochemical_window"]

    assert conductivity[0]["material_name"] == "LLZO"
    assert conductivity[0]["value"] == 1.2e-3
    assert conductivity[0]["unit"] == "S/cm"
    assert conductivity[0]["temperature_value"] == 25
    assert conductivity[0]["source_chunk_id"] == "paper-1_3"

    assert window[0]["value"] == 0
    assert window[0]["value_max"] == 5.0
    assert window[0]["unit"] == "V"


def test_extracts_stable_up_to_voltage_window():
    text = "LGPS is electrochemically stable up to 4.5 V against Li/Li+ in the tested cell."

    records = extract_property_candidates("paper-2", text, "Discussion", 1)

    assert records[0]["property_name"] == "electrochemical_window"
    assert records[0]["material_name"] == "LGPS"
    assert records[0]["value_max"] == 4.5


def test_extracts_formula_and_negative_exponent_from_unicode_notation():
    text = (
        "The argyrodite Li6PS5Cl solid electrolyte reached an ionic conductivity "
        "of 3.2 × 10−3 S cm−1 at 25 °C."
    )

    records = extract_property_candidates("paper-3", text, "Results", 2)
    conductivity = [record for record in records if record["property_name"] == "ionic_conductivity"]

    assert len(conductivity) == 1
    assert conductivity[0]["material_name"] == "Li6PS5Cl"
    assert conductivity[0]["normalized_formula"] == "Li6PS5Cl"
    assert conductivity[0]["value"] == 3.2e-3
    assert conductivity[0]["raw_value"] == 3.2
    assert conductivity[0]["raw_unit"] == "S/cm"


def test_strips_sentence_tail_from_formula():
    text = "Li3.25Ge0.25P0.75S4). This sample reached 2.5 x 10-3 S cm-1."

    records = extract_property_candidates("paper-4", text, "Results", 1)
    conductivity = [record for record in records if record["property_name"] == "ionic_conductivity"]

    assert conductivity[0]["material_name"] == "Li3.25Ge0.25P0.75S4"
    assert conductivity[0]["normalized_formula"] == "Li3.25Ge0.25P0.75S4"


def test_rejects_implausible_conductivity_values():
    text = "The overview states high Li+ conductivities of 103-102 S cm1 at room temperature."

    records = extract_property_candidates("paper-5", text, "Introduction", 1)

    assert [record for record in records if record["property_name"] == "ionic_conductivity"] == []


def test_rejects_property_records_without_material_formula():
    text = "The solid electrolyte film showed high ionic conductivity of 1 mS cm-1."

    records = extract_property_candidates("paper-6", text, "Results", 1)

    assert records == []


def test_property_rows_support_element_frequency_and_conductivity_statistics():
    records = [
        {"normalized_formula": "Li6PS5Cl", "material_name": "Li6PS5Cl", "value": 1e-3},
        {"normalized_formula": "Li7La3Zr2O12", "material_name": "Li7La3Zr2O12", "value": 2e-3},
        {"normalized_formula": "", "material_name": "unknown", "value": 5e-3},
    ]

    frequency = element_frequency_rows(records)
    avg = conductivity_by_element_rows(records, "avg")
    median = conductivity_by_element_rows(records, "median")

    assert {"element": "Li", "count": 2} in frequency
    assert {"element": "Cl", "count": 1} in frequency
    assert next(row for row in avg if row["element"] == "Li")["conductivity_s_cm"] == 1.5e-3
    assert next(row for row in median if row["element"] == "Li")["conductivity_s_cm"] == 1.5e-3
