from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app

SAMPLE_PDF = Path(__file__).resolve().parents[3] / "sample_docs" / "aldermoor_procurement_policy.pdf"


def test_health_endpoint_reports_ok_and_mode():
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mode"] in ("local", "cloud")


def test_rag_ask_endpoint_answers_from_indexed_documents(indexed_documents):
    response = TestClient(app).post(
        "/api/rag/ask",
        json={"query": "Who must sign off on purchases above EUR 250,000 at Aldermoor?"},
    )

    assert response.status_code == 200
    assert "department head" in response.json()["answer"].lower()


def test_rag_upload_endpoint_indexes_pdf():
    with open(SAMPLE_PDF, "rb") as pdf:
        response = TestClient(app).post(
            "/api/rag/upload",
            files={"files": ("aldermoor_procurement_policy.pdf", pdf, "application/pdf")},
        )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["filename"] == "aldermoor_procurement_policy.pdf"
    assert result["status"] == "ingested"
    assert result["chunks"] > 0


def test_rag_uploads_endpoint_lists_upload_history():
    response = TestClient(app).get("/api/rag/uploads")

    assert response.status_code == 200
    assert isinstance(response.json()["uploads"], list)


def test_agent_audit_endpoint_returns_cfo_memo():
    response = TestClient(app).post(
        "/api/agent/audit",
        json={
            "request_text": (
                "Purchase order: 2 industrial servo motors from Siemens AG (Germany), "
                "total EUR 12,000, invoice rate EUR_USD 1.08, for the filling line upgrade."
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert {"risk_result", "tax_result", "control_result", "cfo_memo"} <= set(body)
