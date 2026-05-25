"""Small OpenAlex client for retrieving African medical-school-like institutions."""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

OPENALEX_BASE_URL = "https://api.openalex.org"

AFRICA_COUNTRY_CODES = [
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD", "KM", "CD", "CG", "CI", "DJ", "EG",
    "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG", "MW", "ML",
    "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN", "SC", "SL", "SO", "ZA", "SS", "SD",
    "TZ", "TG", "TN", "UG", "ZM", "ZW",
]

MEDICAL_SCHOOL_SEARCH_TERMS = [
    "medical",
    "medicine",
    "health sciences",
    "pharmacy",
    "nursing",
]

SAMPLE_RESULTS = [
    {
        "openalex_id": "https://openalex.org/I4210112080",
        "display_name": "University of Cape Town Faculty of Health Sciences",
        "country_code": "ZA",
        "type": "education",
        "homepage_url": "https://health.uct.ac.za/",
        "works_count": 12345,
        "cited_by_count": 98765,
        "source_query": "offline_sample",
    },
    {
        "openalex_id": "https://openalex.org/I4210091667",
        "display_name": "Makerere University College of Health Sciences",
        "country_code": "UG",
        "type": "education",
        "homepage_url": "https://chs.mak.ac.ug/",
        "works_count": 6789,
        "cited_by_count": 45678,
        "source_query": "offline_sample",
    },
]


def _is_medical_school_like(name: str) -> bool:
    lower = name.lower()
    keywords = [
        "medical school",
        "school of medicine",
        "faculty of medicine",
        "college of medicine",
        "health sciences",
        "medicine and health",
        "university of medicine",
        "health science",
    ]
    return any(keyword in lower for keyword in keywords)


def _normalise_institution(item: Dict[str, Any], source_query: str) -> Dict[str, Any]:
    return {
        "openalex_id": item.get("id"),
        "display_name": item.get("display_name"),
        "country_code": item.get("country_code"),
        "type": item.get("type"),
        "homepage_url": item.get("homepage_url"),
        "works_count": item.get("works_count"),
        "cited_by_count": item.get("cited_by_count"),
        "ror": item.get("ror"),
        "source_query": source_query,
    }


class OpenAlexClient:
    def __init__(self, mailto: Optional[str] = None, timeout: int = 60) -> None:
        self.mailto = mailto or os.getenv("OPENALEX_MAILTO")
        self.timeout = timeout
        self.session = requests.Session()

    def list_african_medical_schools(
        self,
        *,
        per_page: int = 50,
        max_results: int = 200,
        country_codes: Optional[Iterable[str]] = None,
        sample: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return African institutions that look like medical schools/faculties.

        OpenAlex does not expose a dedicated "medical school" entity type. The safest
        first pass is: institutions, type=education, African country codes, plus search
        terms such as "school of medicine" and "faculty of medicine".
        """
        if sample:
            return SAMPLE_RESULTS[:max_results]

        seen: set[str] = set()
        results: List[Dict[str, Any]] = []

        for term in MEDICAL_SCHOOL_SEARCH_TERMS:
            if country_codes:
                codes = list(country_codes)
                filter_value = f"country_code:{'|'.join(codes)},display_name.search:{term}"
            else:
                filter_value = f"continent:africa,display_name.search:{term}"

            cursor = "*"
            while cursor and len(results) < max_results:
                payload = self._get_institutions(term, filter_value, per_page, cursor)
                for item in payload.get("results", []):
                    institution_id = item.get("id")
                    if not institution_id or institution_id in seen:
                        continue
                    seen.add(institution_id)
                    results.append(_normalise_institution(item, term))
                    if len(results) >= max_results:
                        break

                next_cursor = payload.get("meta", {}).get("next_cursor")
                cursor = next_cursor if next_cursor and next_cursor != cursor else None
                time.sleep(0.1)

        return results

    def _get_institutions(self, search_term: str, filter_value: str, per_page: int, cursor: str) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "filter": filter_value,
            "per-page": per_page,
            "cursor": cursor,
        }
        if self.mailto:
            params["mailto"] = self.mailto

        response = self.session.get(f"{OPENALEX_BASE_URL}/institutions", params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
