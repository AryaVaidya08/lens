from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    """One retrievable passage tagged with its drug and source section."""

    drug_id: str
    section: str
    text: str
    embedding: list[float]