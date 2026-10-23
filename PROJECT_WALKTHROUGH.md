# ProcureLens: project walkthrough

This guide explains what happens from the moment someone uploads a spreadsheet to the moment they see a result. It is intended as a code-reading guide and an interview-prep reference.

## The short version

```text
CSV or Excel file
  → React upload form
  → FastAPI validates the file and columns
  → pandas parses rows
  → normalization + fuzzy duplicate checks + ML category prediction
  → SQLAlchemy writes transaction records to PostgreSQL
  → dashboard API aggregates the saved data
  → React displays metrics, categories, flags, and records
```

The policy assistant follows a separate retrieval flow:

```text
Question → TF-IDF vectorization → cosine similarity over policy passages
          → best matching source excerpts and section names
```

## Start by reading these files

1. `api/app/main.py` — application setup and HTTP routes.
2. `api/app/ml.py` — explainable category classifier and fuzzy supplier matching.
3. `api/app/policies.py` — source passages and local retrieval logic.
4. `api/app/models.py` — database record shape.
5. `web/src/App.tsx` — dashboard state, API calls, spreadsheet upload, search, and rendering.
6. `web/src/styles.css` — responsive dashboard styling.
7. `api/tests/test_api.py` — examples of API behavior the project expects to keep working.

## Upload lifecycle

`POST /api/import` receives a multipart CSV or `.xlsx` upload from the Import button in the dashboard.

1. The API accepts `.csv` and `.xlsx` files and caps uploads at 5 MB.
2. pandas parses CSV bytes or reads the first worksheet from an Excel workbook, then trims/lowercases header names.
3. Required fields are checked: `supplier`, `description`, `amount`, `invoice_id`, and `transaction_date`.
4. Each row is validated. Invalid rows are skipped and counted instead of crashing the whole import.
5. Supplier names are normalized by lowercasing, removing punctuation and common legal suffixes, then collapsing spaces.
6. An invoice is flagged when its invoice identifier already exists, or when normalized supplier, close amount, and transaction date match an existing record.
7. The classifier predicts a category if the uploaded sheet did not provide one. A confidence score accompanies each prediction.
8. Valid records are committed through SQLAlchemy. The API returns imported, rejected, and duplicate counts.
9. The UI reloads `/api/dashboard` and `/api/transactions` to show the new rows.

## Classification in plain language

`ml.py` trains a TF-IDF vectorizer and logistic-regression model when the API process starts. The training examples are short descriptions for six spend categories. TF-IDF gives more weight to informative words and phrases. Logistic regression estimates a probability for each category. The highest-probability label and its confidence are returned.

This is a demonstration baseline, not a claim of production-grade accuracy. A real deployment needs labeled company data, an evaluation split, category-specific metrics, drift monitoring, reviewer feedback, and a retraining plan. The UI and stored confidence value make that next step visible.

Supplier matching uses RapidFuzz token similarity to suggest nearby supplier names. A suggestion is a review aid: it does not merge supplier records automatically.

## Policy retrieval in plain language

`policies.py` stores small example policy passages in the repository. TF-IDF converts those passages and the user question into sparse vectors. Cosine similarity ranks passages by their shared terms. The API returns the passage text, source title, section, and score. It does not generate claims beyond the retrieved text and does not call an external AI service.

To extend this responsibly, replace the examples with approved policy documents, preserve document/version metadata, add access controls, and evaluate retrieval against a curated question set before adding generative answers.

## API map

| Route | Request | Result |
|---|---|---|
| `GET /health` | none | Service status |
| `GET /api/dashboard` | none | Spend KPIs, category totals, top suppliers, recent transactions |
| `GET /api/transactions?q=...&duplicates_only=true` | optional filters | Matching saved transactions |
| `POST /api/import` | multipart `.csv` or `.xlsx` file | Import counts and duplicate count |
| `GET /api/suppliers/{name}/matches` | supplier in URL | Similar saved supplier names with scores |
| `POST /api/policies/ask` | JSON `{ "question": "..." }` | Answer note plus relevant source passages |

Interactive OpenAPI documentation is served at `/docs` by FastAPI.

## Database and containers

`models.py` defines a transaction table with raw and normalized supplier names, amount, invoice/date fields, inferred category, confidence, and duplicate-review state. `database.py` creates the SQLAlchemy engine and session factory from `DATABASE_URL`.

Docker Compose starts PostgreSQL, then the API after the database health check, then an Nginx container that serves the built React app and proxies `/api` to FastAPI. For local API work without Docker, the default database is a SQLite file ignored by Git.

## Verification

The pytest suite covers health, empty dashboard behavior, invalid sheet headers, CSV and Excel imports, partial row rejection, duplicate invoice detection, and policy source retrieval. The CI workflow runs the API suite and compiles the TypeScript frontend on pushes and pull requests.

```bash
cd api && pytest -q
cd ../web && npm run build
```

## Interview explanation

> “I built ProcureLens as an end-to-end procurement data-quality workflow. The FastAPI service validates CSV and Excel imports, normalizes supplier names, detects likely duplicate invoices, and applies a confidence-scored TF-IDF/logistic-regression classifier. SQLAlchemy persists the reviewable results in PostgreSQL. A React dashboard exposes the workflow, and a local TF-IDF retrieval feature returns procurement policy excerpts with citations. I added API tests and a CI workflow, and I kept the ML decisions reviewable instead of silently applying low-confidence predictions.”

When describing results, use only measurements you have actually collected. The bundled records are synthetic, and the repository does not claim a measured business or model-accuracy improvement.
