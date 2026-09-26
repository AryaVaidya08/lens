"""
Central app configuration.

Holds env-based settings so nothing in the codebase reads os.environ
directly. Swap points from docs/architecture.md (LLM provider, DB path)
should be read from here, not hardcoded at call sites.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings:
    """Env-driven configuration for the backend."""

    def __init__(self) -> None:
        self.database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./hcp.db")
        self.llm_api_key: str = os.environ.get("XAI_API_KEY", "")
        self.llm_api_base: str = os.environ.get("XAI_API_BASE", "https://api.x.ai/v1")
        self.openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
        self.drug_docs_path: str = os.environ.get(
            "DRUG_DOCS_PATH",
            str(BACKEND_ROOT / "data" / "drug_docs"),
        )
        self.embedding_cache_path: str = os.environ.get(
            "EMBEDDING_CACHE_PATH",
            str(BACKEND_ROOT / "data" / ".embedding_cache.npz"),
        )
        self.embedding_model: str = os.environ.get(
            "EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )


settings = Settings()
