"""FastAPI wrapper around the OpenAlex African medical-schools retriever."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, Query

from openalex_client import MEDICAL_SCHOOL_SEARCH_TERMS, OpenAlexClient

app = FastAPI(
    title="OpenAlex Retriever",
    description="Retrieve and classify medical-school-like institutions in Africa from OpenAlex.",
    version="0.2.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "openalex-retriever"}


@app.get("/medical-schools/africa")
def get_african_medical_schools(
    max_results: int = Query(100, ge=1, le=1000),
    per_page: int = Query(50, ge=1, le=200),
    mailto: Optional[str] = Query(None, description="Email for OpenAlex polite pool."),
    api_key: Optional[str] = Query(None, description="Optional OpenAlex API key."),
    sample: bool = Query(False, description="Return bundled sample data without calling OpenAlex."),
    strict_only: bool = Query(True, description="Return only high/medium-confidence medical school candidates."),
    min_confidence: str = Query("medium", pattern="^(low|medium|high)$"),
    country_code: Optional[List[str]] = Query(None, description="Optional African country code filter, e.g. NG, ZA, KE."),
    category: Optional[List[str]] = Query(None, description="Optional category filter."),
) -> dict:
    client = OpenAlexClient(mailto=mailto, api_key=api_key)
    results = client.list_african_medical_schools(
        max_results=max_results,
        per_page=per_page,
        country_codes=country_code,
        sample=sample,
        strict_only=strict_only,
        categories=category,
        min_confidence=min_confidence,
    )

    category_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    for row in results:
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1
        confidence_counts[row["confidence"]] = confidence_counts.get(row["confidence"], 0) + 1

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(results),
            "max_results": max_results,
            "per_page": per_page,
            "sample_mode": sample,
            "strict_only": strict_only,
            "min_confidence": min_confidence,
            "country_code": country_code,
            "category": category,
            "mailto_used": bool(mailto),
            "api_key_used": bool(api_key),
            "search_terms": MEDICAL_SCHOOL_SEARCH_TERMS,
            "source": "https://api.openalex.org/institutions",
            "category_counts": category_counts,
            "confidence_counts": confidence_counts,
        },
        "results": results,
        "note": (
            "OpenAlex has no exact medical-school entity type. Results are rule-classified from "
            "OpenAlex institutions using African scope, medical/health search terms, institution type, "
            "and name-based confidence rules."
        ),
    }
