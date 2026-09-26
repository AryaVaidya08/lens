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

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.config import settings

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

        return mongomock.MongoClient()

    client = MongoClient(uri, serverSelectionTimeoutMS=4000)
    try:
        client.admin.command("ping")
    except PyMongoError as exc:
        raise RuntimeError(
            "Cannot reach MongoDB at %s. Start mongod locally or set "
            "MONGODB_URI to your Atlas connection string." % uri
        ) from exc
    return client


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
    db.sessions.create_index("token_hash", unique=True)
    db.sessions.create_index("hcp_id")
    db.sessions.create_index("expires_at")
    db.password_resets.create_index("token_hash", unique=True)
    db.password_resets.create_index("hcp_id")
    db.password_resets.create_index("expires_at")


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
