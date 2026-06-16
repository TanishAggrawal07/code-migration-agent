"""
Basic health endpoint test.
Run: pytest tests/test_health.py -v
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_healthy():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data
