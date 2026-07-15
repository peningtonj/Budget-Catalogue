from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.measure_extraction import extract_measure_records, normalize_portfolio_heading, write_measure_records_sqlite


FIXTURE_PDF = Path(__file__).resolve().parents[1] / "test_measures.pdf"


def test_normalize_portfolio_heading_repairs_ocr_spaced_caps() -> None:
    assert normalize_portfolio_heading("T REASURY") == "TREASURY"
    assert normalize_portfolio_heading("S OCIAL S ERVICES") == "SOCIAL SERVICES"
    assert normalize_portfolio_heading("E DUCATION AND T RAINING") == "EDUCATION AND TRAINING"
    assert normalize_portfolio_heading("A TTORNEY -G ENERAL’S") == "ATTORNEY-GENERAL’S"
    assert normalize_portfolio_heading("Health and Aged Care") == "Health and Aged Care"


def test_extract_measure_records_from_fixture_pdf() -> None:
    assert FIXTURE_PDF.exists(), f"Fixture PDF does not exist at {FIXTURE_PDF}"

    records = extract_measure_records(str(FIXTURE_PDF))

    assert records, "Expected at least one extracted measure from fixture PDF"

    required_keys = {
        "portfolio_name",
        "measure_title",
        "document_section",
        "source_page",
        "full_measure_text",
        "headline_financials",
        "components",
        "related_measures",
    }

    for record in records:
        assert required_keys.issubset(record.keys())
        assert record["document_section"] in {"payment", "receipt"}
        assert isinstance(record["source_page"], int)
        assert isinstance(record["full_measure_text"], str)
        assert isinstance(record["headline_financials"], list)
        assert isinstance(record["components"], list)


def test_extracted_components_keep_dot_dash_hierarchy() -> None:
    records = extract_measure_records(str(FIXTURE_PDF))

    all_components = [component for record in records for component in record["components"]]
    assert all_components, "Expected at least one extracted component"

    # Ensure parser emits both top-level (dot) and nested (dash) components.
    has_dot = any(component["level"] == 1 and component["marker"] == "dot" for component in all_components)
    has_dash = any(component["level"] == 2 and component["marker"] == "dash" for component in all_components)
    assert has_dot
    assert has_dash

    for component in all_components:
        assert component["level"] in {1, 2}
        assert component["marker"] in {"dot", "dash"}
        if component["level"] == 1:
            assert component["parent_ordinal"] is None
        else:
            assert isinstance(component["parent_ordinal"], int)


def test_extraction_can_persist_directly_to_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "catalogue_test.db"

    inserted_count = write_measure_records_sqlite(
        pdf_path=str(FIXTURE_PDF),
        db_path=str(db_path),
        budget_year="2024-25",
        paper_code="MYEFO",
        title="MYEFO test fixture",
    )

    assert inserted_count > 0
    assert db_path.exists()

    with sqlite3.connect(db_path) as connection:
        measure_count = connection.execute("SELECT COUNT(*) FROM measure").fetchone()[0]
        headline_count = connection.execute("SELECT COUNT(*) FROM measure_headline_financial").fetchone()[0]
        component_count = connection.execute("SELECT COUNT(*) FROM measure_component").fetchone()[0]
        nested_component_count = connection.execute(
            "SELECT COUNT(*) FROM measure_component WHERE level = 2"
        ).fetchone()[0]

    assert measure_count == inserted_count
    assert headline_count > 0
    assert component_count > 0
    assert nested_component_count > 0


EXPECTED_RECEIPT_MEASURES = {
    "Building Australia’s Future - A fairer deal for students",
}

EXPECTED_PAYMENT_MEASURES = {
    "Attorney - General’s Portfolio - additional resourcing",
    "Family Law System - improving access",
    "Building Australia’s Future - Building a Better Future Through Considered Infrastructure Investment",
    "Supporting News and Media Diversity",
}

EXPECTED_COMPONENT_COUNTS_BY_MEASURE = {
    "Building Australia’s Future - A fairer deal for students": {"components": 2, "sub_components": 0},
    "Attorney - General’s Portfolio - additional resourcing": {"components": 4, "sub_components": 0},
    "Family Law System - improving access": {"components": 0, "sub_components": 0},
    "Building Australia’s Future - Building a Better Future Through Considered Infrastructure Investment": {
        "components": 3,
        "sub_components": 0,
    },
    "Supporting News and Media Diversity": {"components": 6, "sub_components": 8},
}

EXPECTED_HEADLINE_FINANCIALS_BY_MEASURE = {
    "Building Australia’s Future - A fairer deal for students": [
        ("Receipt", 0, "Department of Employment and Workplace Relations", [0, -19.9, -40.5, -40.4, -41.8]),
        ("Receipt", 0, "Department of Education", [0, -152.6, -197.2, -203.5, -215.1]),
        ("Payment", 1, "Australian Taxation Office", [0, 1.9, 4.7, 0.2, 0.1]),
        ("Payment", 1, "Services Australia", [0, 1.3, 0.3, 0, 0]),
        ("Payment", 1, "Department of Education", [0, 0, 0.4, 0, 0]),
        ("Payment", 1, "Department of Employment and Workplace Relations", [0, 0, 0, 0, 0]),
    ],
    "Attorney - General’s Portfolio - additional resourcing": [
        ("Payment", 0, "Australian Federal Police", [0, 15.1, 14.5, 0, 0]),
        ("Payment", 0, "Office of the Australian Information Commissioner", [0, 0.5, 1.2, 1.3, 0]),
        ("Payment", 0, "Australian Security Intelligence Organisation", [0, 0, 3.9, 0, 0]),
        ("Payment", 0, "Attorney-General’s Department", [0, 0, 1.8, 0, 0]),
        ("Payment", 0, "Various Agencies", [0, 0, 0, 0, 0]),
    ],
    "Family Law System - improving access": [
        ("Payment", 0, "Federal Court of Australia", [0, 0, 14.7, 14.9, 15]),
    ],
    "Building Australia’s Future - Building a Better Future Through Considered Infrastructure Investment": [
        ("Payment", 0, "Department of the Treasury", [0, 375, 160.1, 155.9, 35.4]),
        (
            "Payment",
            0,
            "Department of Infrastructure, Transport, Regional Development, Communications and the Arts",
            [0, 0, 0, 0, 0],
        ),
    ],
    "Supporting News and Media Diversity": [
        (
            "Payment",
            0,
            "Department of Infrastructure, Transport, Regional Development, Communications and the Arts",
            [0, 2.1, 56.6, 55.8, 54.9],
        ),
        ("Payment", 0, "Special Broadcasting Service Corporation", [0, 2, 3.9, 0, 0]),
        ("Payment", 0, "Australian Taxation Office", [0, 0.8, 0.8, 0.3, 0]),
        ("Payment", 0, "National Indigenous Australians Agency", [0, 0, 4, 4, 4]),
        ("Payment", 0, "Australian Broadcasting Corporation", [0, 0, 0, 40.9, 42.2]),
        ("Receipt", 1, "Australian Taxation Office", [0, 0, "..", "..", ".."]),
        ("Receipt", 1, "Australian Communications and Media Authority", [0, 0, -50.2, -0.1, 0]),
    ],
}


EXPECTED_RELATED_MEASURES_BY_MEASURE = {
    "Building Australia's Future - A fairer deal for students": [],
    "Attorney - General's Portfolio - additional resourcing": [
        "Proceeds of Crime Act 2002",
    ],
    "Family Law System - improving access": [],
    "Building Australia's Future - Building a Better Future Through Considered Infrastructure Investment": [
        "Infrastructure Investment Program",
        "Inland Rail Interface Improvement Program",
        "Building a Better Future Through Considered Infrastructure Investment",
    ],
    "Supporting News and Media Diversity": [
        "News Media Assistance Program",
        "News Media Relief Program",
        "Community Broadcasting Program",
        "Indigenous Broadcasting and Media Program",
        "Better Connectivity Plan for Regional and Rural Australia",
    ],
}


def _flatten_headline_financials(headline_financials: list[dict]) -> list[tuple]:
    flattened: list[tuple] = []
    for row in headline_financials:
        values = [
            value_cell["value_numeric_million"] if value_cell["value_kind"] == "numeric" else value_cell["value_raw"]
            for value_cell in row["values"]
        ]
        flattened.append((row["impact_type"], row["is_related"], row["department_name"], values))
    return flattened


def test_fixture_pdf_contains_expected_receipt_measures() -> None:
    records = extract_measure_records(str(FIXTURE_PDF))
    receipt_titles = {r["measure_title"] for r in records if r["document_section"] == "receipt"}
    for expected in EXPECTED_RECEIPT_MEASURES:
        assert expected in receipt_titles, f"Receipt measure not found: {expected!r}"


def test_fixture_pdf_contains_expected_payment_measures() -> None:
    records = extract_measure_records(str(FIXTURE_PDF))
    payment_titles = {r["measure_title"] for r in records if r["document_section"] == "payment"}
    for expected in EXPECTED_PAYMENT_MEASURES:
        assert expected in payment_titles, f"Payment measure not found: {expected!r}"


def test_fixture_pdf_contains_expected_headline_financials_by_measure() -> None:
    records = extract_measure_records(str(FIXTURE_PDF))
    records_by_title = {record["measure_title"]: record for record in records}

    for measure_title, expected_rows in EXPECTED_HEADLINE_FINANCIALS_BY_MEASURE.items():
        assert measure_title in records_by_title, f"Measure not found: {measure_title!r}"
        actual_rows = _flatten_headline_financials(records_by_title[measure_title]["headline_financials"])
        assert actual_rows == expected_rows


def test_fixture_pdf_contains_expected_component_counts_by_measure() -> None:
    records = extract_measure_records(str(FIXTURE_PDF))
    records_by_title = {record["measure_title"]: record for record in records}

    for measure_title, expected_counts in EXPECTED_COMPONENT_COUNTS_BY_MEASURE.items():
        assert measure_title in records_by_title, f"Measure not found: {measure_title!r}"
        components = records_by_title[measure_title]["components"]
        actual_counts = {
            "components": sum(1 for component in components if component["level"] == 1),
            "sub_components": sum(1 for component in components if component["level"] == 2),
        }
        assert actual_counts == expected_counts
