"""
Drug doc ingestion.

Reads all files in backend/data/drug_docs/, chunks and embeds them, and
builds the in-memory index used by index.py::retrieve. Runs once at
backend startup.

Owned by: Voice & LLM lane (mechanics) / Content & demo lane (the docs
themselves, see backend/data/drug_docs/).
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.retrieval.embed import embed_text


@dataclass
class Dossier:
    """One parsed drug_docs file. `drug_id` is the filename stem."""

    drug_id: str
    name: str
    barcode: str = ""
    headline: str = ""
    aliases: list[str] = field(default_factory=list)
    # Section title -> {"prose": str, "bullets": list[str]}
    sections: dict[str, dict] = field(default_factory=dict)

    def bullets(self, section: str) -> list[str]:
        return self.sections.get(section, {}).get("bullets", [])

    def prose(self, section: str) -> str:
        return self.sections.get(section, {}).get("prose", "")


@dataclass
class Chunk:
    """One retrievable passage, always tagged with the drug it belongs to."""

    drug_id: str
    section: str
    text: str
    embedding: list[float]


def parse_dossier(path: Path) -> Dossier:
    """Parses one `key: value` header block plus `## Section` bodies."""
    dossier = Dossier(drug_id=path.stem, name=path.stem.title())
    section = None
    prose: list[str] = []
    bullets: list[str] = []

    def flush() -> None:
        if section is None:
            return
        dossier.sections[section] = {
            "prose": " ".join(" ".join(prose).split()),
            "bullets": list(bullets),
        }

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            flush()
            section = line[3:].strip()
            prose, bullets = [], []
        elif section is None:
            if ":" in line:
                key, _, value = line.partition(":")
                key, value = key.strip().lower(), value.strip()
                if key == "name":
                    dossier.name = value
                elif key == "barcode":
                    dossier.barcode = value
                elif key == "headline":
                    dossier.headline = value
                elif key == "aliases":
                    dossier.aliases = [a.strip().lower() for a in value.split(",") if a.strip()]
        elif line.startswith("- "):
            bullets.append(line[2:].strip())
        elif line:
            prose.append(line)
    flush()
    return dossier


def load_dossiers(folder_path: str) -> dict[str, Dossier]:
    """
    Parses every dossier in `folder_path`, keyed by drug_id.

    Shared by db/seed.py (to create drug rows), routes/drug.py (to pick
    tier-appropriate HUD content), and ingest_docs below (to build the index),
    so the docs folder stays the single source of drug content.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return {}
    return {
        path.stem: parse_dossier(path)
        for path in sorted(folder.glob("*.txt"))
    }


def ingest_docs(folder_path: str) -> list[Chunk]:
    """
    Builds and returns the in-memory retrieval index from every file in
    `folder_path`.

    One chunk per section: sections are already the natural semantic unit of
    these dossiers, and they stay small enough to hand to the LLM whole.
    """
    chunks: list[Chunk] = []
    for dossier in load_dossiers(folder_path).values():
        for section, body in dossier.sections.items():
            # Every part is punctuated as a full sentence: the answer builder in
            # llm/client.py ranks context a sentence at a time.
            parts = []
            if body["prose"]:
                parts.append(body["prose"])
            parts.extend(
                bullet if bullet.endswith((".", "!", "?")) else f"{bullet}."
                for bullet in body["bullets"]
            )
            text = " ".join(parts)
            chunks.append(
                Chunk(
                    drug_id=dossier.drug_id,
                    section=section,
                    text=text,
                    # The section title is embedded but kept out of `text`, so
                    # "what's the dosing" matches the Dosing section without the
                    # heading being read aloud as part of the answer.
                    embedding=embed_text(f"{dossier.name} {section}. {text}"),
                )
            )
    return chunks
