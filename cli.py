"""CLI entry point for the OpenAlex retriever."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from openalex_client import MEDICAL_SCHOOL_SEARCH_TERMS, OpenAlexClient


def _default_output_path(output_format: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"african_medical_schools_{ts}.{output_format}"


def _print_progress(msg: str) -> None:
    print(f"  {msg}", file=sys.stderr, flush=True)


def _write_csv(path: str, results: List[Dict[str, Any]]) -> None:
    fieldnames = [
        "display_name",
        "country_code",
        "type",
        "category",
        "confidence",
        "is_medical_school",
        "matched_keyword",
        "reason",
        "openalex_id",
        "homepage_url",
        "works_count",
        "cited_by_count",
        "ror",
        "source_query",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


class _ProgressClient(OpenAlexClient):
    """Thin subclass that prints progress to stderr while fetching."""

    def _get_institutions(self, search_term, filter_value, per_page, cursor):
        _print_progress(f'Fetching: "{search_term}" (cursor={cursor[:8] if cursor != "*" else "*"}...)')
        return super()._get_institutions(search_term, filter_value, per_page, cursor)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve and classify African medical-school-like institutions from OpenAlex.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--max-results", type=int, default=100, help="Maximum matching institutions to return.")
    parser.add_argument("--per-page", type=int, default=50, help="Page size for OpenAlex API.")
    parser.add_argument("--mailto", default=None, help="Email for OpenAlex polite pool, or set OPENALEX_MAILTO.")
    parser.add_argument("--api-key", default=None, help="Optional OpenAlex API key, or set OPENALEX_API_KEY.")
    parser.add_argument("--sample", action="store_true", help="Use bundled offline sample data, no network call.")
    parser.add_argument("--strict-only", action=argparse.BooleanOptionalAction, default=True, help="Keep only medical-school candidates.")
    parser.add_argument("--min-confidence", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--country-code", action="append", help="Filter by country code. Can be repeated, e.g. --country-code NG --country-code ZA.")
    parser.add_argument("--category", action="append", help="Filter by category. Can be repeated.")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output file format.")
    parser.add_argument("--output", "-o", default=None, metavar="FILE", help="Output file path.")
    parser.add_argument("--no-save", action="store_true", help="Print JSON to stdout only; do not write a file.")
    args = parser.parse_args()

    output_path = args.output or _default_output_path(args.format)

    print("OpenAlex African Medical Schools Retriever", file=sys.stderr)
    print(f"  max_results    : {args.max_results}", file=sys.stderr)
    print(f"  per_page       : {args.per_page}", file=sys.stderr)
    print(f"  sample mode    : {args.sample}", file=sys.stderr)
    print(f"  strict_only    : {args.strict_only}", file=sys.stderr)
    print(f"  min_confidence : {args.min_confidence}", file=sys.stderr)
    print(f"  country_code   : {args.country_code}", file=sys.stderr)
    print(f"  format         : {args.format}", file=sys.stderr)
    if not args.no_save:
        print(f"  output file    : {output_path}", file=sys.stderr)
    print("", file=sys.stderr)

    client = _ProgressClient(mailto=args.mailto, api_key=args.api_key)

    started_at = time.time()
    results = client.list_african_medical_schools(
        max_results=args.max_results,
        per_page=args.per_page,
        country_codes=args.country_code,
        sample=args.sample,
        strict_only=args.strict_only,
        categories=args.category,
        min_confidence=args.min_confidence,
    )
    elapsed = round(time.time() - started_at, 2)

    category_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    for row in results:
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
        confidence_counts[row["confidence"]] = confidence_counts.get(row["confidence"], 0) + 1

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "count": len(results),
            "max_results": args.max_results,
            "per_page": args.per_page,
            "sample_mode": args.sample,
            "strict_only": args.strict_only,
            "min_confidence": args.min_confidence,
            "country_code": args.country_code,
            "category": args.category,
            "mailto_used": bool(args.mailto or os.getenv("OPENALEX_MAILTO")),
            "api_key_used": bool(args.api_key or os.getenv("OPENALEX_API_KEY")),
            "search_terms": MEDICAL_SCHOOL_SEARCH_TERMS,
            "source": "https://api.openalex.org/institutions",
            "category_counts": category_counts,
            "confidence_counts": confidence_counts,
        },
        "results": results,
    }

    if args.no_save:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if args.format == "csv":
        _write_csv(output_path, results)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")

    print(f"\nDone. {len(results)} institutions saved to: {output_path}", file=sys.stderr)
    print(f"Elapsed: {elapsed}s", file=sys.stderr)
    print(json.dumps({"count": len(results), "output_file": output_path, "elapsed_seconds": elapsed}, indent=2))


if __name__ == "__main__":
    main()
