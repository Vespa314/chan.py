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


def test_chan_analysis_basic():
    response = client.get("/api/chan?code=sz.000001")
    assert response.status_code == 200
    data = response.json()
    assert "klines" in data
    assert len(data["klines"]) > 0
    first_kl = data["klines"][0]
    assert all(k in first_kl for k in ["time", "open", "high", "low", "close"])
    assert "bi" in data
    assert "seg" in data
    assert "zs" in data
    assert "macd" in data
    assert "bsp" in data


def test_chan_invalid_code():
    response = client.get("/api/chan?code=zz.999999")
    assert response.status_code == 404


def test_chan_missing_code():
    response = client.get("/api/chan")
    assert response.status_code == 400
