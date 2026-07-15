# Australian Budget Catalogue

Australian Budget Catalogue is a searchable catalogue of Australian budget measures, with a FastAPI backend, a React frontend, and supporting ingestion workflows for turning source budget documents into structured records.

The project is built around three connected workflows:

- ingest and structure budget source material
- search and inspect measures through catalogue and detail views
- support grounded chatbot retrieval over the measure catalogue

## What the application includes

- catalogue search across budget measures
- measure detail pages with related measures, source provenance, and structured impacts
- semantic retrieval backed by ChromaDB
- a chatbot flow that expands user questions, searches the catalogue, filters candidate measures, and returns grounded results
- local ingestion and extraction tooling for rebuilding structured data stores

## Repository layout

```text
backend/     FastAPI API, domain services, extraction logic, and data access
frontend/    React + TypeScript application
data/        Local raw inputs, processed outputs, SQLite database, and Chroma index
docs/        Architecture and handoff documentation
scripts/     Operational scripts such as index/database rebuild helpers
```

## Data note

The source budget files are not included in this repository.

If you want to run ingestion workflows or rebuild local data stores, you need to provide the raw source documents yourself. The project expects those files to exist locally under `data/raw/`, for example in directories such as `data/raw/Budget Paper 2/` and `data/raw/MYEFO/`.

Generated local artefacts such as SQLite databases, processed outputs, and Chroma indexes live under `data/` and may depend on those source files being present.

## Requirements

- Python 3.12+
- `uv` for backend environment management
- Node.js for the frontend

## Quick start

### Backend

```bash
cd backend
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will usually be available at `http://127.0.0.1:5173`.

## Chatbot configuration

The chatbot flow uses OpenAI. To enable it locally, add an `.env` file with the required API key and any model overrides used by the backend configuration.

## Useful development commands

### Backend tests

```bash
cd backend
uv run pytest
```

### Frontend production build

```bash
cd frontend
npm run build
```
