import io

import pandas as pd
from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}", seed=False)
    return TestClient(app)


def test_health_reports_ready(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_starts_empty(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/dashboard")
    assert response.status_code == 200
    assert response.json()["kpis"]["transaction_count"] == 0


def test_import_marks_repeated_invoice_and_skips_invalid_row(tmp_path):
    content = (
        "supplier,description,amount,invoice_id,transaction_date\n"
        "Northstar Cloud,Cloud storage plan,1200,INV-44,2026-10-01\n"
        "Northstar Cloud,Cloud storage plan,1200,INV-44,2026-10-01\n"
        "Bad row,No amount,,INV-45,not-a-date\n"
    )
    with make_client(tmp_path) as client:
        response = client.post("/api/import", files={"file": ("sample.csv", content, "text/csv")})
        dashboard = client.get("/api/dashboard").json()
    assert response.status_code == 200
    assert response.json()["imported"] == 2
    assert response.json()["rejected"] == 1
    assert response.json()["duplicates"] == 1
    assert dashboard["kpis"]["duplicate_count"] == 1


def test_import_rejects_missing_columns(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post("/api/import", files={"file": ("bad.csv", "supplier,amount\nAcme,10\n", "text/csv")})
    assert response.status_code == 422


def test_import_reads_excel_workbook(tmp_path):
    frame = pd.DataFrame([{
        "supplier": "Northstar Cloud", "description": "Cloud storage plan", "amount": 1200,
        "invoice_id": "INV-XLSX", "transaction_date": "2026-10-01",
    }])
    content = io.BytesIO()
    frame.to_excel(content, index=False)
    with make_client(tmp_path) as client:
        response = client.post("/api/import", files={"file": ("sample.xlsx", content.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert response.status_code == 200
    assert response.json()["imported"] == 1


def test_policy_search_returns_citations(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post("/api/policies/ask", json={"question": "How do we handle duplicate invoices?"})
    assert response.status_code == 200
    assert response.json()["sources"]
    assert "Invoice Controls" in response.json()["sources"][0]["source"]
