"""
Tests for application configuration.
"""

from app.core.config import get_settings, Settings


def test_settings_singleton() -> None:
    """get_settings() must return the same instance every call."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_default_values() -> None:
    """Key settings must have sensible defaults."""
    s = Settings()
    assert s.gemini_model == "gemini-2.5-flash"
    assert s.embedding_model == "all-MiniLM-L6-v2"
    assert s.chroma_collection_name == "migration_docs"
    assert s.log_level == "INFO"


def test_cors_origins_list_splits_correctly() -> None:
    """cors_origins_list must split comma-separated origins."""
    s = Settings(cors_origins="http://localhost:3000,http://localhost:3001")
    assert "http://localhost:3000" in s.cors_origins_list
    assert "http://localhost:3001" in s.cors_origins_list
    assert len(s.cors_origins_list) == 2


def test_gemini_configured_false_when_empty() -> None:
    """gemini_configured must be False when key is empty string."""
    s = Settings(gemini_api_key="")
    assert s.gemini_configured is False


def test_gemini_configured_true_when_set() -> None:
    """gemini_configured must be True when key is non-empty."""
    s = Settings(gemini_api_key="AIzaSy_fake_key_for_testing")
    assert s.gemini_configured is True


def test_is_production_flag() -> None:
    """is_production must be True only for 'production' env."""
    assert Settings(app_env="production").is_production is True
    assert Settings(app_env="development").is_production is False
    assert Settings(app_env="staging").is_production is False
