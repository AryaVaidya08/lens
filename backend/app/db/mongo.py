"""
MongoDB client.

Collections (database name from settings.mongodb_db, default `lens`):

  hcps         clinician account + ordered patient_ids
  patients     one chart per patient; hcp_id is the owning doctor
  drugs        { _id, name, barcode }
  engagements  { _id: "hcp_id:drug_id", hcp_id, drug_id, touch_count, last_seen }
  chats        { hcp_id, drug_id, question, answer, asked_at }

`_id` on hcps/drugs is the same string the iOS app already sends
(`hcp_001`, `adderall`), so nothing in the API contract changes.
"""

import logging

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.config import settings

logger = logging.getLogger("uvicorn.error")

_client = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = _connect()
    return _client


def _connect():
    uri = settings.mongodb_uri
    if uri.startswith("mongomock"):
        import mongomock

        client = mongomock.MongoClient()
    else:
        client = MongoClient(uri, serverSelectionTimeoutMS=4000)
        try:
            client.admin.command("ping")
        except PyMongoError as exc:
            raise RuntimeError(
                "Cannot reach MongoDB (%s). Start mongod locally or set "
                "MONGODB_URI to your Atlas connection string."
                % settings.mongodb_kind
            ) from exc
    logger.info(
        "Mongo accounts persist in db=%s collection=%s kind=%s",
        settings.mongodb_db,
        settings.accounts_collection,
        settings.mongodb_kind,
    )
    return client


def store_info() -> dict:
    """Safe-to-log /status fields. Never includes the connection string."""
    return {
        "database": "mongodb",
        "mongodb_db": settings.mongodb_db,
        "mongodb_kind": settings.mongodb_kind,
        "accounts_collection": settings.accounts_collection,
    }


def get_database() -> Database:
    return get_client()[settings.mongodb_db]


def get_db():
    """FastAPI dependency — one Database handle per request."""
    yield get_database()


def ensure_indexes(db: Database) -> None:
    db.hcps.create_index("specialty")
    db.hcps.create_index("email", unique=True)
    db.drugs.create_index("barcode")
    db.engagements.create_index([("hcp_id", 1), ("drug_id", 1)], unique=True)
    db.chats.create_index([("hcp_id", 1), ("asked_at", -1)])
    db.patients.create_index("hcp_id")
    db.medication_reviews.create_index([("hcp_id", 1), ("patient_id", 1), ("updated_at", -1)])
    db.medication_access.create_index([("hcp_id", 1), ("patient_id", 1), ("updated_at", -1)])
    db.sessions.create_index("token_hash", unique=True)
    db.sessions.create_index("hcp_id")
    db.sessions.create_index("expires_at")
    db.password_resets.create_index("token_hash", unique=True)
    db.password_resets.create_index("hcp_id")
    db.password_resets.create_index("expires_at")


def close_client() -> None:
    global _client
    if _client is None:
        return
    # Tests share one in-memory mongomock across many TestClient
    # lifespans. Closing it mid-suite wipes seed data and later
    # logins fail against an empty database.
    if settings.mongodb_uri.startswith("mongomock"):
        return
    _client.close()
    _client = None
