"""
Database access used by routes.

MongoDB is the store. `get_db` is the FastAPI dependency every route
should take — do not open a client in a route file.
"""

from app.db.mongo import close_client, ensure_indexes, get_database, get_db

__all__ = ["close_client", "ensure_indexes", "get_database", "get_db"]
