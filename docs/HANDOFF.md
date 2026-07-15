# Clean-Slate Handoff

## What This Project Is

This is a rebuild of the current Australian budget RAG prototype into a cleaner catalogue-and-search application.

The new project should start from one clear product statement:
- maintain a structured catalogue of budget measures
- help users find past measures using keyword, semantic, and hybrid search
- support later workflows for summarising selected groups of measures

## What To Preserve From The Prototype

Preserve the domain learning, not the current structure.

The prototype already proved:
- measure extraction from budget PDFs is feasible
- the catalogue model of measures, impacts, components, and related measures is useful
- hybrid retrieval is directionally right for this problem
- users benefit from measure detail pages and structured impact tables

The prototype should be used as a source for:
- extraction logic
- fixture examples
- data model concepts
- ranking heuristics worth porting and testing

Current preservation decision:
- carry the PDF parsing and measure extraction path forward directly from the prototype as the initial implementation baseline
- do only narrow cleanup first: package it cleanly, add fixture tests, and remove duplicated script copies of the same logic

## What To Avoid Porting Directly

Do not preserve these prototype patterns as-is:
- one large backend search module doing retrieval, ranking, shaping, and summarisation together
- one large frontend component handling routing, state, data fetching, filtering, and rendering
- frontend-only advanced search behaviour that is not backed by real API parameters
- duplicated text parsing and aggregation logic across backend and frontend
- environment state, runtime data, and experiments mixed with application source

## Starting Assumptions

- Python backend with FastAPI
- React + TypeScript frontend with Vite
- SQLite for structured catalogue data in the first version
- ChromaDB for semantic retrieval in the first version
- summary generation remains optional and downstream from retrieval

## First Build Priorities

1. Create the clean repository structure.
2. Implement typed backend search contracts.
3. Build keyword, semantic, and hybrid search as explicit backend modes.
4. Build the catalogue search page and measure detail page against that API.
5. Add tests for extraction fixtures and search ranking behaviour.
6. Migrate only the validated extraction and ranking logic from the prototype.

## Suggested First Tickets

1. Define backend `SearchRequest`, `SearchResult`, and `MeasureDetail` schemas.
2. Implement measure repository access against SQLite.
3. Implement a keyword retriever and semantic retriever with a hybrid ranker.
4. Build frontend API client and query hooks.
5. Build catalogue search page with server-backed filters.
6. Build measure detail page from structured backend responses.

## Data Migration Guidance

Use the prototype repository as reference for:
- SQLite schema concepts
- Chroma collection shape
- PDF extraction routines
- sample data fixtures

Specific guidance for PDF parsing:
- treat `backend/measure_extraction.py` in the prototype as the canonical source to migrate first
- keep parsing heuristics functionally unchanged unless fixture tests demonstrate a defect
- consolidate overlapping script logic into the migrated extraction module rather than preserving multiple near-duplicate copies

Do not migrate:
- the local virtual environment
- generated runtime databases as source code
- notebook experiments into product folders
- large dependency lists without reviewing actual runtime need

## Commands For A Fresh Start

From this repository root:

```bash
cd new-project-bootstrap
./setup.sh ../aus-budget-catalogue
```

That creates the new project skeleton in `../aus-budget-catalogue`.

## Minimum Context A New Copilot Instance Should Know

- The target app is a measure catalogue and retrieval tool.
- Retrieval quality and clean API contracts matter more than rapid LLM features.
- Search filters must be backed by the backend, not faked in the UI.
- Backend owns domain parsing and structured measure presentation.
- Frontend should be feature-sliced, not centered on one `App.tsx` file.
- Prototype code is reference material, not the desired final architecture.
