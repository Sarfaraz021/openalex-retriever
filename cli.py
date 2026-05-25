"""CLI entry point for the OpenAlex scraper."""
from __future__ import annotations

import argparse
import json

from openalex_client import OpenAlexClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve African medical schools from OpenAlex.")
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--per-page", type=int, default=50)
    parser.add_argument("--mailto", default=None, help="Email for OpenAlex polite pool.")
    parser.add_argument("--sample", action="store_true", help="Use bundled offline sample data.")
    args = parser.parse_args()

    client = OpenAlexClient(mailto=args.mailto)
    results = client.list_african_medical_schools(
        max_results=args.max_results,
        per_page=args.per_page,
        sample=args.sample,
    )

    print(json.dumps({"count": len(results), "results": results}, indent=2))


if __name__ == "__main__":
    main()
