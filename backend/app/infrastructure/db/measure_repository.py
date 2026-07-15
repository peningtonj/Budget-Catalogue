from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from app.domain.measures.models import (
    MeasureComponent,
    MeasureComponentImpactValue,
    MeasureDetail,
    MeasureHeadlineFinancial,
    MeasureHeadlineFinancialValue,
    MeasureIncomingRelatedMeasure,
    MeasureRelatedMeasure,
    MeasureSearchFilters,
    MeasureSearchItem,
)
from app.domain.chat.models import ChatMeasureCandidate


def default_db_path() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "sqlite" / "catalogue.db"


def _titlecase_portfolio_token(match: re.Match[str]) -> str:
    token = match.group(0)
    return token[:1].upper() + token[1:].lower()


def normalize_portfolio_name(value: str | None) -> str:
    if not value:
        return ""

    normalized = " ".join(value.replace("\u00a0", " ").split())
    normalized = normalized.replace("’", "'")
    normalized = re.sub(r"\s*,\s*", ", ", normalized)
    normalized = re.sub(r"\s*-\s*", "-", normalized)
    normalized = re.sub(r"[A-Za-z]+(?:'[A-Za-z]+)?", _titlecase_portfolio_token, normalized)
    normalized = re.sub(r"\b(And|Of|The)\b", lambda match: match.group(1).lower(), normalized)
    return normalized


def normalize_measure_title_match(value: str | None) -> str:
    if not value:
        return ""

    normalized = " ".join(value.replace("\u00a0", " ").split())
    normalized = normalized.replace("’", "'")
    normalized = re.sub(r"\s*-\s*", "-", normalized)
    return normalized.casefold()


class MeasureRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.create_function("normalize_portfolio", 1, normalize_portfolio_name, deterministic=True)
        connection.create_function("normalize_measure_title_match", 1, normalize_measure_title_match, deterministic=True)
        return connection

    def list_portfolios(self) -> list[str]:
        if not self.db_path.exists():
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT normalize_portfolio(portfolio_name) AS portfolio_name
                FROM measure
                WHERE normalize_portfolio(portfolio_name) != ''
                ORDER BY normalize_portfolio(portfolio_name) ASC
                """
            ).fetchall()
        return [str(row["portfolio_name"]) for row in rows]

    def list_budget_rounds(self) -> list[str]:
        if not self.db_path.exists():
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT title AS budget_round
                FROM source_document
                WHERE title IS NOT NULL AND title != ''
                ORDER BY title DESC
                """
            ).fetchall()
        return [str(row["budget_round"]) for row in rows]

    def count_measures(self) -> int:
        if not self.db_path.exists():
            return 0

        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS measure_count FROM measure").fetchone()
        return int(row["measure_count"] if row is not None else 0)

    def list_index_documents(self) -> list[ChatMeasureCandidate]:
        if not self.db_path.exists():
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    m.id AS measure_id,
                    m.measure_title,
                    normalize_portfolio(m.portfolio_name) AS portfolio_name,
                    COALESCE(sd.title, sd.paper_code, sd.budget_year) AS budget_round,
                    m.document_section,
                    m.source_page,
                    SUM(
                        CASE
                            WHEN mhfv.value_kind = 'numeric' THEN mhfv.value_numeric_million
                            ELSE NULL
                        END
                    ) AS headline_financial_total_million,
                    m.full_measure_text
                FROM measure AS m
                JOIN source_document AS sd ON sd.id = m.source_document_id
                LEFT JOIN measure_headline_financial AS mhf ON mhf.measure_id = m.id
                LEFT JOIN measure_headline_financial_value AS mhfv ON mhfv.headline_financial_id = mhf.id
                GROUP BY
                    m.id,
                    m.measure_title,
                    normalize_portfolio(m.portfolio_name),
                    COALESCE(sd.title, sd.paper_code, sd.budget_year),
                    m.document_section,
                    m.source_page,
                    m.full_measure_text
                ORDER BY m.id ASC
                """
            ).fetchall()
        return [
            ChatMeasureCandidate(
                **dict(row),
                semantic_score=0.0,
            )
            for row in rows
        ]

    def search(self, filters: MeasureSearchFilters) -> list[MeasureSearchItem]:
        if not self.db_path.exists():
            return []

        normalized_query = filters.query.strip()
        wildcard_query = f"%{normalized_query}%"
        prefix_query = f"{normalized_query}%"
        normalized_portfolio_query = f"%{normalize_portfolio_name(normalized_query)}%"
        normalized_portfolio_prefix_query = f"{normalize_portfolio_name(normalized_query)}%"
        normalized_portfolio_filter = normalize_portfolio_name(filters.portfolio_name)
        budget_rounds = [budget_round for budget_round in filters.budget_rounds if budget_round]
        budget_round_clause = ""
        params: list[object] = [
            normalized_query,
            wildcard_query,
            wildcard_query,
            normalized_portfolio_query,
            filters.document_section,
            filters.document_section,
            normalized_portfolio_filter or None,
            normalized_portfolio_filter or None,
        ]

        if budget_rounds:
            placeholders = ", ".join("?" for _ in budget_rounds)
            budget_round_clause = f"\n              AND sd.title IN ({placeholders})"
            params.extend(budget_rounds)

        sql = """
            SELECT
                m.id,
                m.measure_title,
                normalize_portfolio(m.portfolio_name) AS portfolio_name,
                sd.title AS budget_round,
                m.document_section,
                m.source_page,
                SUM(
                    CASE
                        WHEN mhfv.value_kind = 'numeric' THEN mhfv.value_numeric_million
                        ELSE NULL
                    END
                ) AS headline_financial_total_million,
                m.full_measure_text
            FROM measure m
            JOIN source_document sd ON sd.id = m.source_document_id
            LEFT JOIN measure_headline_financial mhf ON mhf.measure_id = m.id
            LEFT JOIN measure_headline_financial_value mhfv ON mhfv.headline_financial_id = mhf.id
            WHERE (? = ''
                OR m.measure_title LIKE ? COLLATE NOCASE
                OR m.full_measure_text LIKE ? COLLATE NOCASE
                                OR normalize_portfolio(m.portfolio_name) LIKE ? COLLATE NOCASE)
              AND (? IS NULL OR m.document_section = ?)
                            AND (? IS NULL OR normalize_portfolio(m.portfolio_name) = ?)
                """ + budget_round_clause + """
            GROUP BY
                m.id,
                m.measure_title,
                                normalize_portfolio(m.portfolio_name),
                sd.title,
                m.document_section,
                m.source_page,
                m.full_measure_text
            ORDER BY
                CASE
                    WHEN m.measure_title = ? THEN 0
                    WHEN m.measure_title LIKE ? COLLATE NOCASE THEN 1
                    WHEN normalize_portfolio(m.portfolio_name) LIKE ? COLLATE NOCASE THEN 2
                    ELSE 3
                END,
                m.measure_title ASC
            LIMIT ?
        """

        params.extend(
            [
                normalized_query,
                prefix_query,
                normalized_portfolio_prefix_query,
                filters.limit,
            ]
        )

        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()

        return [MeasureSearchItem.model_validate(dict(row)) for row in rows]

    def get_detail(self, measure_id: int) -> MeasureDetail | None:
        if not self.db_path.exists():
            return None

        with self._connect() as connection:
            measure_row = connection.execute(
                """
              SELECT m.id, m.measure_title, normalize_portfolio(m.portfolio_name) AS portfolio_name,
                  COALESCE(sd.title, sd.paper_code, sd.budget_year) AS budget_round,
                  m.document_section, m.source_page, m.full_measure_text
              FROM measure AS m
              JOIN source_document AS sd ON sd.id = m.source_document_id
              WHERE m.id = ?
                """,
                (measure_id,),
            ).fetchone()
            if measure_row is None:
                return None

            headline_financials = self._fetch_headline_financials(connection, measure_id)
            components = self._fetch_components(connection, measure_id)
            related_measures = self._fetch_related_measures(connection, measure_id)
            incoming_related_measures = self._fetch_incoming_related_measures(connection, measure_id)

        return MeasureDetail(
            **dict(measure_row),
            headline_financials=headline_financials,
            components=components,
            related_measures=related_measures,
            incoming_related_measures=incoming_related_measures,
        )

    def _fetch_headline_financials(self, connection: sqlite3.Connection, measure_id: int) -> list[MeasureHeadlineFinancial]:
        rows = connection.execute(
            """
            SELECT id, impact_type, is_related, department_name, ordinal
            FROM measure_headline_financial
            WHERE measure_id = ?
            ORDER BY ordinal ASC
            """,
            (measure_id,),
        ).fetchall()
        results: list[MeasureHeadlineFinancial] = []
        for row in rows:
            value_rows = connection.execute(
                """
                SELECT fiscal_year, value_kind, value_numeric_million, value_raw
                FROM measure_headline_financial_value
                WHERE headline_financial_id = ?
                ORDER BY fiscal_year ASC
                """,
                (row["id"],),
            ).fetchall()
            results.append(
                MeasureHeadlineFinancial(
                    impact_type=str(row["impact_type"]),
                    is_related=bool(row["is_related"]),
                    department_name=str(row["department_name"]),
                    ordinal=int(row["ordinal"]),
                    values=[MeasureHeadlineFinancialValue.model_validate(dict(value_row)) for value_row in value_rows],
                )
            )
        return results

    def _fetch_components(self, connection: sqlite3.Connection, measure_id: int) -> list[MeasureComponent]:
        rows = connection.execute(
            """
            SELECT id, parent_component_id, level, marker, ordinal, component_text, amount_raw,
                   amount_million, start_fiscal_year, duration_years, allocation_status
            FROM measure_component
            WHERE measure_id = ?
            ORDER BY level ASC, COALESCE(parent_component_id, id) ASC, ordinal ASC
            """,
            (measure_id,),
        ).fetchall()
        results: list[MeasureComponent] = []
        for row in rows:
            impact_rows = connection.execute(
                """
                SELECT fiscal_year, value_kind, value_numeric_million, value_raw
                FROM measure_component_impact
                WHERE component_id = ?
                ORDER BY fiscal_year ASC
                """,
                (row["id"],),
            ).fetchall()
            results.append(
                MeasureComponent(
                    **dict(row),
                    impact_values=[MeasureComponentImpactValue.model_validate(dict(impact_row)) for impact_row in impact_rows],
                )
            )
        return results

    def _fetch_related_measures(self, connection: sqlite3.Connection, measure_id: int) -> list[MeasureRelatedMeasure]:
        rows = connection.execute(
            """
            SELECT
                r.ordinal,
                r.related_measure_title,
                (
                    SELECT candidate.id
                    FROM measure AS candidate
                    JOIN measure AS owner ON owner.id = r.measure_id
                    WHERE normalize_measure_title_match(candidate.measure_title) = normalize_measure_title_match(r.related_measure_title)
                    ORDER BY
                        CASE WHEN candidate.source_document_id = owner.source_document_id THEN 0 ELSE 1 END,
                        candidate.id ASC
                    LIMIT 1
                ) AS linked_measure_id
            FROM measure_related_measure AS r
            WHERE r.measure_id = ?
            ORDER BY r.ordinal ASC
            """,
            (measure_id,),
        ).fetchall()
        return [MeasureRelatedMeasure.model_validate(dict(row)) for row in rows]

    def _fetch_incoming_related_measures(
        self, connection: sqlite3.Connection, measure_id: int
    ) -> list[MeasureIncomingRelatedMeasure]:
        rows = connection.execute(
            """
            SELECT DISTINCT
                owner.id AS measure_id,
                owner.measure_title,
                normalize_portfolio(owner.portfolio_name) AS portfolio_name,
                COALESCE(sd.title, sd.paper_code, sd.budget_year) AS budget_round
            FROM measure_related_measure AS related
            JOIN measure AS owner ON owner.id = related.measure_id
            JOIN measure AS current_measure ON current_measure.id = ?
            JOIN source_document AS sd ON sd.id = owner.source_document_id
            WHERE normalize_measure_title_match(related.related_measure_title) = normalize_measure_title_match(current_measure.measure_title)
              AND owner.id != current_measure.id
            ORDER BY budget_round DESC, owner.measure_title ASC, owner.id ASC
            """,
            (measure_id,),
        ).fetchall()
        return [MeasureIncomingRelatedMeasure.model_validate(dict(row)) for row in rows]
