"""Normalize extracted OPIS observations without network or workbook writes."""
from datetime import date
from decimal import Decimal
from math import isfinite


def normalize_opis(record):
    """Accept explicit source units. Empty reports are skipped, partial ones rejected."""
    if not isinstance(record, dict):
        raise ValueError("Record must be an object")
    fields = ("conway", "tet", "wti")
    if all(record.get(k) is None for k in fields):
        return None
    if not isinstance(record.get("date"), str):
        raise ValueError("Report date must be ISO YYYY-MM-DD")
    parsed = date.fromisoformat(record["date"])
    if parsed.isoformat() != record["date"]:
        raise ValueError("Report date must be ISO YYYY-MM-DD")
    for k in fields:
        v = record.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or v < 0:
            raise ValueError(f"Missing or invalid {k}")
    unit = record.get("propane_unit")
    if unit not in ("cents/gal", "USD/gal") or record.get("wti_unit") != "USD/bbl":
        raise ValueError("Explicit recognized price units required")
    factor = Decimal("0.01") if unit == "cents/gal" else Decimal(1)
    return {"date": record["date"], "conway": float(Decimal(str(record["conway"])) * factor),
            "tet": float(Decimal(str(record["tet"])) * factor), "wti": record["wti"],
            "propane_unit": "USD/gal", "wti_unit": "USD/bbl"}


def classify_upsert(existing, candidate):
    """Return a write plan, rejecting duplicate history rather than concealing it."""
    if candidate is None:
        return "skip_empty"
    matches = [r for r in existing if r["date"] == candidate["date"]]
    if len(matches) > 1:
        raise ValueError("Duplicate report date in existing history; reconcile before writing")
    if not matches:
        return "insert"
    keys = ("date", "conway", "tet", "wti", "propane_unit", "wti_unit")
    return "duplicate" if all(matches[0].get(k) == candidate.get(k) for k in keys) else "revision"
