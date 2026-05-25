"""FastAPI wrapper around the OpenAlex African medical-schools retriever."""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query

from openalex_client import OpenAlexClient

app = FastAPI(
    title="OpenAlex Scrapper",
    description="Retrieve medical-school-like institutions in Africa from OpenAlex.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/medical-schools/africa")
def get_african_medical_schools(
    max_results: int = Query(100, ge=1, le=1000),
    per_page: int = Query(50, ge=1, le=200),
    mailto: Optional[str] = Query(None, description="Email for OpenAlex polite pool."),
    sample: bool = Query(False, description="Return bundled sample data without calling OpenAlex."),
) -> dict:
    client = OpenAlexClient(mailto=mailto)
    results = client.list_african_medical_schools(
        max_results=max_results,
        per_page=per_page,
        sample=sample,
    )

    return {
        "count": len(results),
        "results": results,
        "note": (
            "OpenAlex has no exact medical-school type, so results are filtered from institutions "
            "using African country codes, type=education, and medicine/health search terms."
        ),
    }
