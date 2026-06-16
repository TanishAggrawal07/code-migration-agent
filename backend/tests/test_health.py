"""
Tests for the /health endpoint.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    """Health endpoint must return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_healthy() -> None:
    """Health response body must contain status=healthy."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "healthy"


def test_health_returns_version() -> None:
    """Health response must include a version field."""
    response = client.get("/health")
    data = response.json()
    assert "version" in data
    assert data["version"] != ""


def test_health_returns_environment() -> None:
    """Health response must include an environment field."""
    response = client.get("/health")
    data = response.json()
    assert "environment" in data
