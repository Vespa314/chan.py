from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_valid_stock():
    response = client.get("/api/search?q=平安")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any("平安" in item for item in data)


def test_search_no_results():
    response = client.get("/api/search?q=zzzznotexist")
    assert response.status_code == 200
    assert response.json() == []


def test_search_empty_query():
    response = client.get("/api/search?q=")
    assert response.status_code == 400
