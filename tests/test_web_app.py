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


def test_api_jurisdictions_returns_all_81_provinces():
    response = client.get("/api/jurisdictions")
    assert response.status_code == 200
    data = response.json()
    assert "provinces" in data
    assert len(data["provinces"]) == 81
    # Adana 01, Ankara 06, Istanbul 34, Duzce 81
    names = [p["name"] for p in data["provinces"]]
    assert "Adana" in names
    assert "Ankara" in names
    assert "İstanbul" in names
    assert "İzmir" in names
    assert "Konya" in names
    assert "Muğla" in names
    assert "Trabzon" in names
    assert "Düzce" in names

    # Toplam ilçe sayısı
    total_districts = sum(len(p["districts"]) for p in data["provinces"])
    assert total_districts >= 900


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
