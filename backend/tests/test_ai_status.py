"""
Tests for GET /api/ai/status and GET /api/ai/services.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_ai_status_returns_200() -> None:
    """AI status endpoint must return HTTP 200."""
    response = client.get("/api/ai/status")
    assert response.status_code == 200


def test_ai_status_has_expected_keys() -> None:
    """AI status response must contain all four service keys."""
    response = client.get("/api/ai/status")
    data = response.json()
    for key in ("gemini", "embeddings", "chromadb", "tree_sitter", "all_healthy"):
        assert key in data, f"Missing key: {key}"


def test_ai_status_values_are_bool() -> None:
    """All values in the AI status response must be booleans."""
    response = client.get("/api/ai/status")
    data = response.json()
    for key in ("gemini", "embeddings", "chromadb", "tree_sitter", "all_healthy"):
        assert isinstance(data[key], bool), f"{key} must be a bool, got {type(data[key])}"


def test_ai_services_detail_returns_200() -> None:
    """AI services detail endpoint must return HTTP 200."""
    response = client.get("/api/ai/services")
    assert response.status_code == 200


def test_ai_services_detail_structure() -> None:
    """AI services detail must contain all four service blocks."""
    response = client.get("/api/ai/services")
    data = response.json()
    for key in ("gemini", "embeddings", "chromadb", "tree_sitter"):
        assert key in data, f"Missing service block: {key}"


def test_ai_services_gemini_has_model() -> None:
    """Gemini block must expose model name and api_key_configured."""
    response = client.get("/api/ai/services")
    data = response.json()
    assert "model" in data["gemini"]
    assert "api_key_configured" in data["gemini"]


def test_ai_services_embeddings_has_model() -> None:
    """Embeddings block must expose model name and device."""
    response = client.get("/api/ai/services")
    data = response.json()
    assert "model" in data["embeddings"]
    assert "device" in data["embeddings"]
