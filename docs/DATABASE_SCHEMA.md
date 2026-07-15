# Database Schema

This document describes the first-pass SQLite schema for the budget measure catalogue.

The schema captures:
- headline financials (new money by department, by year)
- full measure text
- measure components (dot points)
- measure sub-components (dash points)

Canonical SQL is in `backend/app/infrastructure/db/schema.sql`.

## Core Tables

### `source_document`

Stores provenance metadata for each budget source file.

Columns:
- `id` (INTEGER, PK)
- `budget_year` (TEXT, required)
- `paper_code` (TEXT)
- `title` (TEXT)
- `file_path` (TEXT)
- `sha256` (TEXT)
- `created_at` (TEXT, defaults to `CURRENT_TIMESTAMP`)

### `measure`

One row per extracted measure.

Columns:
- `id` (INTEGER, PK)
- `source_document_id` (INTEGER, FK -> `source_document.id`, required)
- `portfolio_name` (TEXT, required)
- `measure_title` (TEXT, required)
- `document_section` (TEXT, required; `payment | receipt`)
- `source_page` (INTEGER)
- `full_measure_text` (TEXT, required)
- `created_at` (TEXT, defaults to `CURRENT_TIMESTAMP`)
- `updated_at` (TEXT, defaults to `CURRENT_TIMESTAMP`)

Constraint:
- unique key on (`source_document_id`, `measure_title`, `source_page`)

## Headline Financials

### `measure_headline_financial`

Stores department-level headline lines for a measure.

Columns:
- `id` (INTEGER, PK)
- `measure_id` (INTEGER, FK -> `measure.id`, required)
- `impact_type` (TEXT, required; `Payment | Receipt`)
- `department_name` (TEXT, required)
- `is_related` (INTEGER, required; `0 | 1`)
- `ordinal` (INTEGER, required; display order)

Constraint:
- unique key on (`measure_id`, `impact_type`, `department_name`, `is_related`)

### `measure_headline_financial_value`

Stores one year-value cell per department headline line.

Columns:
- `id` (INTEGER, PK)
- `headline_financial_id` (INTEGER, FK -> `measure_headline_financial.id`, required)
- `fiscal_year` (TEXT, required)
- `value_kind` (TEXT, required; `numeric | nfp | blank | other`)
- `value_numeric_million` (NUMERIC, nullable)
- `value_raw` (TEXT, nullable)

Constraint:
- unique key on (`headline_financial_id`, `fiscal_year`)

## Components and Sub-components

### `measure_component`

Stores both dot-point components and dash sub-components in a single hierarchy.

Columns:
- `id` (INTEGER, PK)
- `measure_id` (INTEGER, FK -> `measure.id`, required)
- `parent_component_id` (INTEGER, FK -> `measure_component.id`, nullable)
- `level` (INTEGER, required; `1 | 2`)
- `marker` (TEXT, required; `dot | dash`)
- `ordinal` (INTEGER, required; display order within level/parent)
- `component_text` (TEXT, required)
- `amount_raw` (TEXT, nullable)
- `amount_million` (NUMERIC, nullable)
- `start_fiscal_year` (TEXT, nullable)
- `duration_years` (INTEGER, nullable)
- `allocation_status` (TEXT, required; `allocated | unallocated | unknown`)

Hierarchy constraints:
- level 1 (`dot`) cannot have a parent
- level 2 (`dash`) must have a parent

### `measure_component_impact`

Stores yearly impact values for a component or sub-component.

Columns:
- `id` (INTEGER, PK)
- `component_id` (INTEGER, FK -> `measure_component.id`, required)
- `impact_type` (TEXT, required; `Payment | Receipt`)
- `fiscal_year` (TEXT, required)
- `value_kind` (TEXT, required; `numeric | nfp | blank | other`)
- `value_numeric_million` (NUMERIC, nullable)
- `value_raw` (TEXT, nullable)

Constraint:
- unique key on (`component_id`, `impact_type`, `fiscal_year`)

## Relationship Summary

- one `source_document` has many `measure`
- one `measure` has many `measure_headline_financial`
- one `measure_headline_financial` has many `measure_headline_financial_value`
- one `measure` has many `measure_component`
- one level-1 `measure_component` may have many level-2 `measure_component` children
- one `measure_component` has many `measure_component_impact`

## Creating the Database

From repository root:

```bash
python scripts/create_sqlite_db.py
```

Default output database path:
- `data/sqlite/catalogue.db`
