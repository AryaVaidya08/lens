"""
SQLAlchemy models.

Fields only — no query methods here. Query logic belongs in the route
or db access functions that use these models, not on the models
themselves.

Owned by: Backend & data lane.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class HCP(Base):
    __tablename__ = "hcps"

    # TODO: implement
    id = Column(String, primary_key=True)
    name = Column(String)
    specialty = Column(String)


class Drug(Base):
    __tablename__ = "drugs"

    # TODO: implement
    id = Column(String, primary_key=True)
    name = Column(String)
    barcode = Column(String)


class Engagement(Base):
    __tablename__ = "engagements"

    # TODO: implement
    hcp_id = Column(String, ForeignKey("hcps.id"), primary_key=True)
    drug_id = Column(String, ForeignKey("drugs.id"), primary_key=True)
    touch_count = Column(Integer)
    last_seen = Column(DateTime)
