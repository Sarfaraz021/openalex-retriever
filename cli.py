"""CLI entry point for the OpenAlex scraper."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

from openalex_client import OpenAlexClient, MEDICAL_SCHOOL_SEARCH_TERMS


def _default_output_path() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"african_medical_schools_{ts}.json"


def _print_progress(msg: str) -> None:
    print(f"  {msg}", file=sys.stderr, flush=True)


class _ProgressClient(OpenAlexClient):
    """Thin subclass that prints progress to stderr while fetching."""

    def _get_institutions(self, search_term, filter_value, per_page, cursor):
        _print_progress(f'Fetching: "{search_term}" (cursor={cursor[:8] if cursor != "*" else "*"}...)')
        return super()._get_institutions(search_term, filter_value, per_page, cursor)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve African medical schools from OpenAlex and save to JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--max-results", type=int, default=100, help="Maximum institutions to fetch.")
    parser.add_argument("--per-page", type=int, default=50, help="Page size for OpenAlex API.")
    parser.add_argument("--mailto", default=None, help="Email for OpenAlex polite pool (or set OPENALEX_MAILTO env var).")
    parser.add_argument("--sample", action="store_true", help="Use bundled offline sample data (no network call).")
    parser.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Path for the output JSON file. Defaults to african_medical_schools_<timestamp>.json",
    )
    parser.add_argument("--no-save", action="store_true", help="Print JSON to stdout only; do not write a file.")
    args = parser.parse_args()

    output_path = args.output or _default_output_path()

    print("OpenAlex African Medical Schools Scraper", file=sys.stderr)
    print(f"  max_results : {args.max_results}", file=sys.stderr)
    print(f"  per_page    : {args.per_page}", file=sys.stderr)
    print(f"  sample mode : {args.sample}", file=sys.stderr)
    if not args.no_save:
        print(f"  output file : {output_path}", file=sys.stderr)
    print("", file=sys.stderr)

    client = _ProgressClient(mailto=args.mailto)

    started_at = time.time()
    results = client.list_african_medical_schools(
        max_results=args.max_results,
        per_page=args.per_page,
        sample=args.sample,
    )
    elapsed = round(time.time() - started_at, 2)

    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "count": len(results),
            "max_results": args.max_results,
            "per_page": args.per_page,
            "sample_mode": args.sample,
            "mailto_used": bool(args.mailto or os.getenv("OPENALEX_MAILTO")),
            "search_terms": MEDICAL_SCHOOL_SEARCH_TERMS,
            "source": "https://api.openalex.org/institutions",
        },
        "results": results,
    }

    json_output = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.no_save:
        print(json_output)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_output)
            f.write("\n")
        print(f"\nDone. {len(results)} institutions saved to: {output_path}", file=sys.stderr)
        print(f"Elapsed: {elapsed}s", file=sys.stderr)

        # Also print a compact summary to stdout
        print(json.dumps({"count": len(results), "output_file": output_path, "elapsed_seconds": elapsed}, indent=2))


if __name__ == "__main__":
    main()
