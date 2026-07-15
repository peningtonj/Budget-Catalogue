# Australian Budget Catalogue

Clean-slate rebuild of the measure catalogue and retrieval application.

## Intended workflows

- ingest budget source documents into a structured catalogue
- search measures with keyword, semantic, and hybrid retrieval
- inspect measure details and affected entities
- build later summary workflows on top of selected measures

## Quick start

### Backend

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
