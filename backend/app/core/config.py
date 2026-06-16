"""
Application configuration using Pydantic Settings.

All values are sourced from environment variables or the .env file.
Sensitive fields (API keys) are never echoed in logs — reference by name only.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object — instantiated once via get_settings()."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ────────────────────────────────────────────────────
    app_name: str = "Code Migration Agent"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    # ── LLM ───────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: int = 60
    gemini_max_retries: int = 3

    # ── Embeddings ────────────────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 32

    # ── Vector store ──────────────────────────────────────────────────
    chroma_db_path: str = "./chroma_db"
    chroma_collection_name: str = "migration_docs"

    # ── File storage ──────────────────────────────────────────────────
    upload_dir: str = "./uploads"
    output_dir: str = "./outputs"
    max_upload_size_mb: int = 100

    # ── Logging ───────────────────────────────────────────────────────
    log_dir: str = "./logs"
    log_max_bytes: int = 10 * 1024 * 1024   # 10 MB
    log_backup_count: int = 5

    # ── CORS ──────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    # ── Computed helpers ──────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> list[str]:
        """Split comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """True when running in production environment."""
        return self.app_env.lower() == "production"

    @property
    def gemini_configured(self) -> bool:
        """True when a non-empty Gemini API key is present."""
        return bool(self.gemini_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()
