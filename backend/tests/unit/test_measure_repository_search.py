from __future__ import annotations

import sqlite3
from pathlib import Path

from app.domain.measures.models import MeasureSearchFilters
from app.infrastructure.db.measure_repository import MeasureRepository, normalize_measure_title_match, normalize_portfolio_name


def _create_schema(connection: sqlite3.Connection) -> None:
    schema_path = Path(__file__).resolve().parents[2] / "app" / "infrastructure" / "db" / "schema.sql"
    connection.executescript(schema_path.read_text(encoding="utf-8"))


def _seed_measure(
    connection: sqlite3.Connection,
    *,
    source_document_id: int,
    portfolio_name: str,
    measure_title: str,
    document_section: str = "payment",
    source_page: int = 1,
    full_measure_text: str = "Budget measure text",
) -> None:
    connection.execute(
        """
        INSERT INTO measure (
            source_document_id,
            portfolio_name,
            measure_title,
            document_section,
            source_page,
            full_measure_text
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source_document_id, portfolio_name, measure_title, document_section, source_page, full_measure_text),
    )


def test_search_filters_by_multiple_budget_rounds(tmp_path: Path) -> None:
    db_path = tmp_path / "catalogue.db"

    with sqlite3.connect(db_path) as connection:
        _create_schema(connection)
        connection.execute(
            "INSERT INTO source_document (id, budget_year, paper_code, title, file_path) VALUES (1, '2023-24', 'BP2', '2023-24 BP2', '/tmp/2023-24.pdf')"
        )
        connection.execute(
            "INSERT INTO source_document (id, budget_year, paper_code, title, file_path) VALUES (2, '2024-25', 'MYEFO', 'Mid-Year Economic and Fiscal Outlook 2024-25', '/tmp/2024-25.pdf')"
        )
        connection.execute(
            "INSERT INTO source_document (id, budget_year, paper_code, title, file_path) VALUES (3, '2025-26', 'BP2', '2025-26 BP2', '/tmp/2025-26.pdf')"
        )
        _seed_measure(connection, source_document_id=1, portfolio_name='Treasury', measure_title='Student measure')
        _seed_measure(connection, source_document_id=2, portfolio_name='Treasury', measure_title='Industry measure')
        _seed_measure(connection, source_document_id=3, portfolio_name='Health', measure_title='Hospital measure')
        connection.commit()

    repository = MeasureRepository(db_path=db_path)

    results = repository.search(
        MeasureSearchFilters(
            query="",
            budget_rounds=["2023-24 BP2", "Mid-Year Economic and Fiscal Outlook 2024-25"],
            limit=20,
        )
    )

    assert [result.budget_round for result in results] == [
        "Mid-Year Economic and Fiscal Outlook 2024-25",
        "2023-24 BP2",
    ]
    assert {result.measure_title for result in results} == {"Student measure", "Industry measure"}


def test_list_budget_rounds_returns_distinct_titles(tmp_path: Path) -> None:
    db_path = tmp_path / "catalogue.db"

    with sqlite3.connect(db_path) as connection:
        _create_schema(connection)
        connection.execute(
            "INSERT INTO source_document (budget_year, paper_code, title, file_path) VALUES ('2024-25', 'BP2', '2024-25 BP2', '/tmp/a.pdf')"
        )
        connection.execute(
            "INSERT INTO source_document (budget_year, paper_code, title, file_path) VALUES ('2024-25', 'MYEFO', 'Mid-Year Economic and Fiscal Outlook 2024-25', '/tmp/b.pdf')"
        )
        connection.execute(
            "INSERT INTO source_document (budget_year, paper_code, title, file_path) VALUES ('2024-25', 'BP2', '2024-25 BP2', '/tmp/c.pdf')"
        )
        connection.commit()

    repository = MeasureRepository(db_path=db_path)

    assert repository.list_budget_rounds() == [
        'Mid-Year Economic and Fiscal Outlook 2024-25',
        '2024-25 BP2',
    ]


def test_list_portfolios_returns_normalized_distinct_values(tmp_path: Path) -> None:
    db_path = tmp_path / "catalogue.db"

    with sqlite3.connect(db_path) as connection:
        _create_schema(connection)
        connection.execute(
            "INSERT INTO source_document (id, budget_year, paper_code, title, file_path) VALUES (1, '2024-25', 'BP2', '2024-25 BP2', '/tmp/a.pdf')"
        )
        _seed_measure(connection, source_document_id=1, portfolio_name='TREASURY', measure_title='Uppercase measure')
        _seed_measure(connection, source_document_id=1, portfolio_name=' Treasury  ', measure_title='Trimmed measure')
        _seed_measure(connection, source_document_id=1, portfolio_name="ATTORNEY-GENERAL’S", measure_title='Apostrophe measure')
        connection.commit()

    repository = MeasureRepository(db_path=db_path)

    assert repository.list_portfolios() == ["Attorney-General's", 'Treasury']


def test_search_normalizes_portfolio_filter_and_result_values(tmp_path: Path) -> None:
    db_path = tmp_path / "catalogue.db"

    with sqlite3.connect(db_path) as connection:
        _create_schema(connection)
        connection.execute(
            "INSERT INTO source_document (id, budget_year, paper_code, title, file_path) VALUES (1, '2024-25', 'BP2', '2024-25 BP2', '/tmp/a.pdf')"
        )
        _seed_measure(connection, source_document_id=1, portfolio_name='TREASURY', measure_title='Uppercase measure')
        _seed_measure(connection, source_document_id=1, portfolio_name='Treasury  ', measure_title='Whitespace measure')
        _seed_measure(connection, source_document_id=1, portfolio_name='Health', measure_title='Other measure')
        connection.commit()

    repository = MeasureRepository(db_path=db_path)

    results = repository.search(MeasureSearchFilters(query='', portfolio_name=' treasury ', limit=20))

    assert [result.measure_title for result in results] == ['Uppercase measure', 'Whitespace measure']
    assert {result.portfolio_name for result in results} == {'Treasury'}


def test_normalize_portfolio_name_cleans_case_and_spacing() -> None:
    assert normalize_portfolio_name(' TREASURY  ') == 'Treasury'
    assert normalize_portfolio_name('ATTORNEY-GENERAL’S') == "Attorney-General's"
    assert normalize_portfolio_name('Agriculture , Water AND THE ENVIRONMENT') == 'Agriculture, Water and the Environment'


def test_normalize_measure_title_match_collapses_hyphen_spacing() -> None:
    assert normalize_measure_title_match('Workforce Australia - micro - policy amendments') == normalize_measure_title_match(
        'Workforce Australia - micro-policy amendments'
    )


def test_get_detail_links_related_measures_to_catalogue_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "catalogue.db"

    with sqlite3.connect(db_path) as connection:
        _create_schema(connection)
        connection.execute(
            "INSERT INTO source_document (id, budget_year, paper_code, title, file_path) VALUES (1, '2024-25', 'BP2', '2024-25 BP2', '/tmp/a.pdf')"
        )
        connection.execute(
            "INSERT INTO source_document (id, budget_year, paper_code, title, file_path) VALUES (2, '2024-25', 'MYEFO', '2024-25 MYEFO', '/tmp/b.pdf')"
        )
        _seed_measure(connection, source_document_id=1, portfolio_name='Treasury', measure_title='Current measure')
        _seed_measure(connection, source_document_id=1, portfolio_name='Treasury', measure_title='Linked-measure')
        _seed_measure(connection, source_document_id=2, portfolio_name='Treasury', measure_title='Linked-measure')
        _seed_measure(connection, source_document_id=2, portfolio_name='Health', measure_title='Incoming measure')
        connection.execute(
            "INSERT INTO measure_related_measure (measure_id, ordinal, related_measure_title) VALUES (1, 1, 'Linked - measure')"
        )
        connection.execute(
            "INSERT INTO measure_related_measure (measure_id, ordinal, related_measure_title) VALUES (4, 1, 'Current measure')"
        )
        connection.commit()

    repository = MeasureRepository(db_path=db_path)
    detail = repository.get_detail(1)

    assert detail is not None
    assert [related_measure.model_dump() for related_measure in detail.related_measures] == [
        {
            'ordinal': 1,
            'related_measure_title': 'Linked - measure',
            'linked_measure_id': 2,
        }
    ]
    assert [related_measure.model_dump() for related_measure in detail.incoming_related_measures] == [
        {
            'measure_id': 4,
            'measure_title': 'Incoming measure',
            'portfolio_name': 'Health',
            'budget_round': '2024-25 MYEFO',
        }
    ]