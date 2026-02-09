from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_create_consumption():
    """Test de l'endpoint POST /consumption"""
    response = client.post("/consumption", json={
        "date":"23/01/2025",
        "hour":14,
        "power":55.3
    })
    assert response.status_code == 200

