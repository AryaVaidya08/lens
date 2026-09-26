"""
Use an in-memory Mongo mock so pytest never needs a running mongod
and never writes into the demo `lens` database.
"""

import os

os.environ["MONGODB_URI"] = "mongomock://localhost"
os.environ["MONGODB_DB"] = "lens_test"
os.environ.setdefault("SEED_ON_STARTUP", "1")
