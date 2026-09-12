import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Neon PostgreSQL" in data.get("database", "")

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_integrations_status():
    response = client.get("/api/v1/integrations/status")
    assert response.status_code == 200
    data = response.json()
    assert data["database"]["provider"] == "Neon PostgreSQL"
