"""
SQLAlchemy models.

Fields only — no query methods here. Query logic belongs in the route
or db access functions that use these models, not on the models
themselves.

Owned by: Backend & data lane.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    barcode = Column(String, nullable=True, index=True)
    generic_name = Column(String, nullable=True)


class Engagement(Base):
    __tablename__ = "engagements"

    hcp_id = Column(String, ForeignKey("hcps.id"), primary_key=True)
    drug_id = Column(String, ForeignKey("drugs.id"), primary_key=True)
    touch_count = Column(Integer, nullable=False, default=0)
    last_seen = Column(DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))
