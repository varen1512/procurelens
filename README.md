# ProcureLens

**AI-assisted spend data quality, supplier resolution, and policy search.**

ProcureLens turns messy procurement spreadsheets into a reviewable workflow: upload transaction CSV or Excel files, normalize supplier names, flag likely duplicate invoices, classify spend descriptions, inspect the data through a dashboard, and search procurement policies with source-backed answers. The included vendor names and transactions are synthetic demo data.

This is a portfolio project built to demonstrate Python data processing, practical machine learning, entity resolution, REST API design, SQL persistence, a React interface, containerization, and automated checks.

## What it does

- **Spreadsheet intake:** validates uploaded CSV or `.xlsx` transactions and reports row-level issues.
- **Supplier resolution:** normalizes names and finds likely duplicate suppliers using fuzzy matching.
- **Spend classification:** trains a TF-IDF + logistic-regression classifier on a small, explainable seed taxonomy; returns a confidence score and supports human review.
- **Invoice duplicate detection:** flags records with a matching invoice identifier or a close supplier/amount/date match.
- **Policy search:** retrieves passages from bundled policy documents using TF-IDF and returns the matching source excerpts. It works locally and does not require an external LLM key.
- **Dashboard and API:** exposes spend summaries, category totals, data-quality flags, spreadsheet import, and policy search through FastAPI and a React UI.
- **Persistence:** uses PostgreSQL in Docker Compose and SQLite by default for local development.

## Quick start

### Docker Compose

```bash
docker compose up --build
```

Open `http://localhost:8080`. The API docs are at `http://localhost:8000/docs`.

### Local development

API (Python 3.11+):

```bash
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Web UI (Node 20+):

```bash
cd web
npm install
npm run dev
```

Vite proxies `/api` requests to `http://localhost:8000`.

## Spreadsheet format

Required columns in CSV and Excel: `supplier`, `description`, `amount`, `invoice_id`, `transaction_date`.
Optional column: `category` (used as a label when provided). A sample file is in `api/app/data/sample_transactions.csv`.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service health |
| GET | `/api/dashboard` | Spend, category, supplier, and quality summaries |
| GET | `/api/transactions` | Filterable transaction records |
| POST | `/api/import` | Import and analyze a CSV or `.xlsx` upload |
| POST | `/api/policies/ask` | Retrieve relevant policy passages for a question |

## Design notes

Classification and policy retrieval are intentionally transparent baselines. Classification uses a small built-in labeled taxonomy and returns confidence so reviewers can verify uncertain results. Policy search returns source passages rather than inventing unsupported answers. For production use, the next steps would be tenant isolation, access control, larger curated training data, audit logging, and a reviewed human-in-the-loop workflow.

## Learn how it works

Read [PROJECT_WALKTHROUGH.md](PROJECT_WALKTHROUGH.md) for the request flow, data model, ML methods, API map, and a guided tour of where to start reading the code.

## Privacy and secrets

The repository contains only source code, synthetic sample records, and documentation. Do not commit resumes, job trackers, customer data, `.env` files, API tokens, or database dumps. The Compose password defaults to a local development value; set `POSTGRES_PASSWORD` to a secret stored outside GitHub for any shared deployment.

## Project structure

```text
api/       FastAPI service, SQLAlchemy persistence, ML/data-quality pipeline, tests
web/       React + TypeScript dashboard
docker-compose.yml
```

## Checks

```bash
cd api && pytest
cd ../web && npm run build
```

## License

MIT. See [LICENSE](LICENSE).
