"""OpenAlex client for retrieving and classifying African medical-school-like institutions.

This module uses the official OpenAlex Institutions API. It does not scrape HTML.
Because OpenAlex does not expose a dedicated `medical_school` entity type, the
client retrieves broad medical/health institution candidates and then classifies
results into medical schools, candidates, related institutions, or excluded items.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests

OPENALEX_BASE_URL = "https://api.openalex.org"

AFRICA_COUNTRY_CODES = [
    "DZ", "AO", "BJ", "BW", "BF", "BI", "CV", "CM", "CF", "TD", "KM", "CD", "CG", "CI", "DJ", "EG",
    "GQ", "ER", "SZ", "ET", "GA", "GM", "GH", "GN", "GW", "KE", "LS", "LR", "LY", "MG", "MW", "ML",
    "MR", "MU", "MA", "MZ", "NA", "NE", "NG", "RW", "ST", "SN", "SC", "SL", "SO", "ZA", "SS", "SD",
    "TZ", "TG", "TN", "UG", "ZM", "ZW",
]

# Use both strict and broad terms. Strict terms produce higher precision, broad terms
# help discover schools that OpenAlex only matches through generic medical wording.
MEDICAL_SCHOOL_SEARCH_TERMS = [
    "medical school",
    "school of medicine",
    "faculty of medicine",
    "college of medicine",
    "medical university",
    "university of medical sciences",
    "health sciences",
    "medical",
    "medicine",
    "pharmacy",
    "nursing",
]

HIGH_CONFIDENCE_TERMS = [
    "medical school",
    "school of medicine",
    "faculty of medicine",
    "college of medicine",
    "medical university",
    "university of medical sciences",
    "medical college",
    "hospital medical college",
]

MEDIUM_CONFIDENCE_TERMS = [
    "health sciences",
    "health science",
    "medical training college",
    "postgraduate medical college",
    "university of health sciences",
    "college of health sciences",
    "faculty of health sciences",
    "school of health sciences",
    "medicine and health",
    "pharmacy school",
    "school of pharmacy",
    "school of nursing",
    "nursing college",
]

RELATED_MEDICAL_TERMS = [
    "medical research",
    "research institute",
    "medical centre",
    "medical center",
    "hospital",
    "council",
    "association",
    "bureau",
    "stores",
    "publishing",
    "trading",
    "oncology centre",
    "oncology center",
    "laboratory science council",
    "medical action",
]

# Terms that strongly indicate the result is not a teaching institution. These are
# only applied after the high/medium school rules so names such as
# "Adama Hospital Medical College" are still kept as medical schools.
NON_SCHOOL_TYPES = {"company", "nonprofit", "government", "facility", "other"}

SAMPLE_RESULTS = [
    {
        "id": "https://openalex.org/I3133036570",
        "display_name": "Lusaka Apex Medical University",
        "country_code": "ZM",
        "type": "education",
        "homepage_url": "http://lamu.edu.zm/",
        "works_count": 784,
        "cited_by_count": 11897,
        "ror": "https://ror.org/016ayye29",
    },
    {
        "id": "https://openalex.org/I4405261048",
        "display_name": "Adama Hospital Medical College",
        "country_code": "ET",
        "type": "education",
        "homepage_url": "https://www.adamahmc.edu.et",
        "works_count": 0,
        "cited_by_count": 0,
        "ror": "https://ror.org/04p8ta418",
    },
    {
        "id": "https://openalex.org/I2841861",
        "display_name": "Kenya Medical Research Institute",
        "country_code": "KE",
        "type": "facility",
        "homepage_url": "http://kemri-wellcome.org/",
        "works_count": 22059,
        "cited_by_count": 1793813,
        "ror": "https://ror.org/04r1cxt79",
    },
]


def _first_matching_term(name: str, terms: Sequence[str]) -> Optional[str]:
    lower = name.lower()
    return next((term for term in terms if term in lower), None)


def classify_institution(name: str, institution_type: Optional[str]) -> Dict[str, Any]:
    """Classify an OpenAlex institution as a medical school or related entity.

    Returns a deterministic rule-based classification with a reason so users can
    audit why a result was kept or downgraded.
    """
    name = name or ""
    institution_type = institution_type or "unknown"
    lower_type = institution_type.lower()

    high_match = _first_matching_term(name, HIGH_CONFIDENCE_TERMS)
    if high_match:
        # Nonprofits/companies that happen to contain a medical school term in
        # their name (e.g. "Baylor College of Medicine Children's Foundation")
        # are not teaching institutions — downgrade them.
        if lower_type in {"nonprofit", "company"}:
            return {
                "category": "related_medical_institution",
                "confidence": "medium",
                "is_medical_school": False,
                "matched_keyword": high_match,
                "reason": (
                    f"Name matches '{high_match}' but institution type is {institution_type}"
                    " — likely a foundation or NGO, not a teaching institution."
                ),
            }
        return {
            "category": "medical_school",
            "confidence": "high",
            "is_medical_school": True,
            "matched_keyword": high_match,
            "reason": f"Name contains high-confidence medical school term: {high_match}.",
        }

    medium_match = _first_matching_term(name, MEDIUM_CONFIDENCE_TERMS)
    if medium_match and lower_type in {"education", "healthcare"}:
        return {
            "category": "medical_school_candidate",
            "confidence": "medium",
            "is_medical_school": True,
            "matched_keyword": medium_match,
            "reason": f"Institution type is {institution_type} and name contains candidate term: {medium_match}.",
        }

    related_match = _first_matching_term(name, RELATED_MEDICAL_TERMS)
    if related_match or lower_type in NON_SCHOOL_TYPES:
        return {
            "category": "related_medical_institution",
            "confidence": "low",
            "is_medical_school": False,
            "matched_keyword": related_match,
            "reason": "Medical/health-related result, but not clearly a school, college, university, or faculty.",
        }

    return {
        "category": "unknown_or_related",
        "confidence": "low",
        "is_medical_school": False,
        "matched_keyword": None,
        "reason": "No strong medical-school indicator found in the institution name.",
    }


def _normalise_institution(item: Dict[str, Any], source_query: str) -> Dict[str, Any]:
    classification = classify_institution(item.get("display_name") or "", item.get("type"))
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
        **classification,
    }


def _passes_filters(
    row: Dict[str, Any],
    *,
    strict_only: bool,
    categories: Optional[Sequence[str]],
    min_confidence: str,
) -> bool:
    confidence_rank = {"low": 1, "medium": 2, "high": 3}

    if strict_only and not row.get("is_medical_school"):
        return False

    if categories and row.get("category") not in categories:
        return False

    row_rank = confidence_rank.get(str(row.get("confidence", "low")), 1)
    required_rank = confidence_rank.get(min_confidence, 1)
    return row_rank >= required_rank


class OpenAlexClient:
    def __init__(
        self,
        mailto: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 60,
        sleep_seconds: float = 0.1,
    ) -> None:
        self.mailto = mailto or os.getenv("OPENALEX_MAILTO")
        self.api_key = api_key or os.getenv("OPENALEX_API_KEY")
        self.timeout = timeout
        self.sleep_seconds = sleep_seconds
        self.session = requests.Session()

    def list_african_medical_schools(
        self,
        *,
        per_page: int = 50,
        max_results: int = 200,
        country_codes: Optional[Iterable[str]] = None,
        sample: bool = False,
        strict_only: bool = True,
        categories: Optional[Sequence[str]] = None,
        min_confidence: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Return classified African medical-school candidates.

        `strict_only=True` returns only high/medium-confidence school-like results.
        Set it to False to also inspect related hospitals, associations, councils,
        research institutes, and other medical institutions.
        """
        seen: set[str] = set()
        results: List[Dict[str, Any]] = []

        if sample:
            for item in SAMPLE_RESULTS:
                row = _normalise_institution(item, "offline_sample")
                if _passes_filters(row, strict_only=strict_only, categories=categories, min_confidence=min_confidence):
                    results.append(row)
            return results[:max_results]

        continent_filter = self._build_geo_filter(country_codes)

        for term in MEDICAL_SCHOOL_SEARCH_TERMS:
            filter_value = f"{continent_filter},display_name.search:{term}"
            cursor = "*"
            while cursor and len(results) < max_results:
                payload = self._get_institutions(term, filter_value, per_page, cursor)
                for item in payload.get("results", []):
                    institution_id = item.get("id")
                    if not institution_id or institution_id in seen:
                        continue
                    seen.add(institution_id)
                    row = _normalise_institution(item, term)
                    if not _passes_filters(row, strict_only=strict_only, categories=categories, min_confidence=min_confidence):
                        continue
                    results.append(row)
                    if len(results) >= max_results:
                        break

                next_cursor = payload.get("meta", {}).get("next_cursor")
                cursor = next_cursor if next_cursor and next_cursor != cursor else None
                time.sleep(self.sleep_seconds)

        # Second pass: embedded faculties of medicine inside large universities.
        # Many top African medical schools are sub-units of their parent university
        # (e.g. UCT Faculty of Health Sciences) and don't surface in the name search
        # above. We query by lineage of known high-output African universities and
        # pull only child institutions whose names match medical-school terms.
        if len(results) < max_results:
            results = self._enrich_with_embedded_faculties(
                results, seen, continent_filter, strict_only, categories, min_confidence, max_results
            )

        return sorted(results, key=lambda r: (r.get("confidence") != "high", -(r.get("cited_by_count") or 0)))

    def _build_geo_filter(self, country_codes: Optional[Iterable[str]]) -> str:
        if country_codes:
            codes = [c.upper() for c in country_codes]
            return f"country_code:{'|'.join(codes)}"
        return "continent:africa"

    def _enrich_with_embedded_faculties(
        self,
        results: List[Dict[str, Any]],
        seen: set,
        continent_filter: str,
        strict_only: bool,
        categories: Optional[Sequence[str]],
        min_confidence: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Find medical faculties that are sub-units of large African universities.

        OpenAlex models faculties as separate institutions linked to their parent via
        the `lineage` field. We query child institutions whose names contain faculty-
        level medical terms, filtering to Africa and education/healthcare types.
        """
        faculty_terms = [
            "faculty of medicine",
            "school of medicine",
            "faculty of health sciences",
            "college of medicine",
            "school of public health",
        ]
        for term in faculty_terms:
            if len(results) >= max_results:
                break
            filter_value = f"{continent_filter},type:education,display_name.search:{term}"
            payload = self._get_institutions(term, filter_value, 50, "*")
            for item in payload.get("results", []):
                institution_id = item.get("id")
                if not institution_id or institution_id in seen:
                    continue
                seen.add(institution_id)
                row = _normalise_institution(item, f"faculty_search:{term}")
                if not _passes_filters(row, strict_only=strict_only, categories=categories, min_confidence=min_confidence):
                    continue
                results.append(row)
                if len(results) >= max_results:
                    break
            time.sleep(self.sleep_seconds)
        return results

    def _get_institutions(self, search_term: str, filter_value: str, per_page: int, cursor: str) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "filter": filter_value,
            "per-page": per_page,
            "cursor": cursor,
        }
        if self.mailto:
            params["mailto"] = self.mailto
        if self.api_key:
            params["api_key"] = self.api_key

        last_exc: Exception = RuntimeError("no attempts made")
        for attempt in range(1, 4):
            try:
                response = self.session.get(
                    f"{OPENALEX_BASE_URL}/institutions",
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_exc = exc
                wait = 2 ** attempt
                time.sleep(wait)
        raise last_exc
