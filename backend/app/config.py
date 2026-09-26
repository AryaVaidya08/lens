"""
Central app configuration.

Holds env-based settings so nothing in the codebase reads os.environ
directly. Swap points from docs/architecture.md (LLM provider, DB path)
should be read from here, not hardcoded at call sites.
"""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Load backend/.env into os.environ without overwriting values already set."""
    path = BACKEND_DIR / ".env"
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


class Settings:
    """
    Env-driven configuration for the backend.

    Every value has a default that works on a laptop with nothing set, so
    `uvicorn app.main:app --reload` runs with zero setup. Set LLM_API_KEY to
    upgrade answers from the offline fallback to a real LLM (see llm/client.py).
    """

    def __init__(self) -> None:
        # Local mongod by default. For Atlas, set MONGODB_URI to the
        # connection string (mongodb+srv://...) and MONGODB_DB if needed.
        self.mongodb_uri: str = os.environ.get(
            "MONGODB_URI", "mongodb://127.0.0.1:27017"
        )
        self.mongodb_db: str = os.environ.get("MONGODB_DB", "lens")
        # Kept so older scripts that still export DATABASE_URL do not crash.
        self.database_url: str = os.environ.get("DATABASE_URL", "")

        self.llm_api_key: str = os.environ.get("LLM_API_KEY", "")
        self.llm_api_base: str = os.environ.get(
            "LLM_API_BASE", "https://api.openai.com/v1"
        )
        self.llm_model: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.llm_timeout_seconds: float = float(os.environ.get("LLM_TIMEOUT", "12"))

        self.drug_docs_path: str = os.environ.get(
            "DRUG_DOCS_PATH", str(BACKEND_DIR / "data" / "drug_docs")
        )
        self.clinic_records_path: str = os.environ.get(
            "CLINIC_RECORDS_PATH", str(BACKEND_DIR / "data" / "clinic_records")
        )
        self.clinic_api_url: str = os.environ.get("CLINIC_API_URL", "")
        self.clinic_api_token: str = os.environ.get("CLINIC_API_TOKEN", "")
        self.retrieval_top_k: int = int(os.environ.get("RETRIEVAL_TOP_K", "4"))

        # Set to "0" to skip seeding on startup (e.g. to keep hand-edited rows).
        self.seed_on_startup: bool = os.environ.get("SEED_ON_STARTUP", "1") != "0"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)


settings = Settings()
