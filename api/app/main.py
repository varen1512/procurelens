import csv
import io
import math
import os
from collections import defaultdict
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base, make_database
from .ml import classify, find_supplier_matches, normalize_supplier
from .models import Transaction
from .policies import retrieve_policy
from .schemas import PolicyQuestion

REQUIRED_COLUMNS = {"supplier", "description", "amount", "invoice_id", "transaction_date"}


def _duplicate_reason(row: dict, existing: list[Transaction]) -> str:
    invoice = str(row["invoice_id"]).strip().casefold()
    supplier = normalize_supplier(str(row["supplier"]))
    try:
        amount = float(row["amount"])
    except (TypeError, ValueError):
        return ""
    for previous in existing:
        if invoice and invoice == previous.invoice_id.strip().casefold():
            return f"Invoice {row['invoice_id']} already exists"
        same_supplier = supplier == previous.normalized_supplier
        amount_matches = abs(amount - previous.amount) <= max(1.0, previous.amount * 0.01)
        same_day = str(row["transaction_date"]) == previous.transaction_date
        if same_supplier and amount_matches and same_day:
            return "Same supplier, similar amount, and same transaction date"
    return ""


def _seed(session: Session) -> None:
    if session.scalar(select(func.count()).select_from(Transaction)):
        return
    sample = os.path.join(os.path.dirname(__file__), "data", "sample_transactions.csv")
    with open(sample, newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    existing: list[Transaction] = []
    for row in rows:
        category, confidence = classify(row["description"], row["supplier"])
        record = Transaction(
            supplier=row["supplier"], normalized_supplier=normalize_supplier(row["supplier"]),
            description=row["description"], amount=float(row["amount"]), invoice_id=row["invoice_id"],
            transaction_date=row["transaction_date"], category=row.get("category") or category,
            category_confidence=1.0 if row.get("category") else confidence,
            is_duplicate=bool(_duplicate_reason(row, existing)),
            duplicate_reason=_duplicate_reason(row, existing),
        )
        session.add(record)
        existing.append(record)
    session.commit()


def create_app(database_url: str | None = None, seed: bool = True) -> FastAPI:
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./procurelens.db")
    engine, session_factory = make_database(url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(engine)
        if seed:
            with session_factory() as session:
                _seed(session)
        yield
        engine.dispose()

    application = FastAPI(
        title="ProcureLens API", version="1.0.0",
        description="Spend data quality, supplier resolution, classification, and evidence-backed policy retrieval.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(","),
        allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"],
    )

    def get_session():
        with session_factory() as session:
            yield session

    @application.get("/health")
    def health():
        return {"status": "ok", "service": "procurelens-api"}

    @application.get("/api/dashboard")
    def dashboard(session: Session = Depends(get_session)):
        records = list(session.scalars(select(Transaction).order_by(Transaction.transaction_date.desc(), Transaction.id.desc())))
        total = sum(row.amount for row in records)
        by_category: dict[str, float] = defaultdict(float)
        by_supplier: dict[str, float] = defaultdict(float)
        for row in records:
            by_category[row.category] += row.amount
            by_supplier[row.supplier] += row.amount
        duplicates = sum(row.is_duplicate for row in records)
        needs_review = sum(row.category_confidence < 0.55 for row in records)
        quality = max(0, round(100 * (1 - (duplicates + needs_review) / len(records)))) if records else 0
        return {
            "kpis": {
                "total_spend": round(total, 2), "transaction_count": len(records),
                "duplicate_count": duplicates, "needs_review": needs_review, "data_quality_score": quality,
            },
            "categories": [{"name": key, "value": round(value, 2)} for key, value in sorted(by_category.items(), key=lambda item: item[1], reverse=True)],
            "top_suppliers": [{"name": key, "value": round(value, 2)} for key, value in sorted(by_supplier.items(), key=lambda item: item[1], reverse=True)[:5]],
            "recent_transactions": [_serialize(row) for row in records[:10]],
        }

    @application.get("/api/transactions")
    def transactions(
        q: str | None = None,
        duplicates_only: bool = False,
        limit: int = Query(default=100, ge=1, le=500),
        session: Session = Depends(get_session),
    ):
        query = select(Transaction).order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        if duplicates_only:
            query = query.where(Transaction.is_duplicate.is_(True))
        if q:
            pattern = f"%{q.strip()}%"
            query = query.where(Transaction.supplier.ilike(pattern) | Transaction.description.ilike(pattern) | Transaction.invoice_id.ilike(pattern))
        return [_serialize(row) for row in session.scalars(query.limit(limit))]

    @application.post("/api/import")
    async def import_csv(file: UploadFile = File(...), session: Session = Depends(get_session)):
        filename = (file.filename or "").lower()
        if not filename.endswith((".csv", ".xlsx")):
            raise HTTPException(status_code=415, detail="Upload a .csv or .xlsx file.")
        payload = await file.read()
        if len(payload) > 5_000_000:
            raise HTTPException(status_code=413, detail="File must be smaller than 5 MB.")
        try:
            stream = io.BytesIO(payload)
            frame = (pd.read_excel(stream, engine="openpyxl") if filename.endswith(".xlsx") else pd.read_csv(stream))
            frame = frame.rename(columns=lambda name: str(name).strip().lower())
        except Exception as error:
            raise HTTPException(status_code=400, detail=f"Could not parse the uploaded file: {error}") from error
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise HTTPException(status_code=422, detail=f"Missing required columns: {', '.join(sorted(missing))}")
        existing = list(session.scalars(select(Transaction)))
        imported = 0
        rejected = 0
        duplicate_count = 0
        for raw in frame.to_dict(orient="records"):
            try:
                supplier = str(raw.get("supplier", "")).strip()
                description = str(raw.get("description", "")).strip()
                invoice_id = str(raw.get("invoice_id", "")).strip()
                amount = float(raw.get("amount"))
                parsed_date = pd.to_datetime(raw.get("transaction_date"), errors="raise").date().isoformat()
                if (pd.isna(raw.get("supplier")) or pd.isna(raw.get("description")) or pd.isna(raw.get("invoice_id"))
                        or not supplier or not description or not invoice_id or not math.isfinite(amount) or amount < 0):
                    raise ValueError("Required values must be present and amount cannot be negative")
            except (TypeError, ValueError, OverflowError):
                rejected += 1
                continue
            row = {"supplier": supplier, "description": description, "invoice_id": invoice_id, "amount": amount, "transaction_date": parsed_date}
            duplicate_reason = _duplicate_reason(row, existing)
            category_input = raw.get("category")
            category, confidence = classify(description, supplier)
            record = Transaction(
                supplier=supplier, normalized_supplier=normalize_supplier(supplier), description=description,
                amount=amount, invoice_id=invoice_id, transaction_date=parsed_date,
                category=str(category_input).strip() if pd.notna(category_input) and str(category_input).strip() else category,
                category_confidence=1.0 if pd.notna(category_input) and str(category_input).strip() else confidence,
                is_duplicate=bool(duplicate_reason), duplicate_reason=duplicate_reason,
            )
            session.add(record)
            existing.append(record)
            imported += 1
            duplicate_count += bool(duplicate_reason)
        session.commit()
        return {"imported": imported, "rejected": rejected, "duplicates": duplicate_count, "message": f"Imported {imported} rows; {rejected} invalid rows skipped."}

    @application.get("/api/suppliers/{supplier_name}/matches")
    def supplier_matches(supplier_name: str, session: Session = Depends(get_session)):
        names = list(session.scalars(select(Transaction.supplier).distinct()))
        return {"supplier": supplier_name, "matches": find_supplier_matches(supplier_name, names)}

    @application.post("/api/policies/ask")
    def ask_policy(payload: PolicyQuestion):
        sources = retrieve_policy(payload.question)
        if not sources:
            return {"answer": "I couldn't find a matching passage in the bundled policies. Try different keywords or consult the policy owner.", "sources": []}
        answer = "Relevant policy passages are listed below. Confirm the cited policy text before taking action."
        return {"answer": answer, "sources": sources}

    return application


def _serialize(row: Transaction) -> dict:
    return {
        "id": row.id, "supplier": row.supplier, "description": row.description,
        "amount": round(row.amount, 2), "invoice_id": row.invoice_id,
        "transaction_date": row.transaction_date, "category": row.category,
        "category_confidence": round(row.category_confidence, 3),
        "is_duplicate": row.is_duplicate, "duplicate_reason": row.duplicate_reason,
    }


app = create_app()
