"""
Central app configuration.

Holds env-based settings so nothing in the codebase reads os.environ
directly. Swap points from docs/architecture.md (LLM provider, DB path)
should be read from here, not hardcoded at call sites.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
HOME_MONGO_ENV = Path.home() / ".lens-mongodb.env"
ACCOUNTS_COLLECTION = "hcps"
from dotenv import load_dotenv

load_dotenv()

def _apply_env_line(raw: str, environ: dict) -> None:
    line = raw.strip()
    if line.startswith("export "):
        line = line[7:].strip()
    if not line or line.startswith("#") or "=" not in line:
        return
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip().strip("'").strip('"')
    if key and key not in environ:
        environ[key] = value


def _load_env_file(path: Path, environ: dict) -> None:
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        _apply_env_line(raw, environ)


def _load_dotenv() -> None:
    """Load Mongo settings without clobbering values already in the process.

    backend/.env first, then ~/.lens-mongodb.env for any keys still unset.
    Tests set MONGODB_URI before import, so they keep mongomock.
    """
    _load_env_file(BACKEND_DIR / ".env", os.environ)
    _load_env_file(HOME_MONGO_ENV, os.environ)


def mongodb_kind(uri: str) -> str:
    text = (uri or "").lower()
    if text.startswith("mongomock"):
        return "mongomock"
    if "mongodb.net" in text or text.startswith("mongodb+srv://"):
        return "atlas"
    if "127.0.0.1" in text or "localhost" in text:
        return "localhost"
    return "other"


_load_dotenv()
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings:
    """Env-driven configuration for the backend."""

    def __init__(self) -> None:
        # MongoDB
        self.mongodb_uri: str = os.environ.get(
            "MONGODB_URI", "mongodb://127.0.0.1:27017"
        )
        self.mongodb_db: str = os.environ.get("MONGODB_DB", "lens")
        self.accounts_collection: str = ACCOUNTS_COLLECTION
        # Kept so older scripts that still export DATABASE_URL do not crash.
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
        # Low-effort grok-4.7 scan rewrites of 3 passages landed around 25s.
        # Keep the cap above that. iOS getSummary waits longer than this.
        self.llm_timeout_seconds: float = float(
            os.environ.get("LLM_TIMEOUT", "45")
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

    @property
    def mongodb_kind(self) -> str:
        return mongodb_kind(self.mongodb_uri)


settings = Settings()