# Architecture Overview

Companion note:
- `docs/CHATBOT_ARCHITECTURE.md` describes a competition-oriented chatbot retrieval layer built on top of this catalogue architecture. It is an extension path, not a replacement for the core product structure described here.

## Product Focus

The new project should treat the measure catalogue as the core product.

Primary capability:
- build and maintain a catalogue of Australian budget measures
- search measures with keyword, semantic, and hybrid retrieval
- inspect measure details, impacts, related measures, and source provenance

Secondary capability:
- assemble groups of measures into an analysis workspace
- generate summaries for selected result sets after retrieval is trustworthy

Non-goals for the first cut:
- LLM-first workflows in the main search path
- frontend-only filtering that implies backend capabilities which do not exist
- re-implementing backend parsing rules in the UI

## System Components

### 1. Backend API

Responsibilities:
- expose search, measure detail, and health endpoints
- validate query parameters and response schemas
- delegate business logic to domain services
 
Suggested toolset:
- Python 3.12+
- FastAPI
- Pydantic v2
- Uvicorn
- Ruff
- Pytest

Suggested structure:

```text
backend/app/
  api/
    routers/
      health.py
      search.py
      measures.py
  core/
    config.py
    logging.py
  domain/
    search/
    measures/
    ingestion/
  infrastructure/
    db/
    vector/
```

### 2. Search Domain

Responsibilities:
- define the search request model
- run keyword, semantic, and hybrid retrieval
- apply ranking, filtering, and relevance gates
- return a stable search response contract

Suggested toolset:
- SQL queries for keyword and metadata filtering
- ChromaDB for vector retrieval in the initial version
- repository interfaces so storage can evolve later

Recommended query model:
- `query`
- `mode`: `keyword | semantic | hybrid`
- `scope`: `title | text | both`
- `source_document`
- `portfolio`
- `department`
- `limit`

### 3. Measure Catalogue Domain

Responsibilities:
- provide canonical measure entities and response shapes
- expose measure detail, impacts, related measures, and display-ready narrative blocks
- own summary-table aggregation inputs

Design rule:
- the backend should own display-oriented measure parsing where the output is domain-specific and reused across clients
- the frontend should render structured data, not rediscover structure from raw text

### 4. Ingestion and Extraction Pipeline

Responsibilities:
- ingest source PDFs
- extract structured measures, impacts, components, and related links
- persist catalogue records and vector search documents

Preservation decision:
- keep the existing PDF parsing and extraction logic from the prototype as the initial baseline
- prefer packaging and test cleanup over algorithm rewrites unless a concrete parsing defect is found
- remove duplicated helper copies in standalone scripts by making the backend extraction module the canonical implementation

Suggested toolset:
- pdfplumber for extraction in the first phase
- SQLite for structured catalogue data
- ChromaDB for embeddings and semantic retrieval
- CLI entry points for ingestion and reindexing

Design rule:
- keep extraction logic out of the web app entrypoints
- treat ingestion as a separate operational workflow with fixture-based tests
- keep parser heuristics close together until fixture coverage is in place; do not prematurely split the parsing logic across many modules

### 5. Frontend Application

Responsibilities:
- provide search, filtering, measure detail, and summary workspace flows
- keep routing, data fetching, and presentation clearly separated
- avoid placing all state and rendering in one top-level file

Suggested toolset:
- React
- TypeScript
- Vite
- React Router
- TanStack Query
- ESLint
- Vitest
- Testing Library

Suggested structure:

```text
frontend/src/
  app/
    App.tsx
    routes.tsx
  features/
    catalogue/
      components/
      hooks/
      pages/
    measures/
      components/
      hooks/
      pages/
    summary/
      components/
      hooks/
      pages/
  lib/
    api/
    utils/
    formatting/
```

### 6. Data and Fixtures

Responsibilities:
- store raw and processed source data separately from application code
- maintain stable test fixtures for extraction and ranking behaviour

Suggested structure:

```text
data/
  raw/
  processed/
  sqlite/
  chroma/

tests/fixtures/
```

## Cross-Cutting Design Rules

- Keep API layers thin and domain services explicit.
- Prefer typed request and response schemas over loose dictionaries.
- Separate prototype experiments from product code.
- Add tests around extraction, ranking, and API contracts before broadening features.
- Treat summary generation as a consumer of search results, not as the main architectural driver.
- Keep configuration centralized and environment-driven.

## Initial Tooling Choices

### Backend

Core:
- FastAPI
- Pydantic Settings
- SQLAlchemy Core or direct repository queries over SQLite
- ChromaDB
- OpenAI client only for optional downstream summarisation

Quality:
- Ruff
- Pytest
- MyPy

### Frontend

Core:
- React
- TypeScript
- Vite
- React Router
- TanStack Query

Quality:
- ESLint
- Vitest
- Testing Library

### Developer Experience

- `uv` for Python environment and dependency management
- `npm` for frontend package management
- Makefile or documented scripts for repeatable workflows

## Proposed Initial Repository Layout

```text
<new-project>/
  README.md
  .env.example
  .gitignore
  docs/
    architecture/
    decisions/
  backend/
    pyproject.toml
    app/
    tests/
  frontend/
    package.json
    src/
    tests/
  data/
    raw/
    processed/
    sqlite/
    chroma/
  scripts/
```
