"""Web App ve REST API testleri - FastAPI endpoint'lerini doğrular."""

from fastapi.testclient import TestClient

from mim_mevzuat.web.app import app

client = TestClient(app)


def test_index_page_returns_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "MİM MEVZUAT" in response.text
    assert "<!DOCTYPE html>" in response.text


def test_api_documents_endpoint():
    response = client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert "documents" in data
    assert len(data["documents"]) >= 2
    titles = [d["title"] for d in data["documents"]]
    assert any("Otopark" in t for t in titles)
    assert any("Planlı Alanlar" in t for t in titles)


def test_api_ask_endpoint_valid_question():
    response = client.post(
        "/api/ask",
        json={
            "query": "Konut projesinde otopark hesabı için hangi bilgiler gereklidir?",
            "jurisdiction": "TR",
            "limit": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Konut projesinde otopark hesabı için hangi bilgiler gereklidir?"
    assert data["validation"]["accepted"] is True
    assert len(data["evidence"]) > 0
    assert len(data["answer"]["citations"]) > 0


def test_api_ask_endpoint_empty_query():
    response = client.post(
        "/api/ask",
        json={"query": "   ", "jurisdiction": "TR"},
    )
    assert response.status_code == 400


def test_api_ask_endpoint_out_of_scope():
    response = client.post(
        "/api/ask",
        json={"query": "Kuantum lazer füzyon motoru ruhsatı", "jurisdiction": "TR"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["validation"]["accepted"] is False
    assert "yeterli dayanak bulunamadı" in data["answer"]["body"].lower()
