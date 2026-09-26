"""
Pull FDA drug labels from openFDA and write RAG-ready dossiers.

Layout (matches README): backend/data/drug_docs/<DRUG_NAME>/<DRUG_ID>.txt

Usage (from backend/):
  python scripts/curate_openfda.py
  python scripts/curate_openfda.py --brands Ozempic Keytruda Eliquis
  python scripts/curate_openfda.py --limit 80
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OPENFDA_LABEL = "https://api.fda.gov/drug/label.json"

# High-visibility brands across specialties so the demo + RAG have real coverage.
DEFAULT_BRANDS = [
    "Ozempic",
    "Wegovy",
    "Mounjaro",
    "Trulicity",
    "Jardiance",
    "Farxiga",
    "Eliquis",
    "Xarelto",
    "Entresto",
    "Lipitor",
    "Crestor",
    "Norvasc",
    "Prinivil",
    "Keytruda",
    "Opdivo",
    "Humira",
    "Skyrizi",
    "Stelara",
    "Dupixent",
    "Cosentyx",
    "Rinvoq",
    "Biktarvy",
    "Paxlovid",
    "Synthroid",
    "Adderall",
    "Gabapentin",
    "Prilosec",
    "Amoxil",
    "Glucophage",
    "Januvia",
    "Lantus",
    "Humalog",
    "Spiriva",
    "Advair",
    "Flonase",
    "Singulair",
    "Prozac",
    "Zoloft",
    "Xanax",
    "Ambien",
    "Vicodin",
    "OxyContin",
    "Tylenol",
    "Advil",
    "Nexium",
    "Plavix",
    "Coumadin",
    "Lasix",
    "Prednisone",
    "Augmentin",
    "Cipro",
    "Zithromax",
    "Tamiflu",
    "Valtrex",
    "Chantix",
    "Viagra",
    "Cialis",
    "Premarin",
    "Prolia",
    "Xgeva",
    "Ibrance",
    "Tagrisso",
    "Imbruvica",
    "Darzalex",
    "Revlimid",
    "Enbrel",
    "Remicade",
    "Ocrevus",
    "Tysabri",
    "Tecfidera",
    "Gilenya",
    "Aimovig",
    "Nurtec",
    "Ubrelvy",
    "Trikafta",
    "Spinraza",
    "Zolgensma",
    "Prevnar",
    "Shingrix",
    "Gardasil",
]

LABEL_FIELDS = [
    ("boxed_warning", "Boxed warning"),
    ("indications_and_usage", "Indications and usage"),
    ("dosage_and_administration", "Dosage and administration"),
    ("dosage_forms_and_strengths", "Dosage forms and strengths"),
    ("contraindications", "Contraindications"),
    ("warnings_and_cautions", "Warnings and cautions"),
    ("warnings", "Warnings"),
    ("precautions", "Precautions"),
    ("adverse_reactions", "Adverse reactions"),
    ("drug_interactions", "Drug interactions"),
    ("use_in_specific_populations", "Use in specific populations"),
    ("overdosage", "Overdosage"),
    ("description", "Description"),
    ("clinical_pharmacology", "Clinical pharmacology"),
    ("mechanism_of_action", "Mechanism of action"),
    ("clinical_studies", "Clinical studies"),
    ("how_supplied", "How supplied"),
    ("storage_and_handling", "Storage and handling"),
    ("patient_counseling_information", "Patient counseling"),
    ("information_for_patients", "Information for patients"),
]

MAX_SECTION_CHARS = 12_000


def repo_docs_root() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "drug_docs"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def safe_dirname(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", value).strip(" .")
    return cleaned or "UNKNOWN"


def first_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def section_text(value) -> str:
    parts = first_list(value)
    text = "\n".join(parts).strip()
    if len(text) > MAX_SECTION_CHARS:
        text = text[:MAX_SECTION_CHARS].rstrip() + "\n[truncated]"
    return text


def openfda_get(params: dict, retries: int = 3) -> dict | None:
    query = urllib.parse.urlencode(params, safe=":+\"[]")
    url = f"{OPENFDA_LABEL}?{query}"
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lens-hcp-copilot/0.1"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            last_error = exc
            time.sleep(0.5 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.5 * (attempt + 1))
    if last_error:
        print(f"  openFDA error: {last_error}", file=sys.stderr)
    return None


def _best_result(results: list[dict], brand: str) -> dict | None:
    if not results:
        return None
    want = brand.strip().lower()
    ranked: list[tuple[int, dict]] = []
    for result in results:
        meta = result.get("openfda") or {}
        names = [item.lower() for item in first_list(meta.get("brand_name"))]
        generics = [item.lower() for item in first_list(meta.get("generic_name"))]
        score = 0
        if want in names:
            score += 10
        if any(want == item for item in names):
            score += 5
        if want in generics:
            score += 2
        if "HUMAN PRESCRIPTION DRUG" in first_list(meta.get("product_type")):
            score += 1
        ranked.append((score, result))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def fetch_label(brand: str) -> dict | None:
    for field in ("openfda.brand_name.exact", "openfda.brand_name", "openfda.generic_name"):
        payload = openfda_get(
            {
                "search": f'{field}:"{brand}"',
                "limit": "5",
            }
        )
        if payload and payload.get("results"):
            picked = _best_result(payload["results"], brand)
            if picked:
                return picked
    return None


def fetch_bulk(limit: int) -> list[dict]:
    results: list[dict] = []
    skip = 0
    page = 100
    while len(results) < limit:
        batch = min(page, limit - len(results))
        payload = openfda_get(
            {
                "search": 'openfda.product_type:"HUMAN PRESCRIPTION DRUG"',
                "limit": str(batch),
                "skip": str(skip),
            }
        )
        if not payload or not payload.get("results"):
            break
        results.extend(payload["results"])
        skip += batch
        time.sleep(0.25)
    return results[:limit]


def dossier_from_label(label: dict, fallback_name: str) -> tuple[str, str, str]:
    meta = label.get("openfda") or {}
    brands = first_list(meta.get("brand_name"))
    generics = first_list(meta.get("generic_name"))
    ndcs = first_list(meta.get("product_ndc"))
    app_nos = first_list(meta.get("application_number"))
    manufacturers = first_list(meta.get("manufacturer_name"))
    pharm_class = first_list(meta.get("pharm_class_epc"))
    routes = first_list(meta.get("route"))
    rxcui = first_list(meta.get("rxcui"))

    official = brands[0] if brands else fallback_name
    brand = fallback_name or official
    drug_id = slugify(brand)
    if not drug_id:
        drug_id = slugify(official or (app_nos[0] if app_nos else "unknown"))

    header_lines = [
        f"Drug: {brand}",
        f"OpenFDA brand names: {', '.join(brands) or 'unknown'}",
        f"Drug ID: {drug_id}",
        f"Generic name: {', '.join(generics) or 'unknown'}",
        f"Manufacturer: {', '.join(manufacturers) or 'unknown'}",
        f"NDC: {', '.join(ndcs) or 'unknown'}",
        f"Application number: {', '.join(app_nos) or 'unknown'}",
        f"RxCUI: {', '.join(rxcui) or 'unknown'}",
        f"Route: {', '.join(routes) or 'unknown'}",
        f"Pharmacologic class: {', '.join(pharm_class) or 'unknown'}",
        "Source: openFDA drug label",
        "",
    ]

    body: list[str] = []
    for field, title in LABEL_FIELDS:
        text = section_text(label.get(field))
        if text:
            body.append(f"## {title}\n{text}\n")

    if not body:
        body.append("## Label\nNo structured sections were present on this openFDA record.\n")

    return brand, drug_id, "\n".join(header_lines + body).strip() + "\n"


def write_dossier(docs_root: Path, brand: str, drug_id: str, content: str) -> Path:
    folder = docs_root / safe_dirname(brand)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{drug_id}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def write_manifest(docs_root: Path) -> Path:
    entries = []
    for txt in sorted(docs_root.glob("*/*.txt")):
        drug_id = txt.stem
        name = txt.parent.name
        ndcs: list[str] = []
        generic = ""
        for line in txt.read_text(encoding="utf-8").splitlines()[:12]:
            if line.startswith("NDC:"):
                ndcs = [part.strip() for part in line[4:].split(",") if part.strip() and part.strip() != "unknown"]
            if line.startswith("Generic name:"):
                generic = line.split(":", 1)[1].strip()
        entries.append(
            {
                "drug_id": drug_id,
                "name": name,
                "generic": generic,
                "ndcs": ndcs,
                "path": str(txt.relative_to(docs_root)).replace("\\", "/"),
            }
        )
    manifest_path = docs_root / "manifest.json"
    manifest_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Curate openFDA drug dossiers for RAG.")
    parser.add_argument("--out", type=Path, default=repo_docs_root())
    parser.add_argument("--brands", nargs="*", help="Brand names to fetch (default: built-in list).")
    parser.add_argument("--limit", type=int, default=None, help="Cap how many brands/labels to write.")
    parser.add_argument(
        "--bulk",
        type=int,
        default=0,
        help="Also pull this many extra HUMAN PRESCRIPTION DRUG labels from openFDA.",
    )
    args = parser.parse_args()

    docs_root: Path = args.out
    docs_root.mkdir(parents=True, exist_ok=True)

    brands = args.brands or DEFAULT_BRANDS
    if args.limit is not None:
        brands = brands[: args.limit]

    written = 0
    skipped = 0
    seen_ids: set[str] = set()

    for brand in brands:
        print(f"Fetching {brand}...")
        label = fetch_label(brand)
        time.sleep(0.2)
        if not label:
            print(f"  skip (not found): {brand}")
            skipped += 1
            continue
        name, drug_id, content = dossier_from_label(label, brand)
        if drug_id in seen_ids:
            print(f"  skip (duplicate id {drug_id}): {brand}")
            skipped += 1
            continue
        path = write_dossier(docs_root, name, drug_id, content)
        seen_ids.add(drug_id)
        written += 1
        print(f"  wrote {path.relative_to(docs_root)}")

    if args.bulk:
        print(f"Fetching {args.bulk} bulk prescription labels...")
        for label in fetch_bulk(args.bulk):
            meta = label.get("openfda") or {}
            fallback = (first_list(meta.get("brand_name")) or ["unknown"])[0]
            name, drug_id, content = dossier_from_label(label, fallback)
            if drug_id in seen_ids:
                skipped += 1
                continue
            path = write_dossier(docs_root, name, drug_id, content)
            seen_ids.add(drug_id)
            written += 1
            print(f"  wrote {path.relative_to(docs_root)}")

    manifest = write_manifest(docs_root)
    print(f"Done. wrote={written} skipped={skipped} manifest={manifest}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
