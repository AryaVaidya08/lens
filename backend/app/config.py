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
        # MongoDB
        self.mongodb_uri: str = os.environ.get(
            "MONGODB_URI", "mongodb://127.0.0.1:27017"
        )
        self.mongodb_db: str = os.environ.get("MONGODB_DB", "lens")

        # Kept for compatibility with older scripts.
        self.database_url: str = os.environ.get("DATABASE_URL", "")

        # LLM: xAI/Grok is the active provider.
        self.llm_api_key: str = os.environ.get(
            "XAI_API_KEY",
            os.environ.get("LLM_API_KEY", ""),
        )
        self.llm_api_base: str = os.environ.get(
            "XAI_API_BASE",
            os.environ.get("LLM_API_BASE", "https://api.x.ai/v1"),
        )
        self.llm_model: str = os.environ.get(
            "XAI_MODEL",
            os.environ.get("LLM_MODEL", "grok-4.7"),
        )
        self.llm_timeout_seconds: float = float(
            os.environ.get("LLM_TIMEOUT", "20")
        )

        # Kept for compatibility if OpenAI is used later.
        self.openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")

        # Drug reference documents / embeddings.
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

        # Clinic / patient data.
        self.clinic_records_path: str = os.environ.get(
            "CLINIC_RECORDS_PATH",
            str(BACKEND_ROOT / "data" / "clinic_records"),
        )
        self.clinic_api_url: str = os.environ.get("CLINIC_API_URL", "")
        self.clinic_api_token: str = os.environ.get("CLINIC_API_TOKEN", "")

        # Retrieval / startup behavior.
        self.retrieval_top_k: int = int(
            os.environ.get("RETRIEVAL_TOP_K", "4")
        )
        self.seed_on_startup: bool = (
            os.environ.get("SEED_ON_STARTUP", "1") != "0"
        )

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)


settings = Settings()