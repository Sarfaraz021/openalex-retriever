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
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

# Allow running this script from repo root without installing as a package.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from openalex_client import OpenAlexClient  # noqa: E402

OPENALEX_BASE_URL = "https://api.openalex.org"

DEFAULT_SAMPLE_INSTITUTIONS = [
    "https://openalex.org/I3133036570",  # Lusaka Apex Medical University
    "https://openalex.org/I145354842",   # University of Medical Sciences and Technology
    "https://openalex.org/I2802393258",  # Sefako Makgatho Health Sciences University
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


def _group_by(
    session: requests.Session,
    *,
    entity: str,
    filter_value: str,
    group_by: str,
    mailto: Optional[str],
    api_key: Optional[str],
) -> Dict[str, Any]:
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
    _write_csv(out_dir / "coverage_by_country.csv", country_rows, ["key", "key_display_name", "count"])
    _write_csv(out_dir / "coverage_by_type.csv", type_rows, ["key", "key_display_name", "count"])
    _write_csv(
        out_dir / "coverage_country_type_matrix.csv",
        matrix_rows,
        ["country_code", "country_name", "type", "type_display_name", "count"],
    )
    return coverage


def audit_query_strategies(out_dir: Path, mailto: Optional[str], api_key: Optional[str], max_results: int) -> Dict[str, Any]:
    """Compare strict, balanced, and broad query strategies."""
    client = OpenAlexClient(mailto=mailto, api_key=api_key)

    strict_results = client.list_african_medical_schools(
        max_results=max_results,
        strict_only=True,
        min_confidence="high",
    )
    balanced_results = client.list_african_medical_schools(
        max_results=max_results,
        strict_only=True,
        min_confidence="medium",
    )
    broad_results = client.list_african_medical_schools(
        max_results=max_results,
        strict_only=False,
        min_confidence="low",
    )

    def summarize(name: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "strategy": name,
            "count": len(rows),
            "category_counts": dict(Counter(r.get("category") for r in rows)),
            "confidence_counts": dict(Counter(r.get("confidence") for r in rows)),
            "type_counts": dict(Counter(r.get("type") for r in rows)),
            "country_counts": dict(Counter(r.get("country_code") for r in rows)),
        }

    strategy_payload = {
        "summary": [
            summarize("strict_high_confidence_only", strict_results),
            summarize("balanced_strict_medium_plus", balanced_results),
            summarize("broad_discovery_low_plus", broad_results),
        ],
        "strict_high_confidence_only": strict_results,
        "balanced_strict_medium_plus": balanced_results,
        "broad_discovery_low_plus": broad_results,
        "interpretation": {
            "why_strict_is_small": [
                "OpenAlex has no dedicated medical_school institution type.",
                "Many faculties/schools are embedded inside broader university records rather than standalone institutions.",
                "Strict rules require strong terms like medical university, college of medicine, school of medicine, or faculty of medicine.",
                "Broad terms like medical/health/nursing increase recall but introduce hospitals, NGOs, research institutes, councils, and associations.",
            ],
            "best_strategy": [
                "Use strict_high_confidence_only for a defensible core list.",
                "Use balanced_strict_medium_plus for a practical review list.",
                "Use broad_discovery_low_plus as a candidate discovery layer, not as the final list.",
                "For embedded faculties, combine institution search with works/authors affiliation queries against parent universities.",
            ],
        },
    }

    _write_json(out_dir / "query_strategy_comparison.json", strategy_payload)
    fieldnames = [
        "display_name", "country_code", "type", "category", "confidence", "is_medical_school",
        "matched_keyword", "reason", "openalex_id", "homepage_url", "works_count", "cited_by_count", "ror", "source_query",
    ]
    _write_csv(out_dir / "strict_high_confidence_only.csv", strict_results, fieldnames)
    _write_csv(out_dir / "balanced_strict_medium_plus.csv", balanced_results, fieldnames)
    _write_csv(out_dir / "broad_discovery_low_plus.csv", broad_results, fieldnames)

    return strategy_payload


def audit_false_positives_negatives(strategy_payload: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    broad = strategy_payload["broad_discovery_low_plus"]
    balanced = strategy_payload["balanced_strict_medium_plus"]
    balanced_ids = {r["openalex_id"] for r in balanced}

    false_positive_risks = [
        r for r in broad
        if r.get("category") == "related_medical_institution"
        or r.get("type") in {"nonprofit", "government", "facility", "other", "company"}
    ]
    false_negative_risks = [
        r for r in broad
        if r.get("openalex_id") not in balanced_ids and r.get("type") in {"education", "healthcare"}
    ]

    payload = {
        "false_positive_risks": false_positive_risks[:100],
        "false_negative_risks": false_negative_risks[:100],
        "notes": {
            "false_positives": "Medical words can retrieve hospitals, NGOs, research councils, foundations, publishers, and associations.",
            "false_negatives": "Embedded faculties may be hidden under broader university records or not separately represented as OpenAlex institutions.",
        },
    }
    _write_json(out_dir / "false_positive_negative_audit.json", payload)
    return payload


def audit_embedded_faculty_strategy(session: requests.Session, out_dir: Path, mailto: Optional[str], api_key: Optional[str]) -> Dict[str, Any]:
    """Probe embedded faculty strategy using works grouped by institutions."""
    probes: List[Dict[str, Any]] = []
    for term in EMBEDDED_TERMS:
        params = {
            "filter": "authorships.institutions.continent:africa",
            "search": term,
            "group_by": "authorships.institutions.id",
            "per-page": 25,
            **_auth_params(mailto, api_key),
        }
        payload = _request_json(session, "works", params)
        probes.append({
            "term": term,
            "matching_works_count": payload.get("meta", {}).get("count"),
            "top_institution_groups": payload.get("group_by", []),
        })
        time.sleep(0.05)

    payload = {
        "method": "works search + African authorship institution grouping",
        "query_pattern": "GET /works?filter=authorships.institutions.continent:africa&search=<term>&group_by=authorships.institutions.id",
        "purpose": "Find broader universities that appear in medicine/nursing/health-sciences works when faculties are not standalone institutions.",
        "probes": probes,
    }
    _write_json(out_dir / "embedded_faculty_strategy_audit.json", payload)
    return payload


def audit_authors_endpoint(session: requests.Session, out_dir: Path, institution_ids: List[str], mailto: Optional[str], api_key: Optional[str]) -> Dict[str, Any]:
    """Inspect what authors endpoint provides for sample institutions."""
    samples: List[Dict[str, Any]] = []
    for institution_id in institution_ids:
        institution_openalex_short = institution_id.rsplit("/", 1)[-1]
        institution = _request_json(session, f"institutions/{institution_openalex_short}", _auth_params(mailto, api_key))

        params = {
            "filter": f"last_known_institutions.id:{institution_id}",
            "sort": "works_count:desc",
            "per-page": 5,
            "select": "id,display_name,orcid,works_count,cited_by_count,last_known_institutions,affiliations,topics,works_api_url",
            **_auth_params(mailto, api_key),
        }
        authors_payload = _request_json(session, "authors", params)
        samples.append({
            "institution": {
                "id": institution.get("id"),
                "display_name": institution.get("display_name"),
                "country_code": institution.get("country_code"),
                "type": institution.get("type"),
                "works_count": institution.get("works_count"),
                "cited_by_count": institution.get("cited_by_count"),
                "ror": institution.get("ror"),
            },
            "authors_query": f"/authors?filter=last_known_institutions.id:{institution_id}&sort=works_count:desc&per-page=5",
            "authors_count": authors_payload.get("meta", {}).get("count"),
            "sample_authors": authors_payload.get("results", []),
            "what_it_provides": [
                "disambiguated author profiles",
                "ORCID when available",
                "works_count and cited_by_count",
                "last_known_institutions",
                "affiliations history where available",
                "topics and works_api_url",
            ],
            "what_it_does_not_provide": [
                "a complete official faculty/staff directory",
                "employment verification",
                "guaranteed department/faculty membership",
                "all historical institutional affiliations with perfect completeness",
            ],
        })
        time.sleep(0.05)

    payload = {"samples": samples}
    _write_json(out_dir / "authors_endpoint_sample_audit.json", payload)
    return payload


def write_report(
    out_dir: Path,
    coverage: Dict[str, Any],
    strategies: Dict[str, Any],
    fpfn: Dict[str, Any],
    embedded: Dict[str, Any],
    authors: Dict[str, Any],
) -> Path:
    country_top = coverage["country_coverage"][:10]
    type_rows = coverage["type_coverage"]
    strategy_summary = strategies["summary"]

    report = f"""# OpenAlex Retrieval Audit — African Medical Schools

Generated at: {datetime.now(timezone.utc).isoformat()}

## Executive summary

OpenAlex is useful for discovering African medical-school-like institutions, but it should not be treated as a canonical directory of medical schools. Its Institutions entity mainly represents organizations appearing in scholarly affiliation metadata, including universities, hospitals, government bodies, research institutes, NGOs, companies, and other entities.

The audit supports a cautious conclusion: OpenAlex has strong bibliographic and affiliation metadata, but it does not consistently expose embedded faculties, departments, schools, or colleges inside parent universities as standalone institution records. Therefore, medical-school discovery needs a two-layer approach: institution retrieval for standalone entities, plus works/authors affiliation analysis for embedded units.

## Confidence and limitations

| Area | Assessment |
|---|---|
| OpenAlex architecture and institution model | High confidence: OpenAlex Institutions represent affiliation organizations, not only schools/universities. |
| Dedicated `medical_school` type | Confirmed absent in this audit approach; no dedicated `medical_school` institution type was available. |
| Embedded faculty limitation | High confidence, but not absolute: many faculties/schools appear embedded under broader universities, while some are standalone records. |
| African institution count | Run-specific API count: {coverage.get('total_african_institutions')} returned by `filter=continent:africa` at the time of this run. This should be treated as dynamic, not a permanent total. |
| Specific author counts | Run-specific counts from the Authors endpoint at the time of this run. They may change as OpenAlex updates. |
| ROR coverage | Not universal. Many institutions have ROR IDs, but not all OpenAlex institution records should be assumed to have one. |
| Two-layer strategy | Sound methodology for retrieval auditing, but still requires manual validation for final ground truth. |

## 1. African institution coverage by country and type

At the time of this run, `filter=continent:africa` returned **{coverage.get('total_african_institutions')}** OpenAlex institution records. This is a live API-derived count and should be treated as a snapshot, not a fixed coverage guarantee.

The table below shows only the top 10 countries for readability. The full country-level coverage is available in `outputs/coverage_by_country.csv` and `outputs/coverage_by_country_type.json`. A full country-by-type matrix is also available in `outputs/coverage_country_type_matrix.csv`, so countries outside the top 10 are still included in the audit evidence.

Top countries by institution count:

| Country entity | Country | Count |
|---|---:|---:|
"""
    for row in country_top:
        report += f"| {row.get('key')} | {row.get('key_display_name')} | {row.get('count')} |\n"

    report += "\nInstitution coverage by type:\n\n| Type | Count |\n|---|---:|\n"
    for row in type_rows:
        report += f"| {row.get('key_display_name')} | {row.get('count')} |\n"

    report += "\n## 2. Why strict keyword filtering returns a small list\n\n"
    for item in strategies["interpretation"]["why_strict_is_small"]:
        report += f"- {item}\n"

    report += "\nStrategy comparison from this run:\n\n| Strategy | Count | Category counts | Confidence counts |\n|---|---:|---|---|\n"
    for row in strategy_summary:
        report += f"| {row['strategy']} | {row['count']} | {row['category_counts']} | {row['confidence_counts']} |\n"

    report += "\nInterpretation: strict keyword filtering returns a smaller but more defensible list. Broad retrieval should be used for discovery and audit comparison, not as the final medical-school list.\n"

    report += "\n## 3. Query strategy for embedded faculties/schools\n\nRecommended retrieval strategy:\n\n"
    for index, item in enumerate(strategies["interpretation"]["best_strategy"], start=1):
        report += f"{index}. {item}\n"
    report += "\nEmbedded probe used:\n\n`GET /works?filter=authorships.institutions.continent:africa&search=<term>&group_by=authorships.institutions.id`\n\nThis can surface parent universities appearing in medicine/nursing/health-sciences works when the specific faculty/school is not a standalone OpenAlex institution. It is a discovery signal, not proof that every embedded faculty is fully represented.\n"

    report += "\n## 4. Main false positives and false negatives\n\nFalse positives usually come from medical keywords in non-school entities, such as:\n\n- hospitals and medical centres\n- research institutes and research councils\n- NGOs/foundations\n- medical councils and associations\n- publishers, companies, and government bodies\n\nFalse negatives usually occur when:\n\n- a Faculty/School/College of Medicine is embedded inside a parent university record\n- OpenAlex records the parent university but not the sub-unit\n- the institution name lacks explicit terms like `medicine`, `medical`, or `health sciences`\n- author affiliations mention departments/faculties in raw affiliation text, but the normalized institution remains the parent university\n\n"
    report += f"Broad-mode risk counts from this run:\n\n- False-positive risk examples found: **{len(fpfn['false_positive_risks'])}**\n- False-negative risk examples found: **{len(fpfn['false_negative_risks'])}**\n\nSee `outputs/false_positive_negative_audit.json` for the exact examples.\n"

    report += "\n## 5. What the authors endpoint provides for 3 sample institutions\n\nThe Authors endpoint provides useful bibliographic author metadata linked to institutions, but it should not be treated as a complete staff/faculty directory.\n\n"
    for sample in authors["samples"]:
        inst = sample["institution"]
        report += f"### {inst.get('display_name')} ({inst.get('country_code')})\n\n"
        report += f"- OpenAlex ID: {inst.get('id')}\n"
        report += f"- Institution type: {inst.get('type')}\n"
        report += f"- Authors matched by `last_known_institutions.id` at time of run: {sample.get('authors_count')}\n"
        report += "- Provides: disambiguated author profiles, ORCID when available, works/citations, last known institutions, affiliation history where available, topics, and works API URL.\n"
        report += "- Does not provide: official staff directory, employment verification, guaranteed department/faculty membership, or perfectly complete historical affiliations.\n\n"

    report += "\n## Bottom line\n\nOpenAlex has enough data for a reproducible retrieval audit and candidate discovery workflow, but it does not reliably expose a complete official list of African medical schools or embedded faculties. The best approach is a cautious two-layer audit: (1) strict institution retrieval for high-confidence standalone schools, and (2) works/authors affiliation analysis to discover possible embedded faculties inside broader universities.\n\nThe output should be considered a structured candidate/audit dataset, not final ground truth without manual validation.\n"

    report_path = out_dir / "openalex_retrieval_audit_report.md"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an OpenAlex retrieval audit for African medical schools.")
    parser.add_argument("--mailto", default=os.getenv("OPENALEX_MAILTO"), help="Email for OpenAlex polite pool.")
    parser.add_argument("--api-key", default=os.getenv("OPENALEX_API_KEY"), help="Optional OpenAlex API key.")
    parser.add_argument("--out-dir", default="outputs", help="Directory for audit outputs.")
    parser.add_argument("--max-results", type=int, default=200, help="Max rows per query strategy.")
    parser.add_argument("--sample-institution", action="append", dest="sample_institutions", help="OpenAlex institution ID/URL for authors audit. Repeat up to 3 times.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    session = requests.Session()
    sample_institutions = args.sample_institutions or DEFAULT_SAMPLE_INSTITUTIONS

    print("Running coverage audit...", file=sys.stderr)
    coverage = audit_coverage(session, out_dir, args.mailto, args.api_key)

    print("Running query strategy comparison...", file=sys.stderr)
    strategies = audit_query_strategies(out_dir, args.mailto, args.api_key, args.max_results)

    print("Auditing false positives/false negatives...", file=sys.stderr)
    fpfn = audit_false_positives_negatives(strategies, out_dir)

    print("Auditing embedded faculty strategy...", file=sys.stderr)
    embedded = audit_embedded_faculty_strategy(session, out_dir, args.mailto, args.api_key)

    print("Auditing authors endpoint for sample institutions...", file=sys.stderr)
    authors = audit_authors_endpoint(session, out_dir, sample_institutions[:3], args.mailto, args.api_key)

    report_path = write_report(out_dir, coverage, strategies, fpfn, embedded, authors)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "outputs": [str(p) for p in sorted(out_dir.glob("*"))],
        "report": str(report_path),
    }
    _write_json(out_dir / "audit_manifest.json", manifest)
    print(json.dumps(manifest, indent=2), file=sys.stdout)


if __name__ == "__main__":
    main()
