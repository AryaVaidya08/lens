"""
Central app configuration.

Holds env-based settings so nothing in the codebase reads os.environ
directly. Swap points from docs/architecture.md (LLM provider, DB path)
should be read from here, not hardcoded at call sites.
"""


class Settings:
    """
    Env-driven configuration for the backend.

    TODO: implement — load these from environment variables (e.g. via
    pydantic-settings or plain os.environ.get with defaults):
      - database_url: str        (SQLite file path, e.g. "sqlite:///./hcp.db")
      - llm_api_key: str          (sponsor LLM API key)
      - llm_api_base: str         (sponsor LLM API base URL, if applicable)
      - drug_docs_path: str       (path to backend/data/drug_docs/)
    """

    # TODO: implement
    pass


settings = Settings()
