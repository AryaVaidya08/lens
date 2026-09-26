"""
Central app configuration.

Holds env-based settings so nothing in the codebase reads os.environ
directly. Swap points from docs/architecture.md (LLM provider, DB path)
should be read from here, not hardcoded at call sites.
"""
from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./hcp.db")
        self.llm_api_key = os.getenv("XAI_API_KEY")
        self.llm_api_base = os.getenv("XAI_API_BASE", "https://api.x.ai/v1")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.drug_docs_path = os.getenv("DRUG_DOCS_PATH", "./data/drug_docs")

settings = Settings()