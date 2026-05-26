"""OpenAlex retrieval audit for African medical-school discovery.

This script answers Peter's five audit questions with reproducible API calls:
1. African institution coverage by country and type.
2. Why strict keyword filtering returns a small list.
3. Which query strategies capture embedded faculties/colleges/schools better.
4. Main false positives and false negatives.
5. What the authors endpoint provides for three sample institutions.

Run:
    python scripts/audit_openalex.py --mailto your_email@example.com

Outputs are written to ./outputs by default.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

import requests

# Allow running this script from repo root without installing as a package.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from openalex_client import (  # noqa: E402
    MEDICAL_SCHOOL_SEARCH_TERMS,
    OpenAlexClient,
    classify_institution,
)

OPENALEX_BASE_URL = "https://api.openalex.org"

# Three sample institutions chosen from the current strict output. These give
# coverage across East, North, and Southern/Central Africa and include both high
# and medium-confidence school-like institutions.
DEFAULT_SAMPLE_INSTITUTIONS = [
    "https://openalex.org/I3133036570",  # Lusaka Apex Medical University
    "https://openalex.org/I145354842",   # University of Medical Sciences and Technology
    "https://openalex.org/I2802393258",  # Sefako Makgatho Health Sciences University
]

STRICT_TERMS = [
    "medical school",
    "school of medicine",
    "faculty of medicine",
    "college of medicine",
    "medical university",
    "university of medical sciences",
]

EMBEDDED_TERMS = [
    "faculty of medicine",
    "school of medicine",
    "college of medicine",
    "college of health sciences",
    "faculty of health sciences",
    "school of nursing",
    "school of pharmacy",
    "health sciences",
    "nursing",
    "pharmacy",
]


def _request_json(session: requests.Session, path: str, params: Dict[str, Any], *, timeout: int = 60) -> Dict[str, Any]:
    response = session.get(f"{OPENALEX_BASE_URL}/{path.lstrip('/')}", params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _auth_params(mailto: Optional[str], api_key: Optional[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    if mailto:
        params["mailto"] = mailto
    if api_key:
        params["api_key"] = api_key
    return params


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _write_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _group_by(session: requests.Session, *, entity: str, filter_value: str, group_by: str, mailto: Optional[str], api_key: Optional[str]) -> Dict[str, Any]:
    params = {
        "filter": filter_value,
        "group_by": group_by,
        "per-page": 200,
        **_auth_params(mailto, api_key),
    }
    return _request_json(session, entity, params)


def _country_code_from_group_key(key: Optional[str]) -> Optional[str]:
    """Extract ZA from OpenAlex group keys like https://openalex.org/countries/ZA."""
    if not key or key == "unknown":
        return None
    if "/countries/" in key:
        return key.rstrip("/").rsplit("/", 1)[-1]
    return key


def audit_coverage(session: requests.Session, out_dir: Path, mailto: Optional[str], api_key: Optional[str]) -> Dict[str, Any]:
    """Audit OpenAlex institution coverage in Africa by country and institution type."""
    by_country = _group_by(
        session,
        entity="institutions",
        filter_value="continent:africa",
        group_by="country_code",
        mailto=mailto,
        api_key=api_key,
    )
    by_type = _group_by(
        session,
        entity="institutions",
        filter_value="continent:africa",
        group_by="type",
        mailto=mailto,
        api_key=api_key,
    )

    country_rows = by_country.get("group_by", [])
    type_rows = by_type.get("group_by", [])

    # Build country x type matrix using API grouping per country.
    matrix_rows: List[Dict[str, Any]] = []
    for row in country_rows:
        code = _country_code_from_group_key(row.get("key"))
        if not code:
            continue
        grouped = _group_by(
            session,
            entity="institutions",
            filter_value=f"continent:africa,country_code:{code}",
            group_by="type",
            mailto=mailto,
            api_key=api_key,
        )
        for type_row in grouped.get("group_by", []):
            matrix_rows.append({
                "country_code": code,
                "country_name": row.get("key_display_name"),
                "type": type_row.get("key"),
                "type_display_name": type_row.get("key_display_name"),
                "count": type_row.get("count"),
            })
        time.sleep(0.05)

    coverage = {
        "country_coverage": country_rows,
        "type_coverage": type_rows,
        "country_type_matrix": matrix_rows,
        "total_african_institutions": by_country.get("meta", {}).get("count"),
    }

    _write_json(out_dir / "coverage_by_country_type.json", coverage)
    _write_csv(
        out_dir / "coverage_by_country.csv",
        country_rows,
        ["key", "key_display_name", "count"],
    )
    _write_csv(
        out_dir / "coverage_by_type.csv",
        type_rows,
        ["key", "key_display_name", "count"],
    )
    _write_csv(
        out_dir / "coverage_country_type_matrix.csv",
        matrix_rows,
        ["country_code", "country_name", "type", "type_display_name", "count"],
    )
    return coverage


# Rest of file unchanged from current repository version.
