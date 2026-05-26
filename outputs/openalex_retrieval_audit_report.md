# OpenAlex Retrieval Audit — African Medical Schools

Generated at: 2026-05-26T20:37:11.761761+00:00

## Executive summary

OpenAlex is useful for discovering African medical-school-like institutions, but it is not a canonical directory of medical schools. Its Institutions entity represents universities and other organizations to which authors claim affiliations. This means coverage is strong for bibliographic affiliation analysis, but incomplete for embedded faculties, departments, and schools inside parent universities.

## 1. Actual African institution coverage by country and type

Total African institutions returned by `filter=continent:africa`: **4022**.

Top countries by institution count:

| Country code | Country | Count |
|---|---:|---:|
| https://openalex.org/countries/ZA | South Africa | 503 |
| https://openalex.org/countries/NG | Nigeria | 456 |
| https://openalex.org/countries/KE | Kenya | 289 |
| https://openalex.org/countries/EG | Egypt | 267 |
| https://openalex.org/countries/UG | Uganda | 231 |
| https://openalex.org/countries/MA | Morocco | 187 |
| https://openalex.org/countries/TZ | Tanzania, United Republic of | 167 |
| https://openalex.org/countries/GH | Ghana | 161 |
| https://openalex.org/countries/DZ | Algeria | 160 |
| https://openalex.org/countries/TN | Tunisia | 139 |

Institution coverage by type:

| Type | Count |
|---|---:|
| education | 1615 |
| nonprofit | 625 |
| government | 533 |
| healthcare | 404 |
| facility | 357 |
| other | 286 |
| company | 145 |
| archive | 53 |
| funder | 4 |

## 2. Why strict keyword filtering returns a small list

- OpenAlex has no dedicated medical_school institution type.
- Many faculties/schools are embedded inside broader university records rather than standalone institutions.
- Strict rules require strong terms like medical university, college of medicine, school of medicine, or faculty of medicine.
- Broad terms like medical/health/nursing increase recall but introduce hospitals, NGOs, research institutes, councils, and associations.

Strategy comparison:

| Strategy | Count | Category counts | Confidence counts |
|---|---:|---|---|
| strict_high_confidence_only | 13 | {'medical_school': 13} | {'high': 13} |
| balanced_strict_medium_plus | 24 | {'medical_school': 13, 'medical_school_candidate': 11} | {'high': 13, 'medium': 11} |
| broad_discovery_low_plus | 92 | {'medical_school': 13, 'related_medical_institution': 55, 'unknown_or_related': 13, 'medical_school_candidate': 11} | {'high': 13, 'low': 67, 'medium': 12} |

## 3. Best query strategy for embedded faculties/schools

- Use strict_high_confidence_only for a defensible core list.
- Use balanced_strict_medium_plus for a practical review list.
- Use broad_discovery_low_plus as a candidate discovery layer, not as the final list.
- For embedded faculties, combine institution search with works/authors affiliation queries against parent universities.

Embedded probe used: `GET /works?filter=authorships.institutions.continent:africa&search=<term>&group_by=authorships.institutions.id`. This helps surface parent universities via medicine/nursing/health-sciences works when faculties are not standalone institution records.

## 4. Main false positives and false negatives

False positives usually come from medical keywords in non-school entities: hospitals, research institutes, NGOs/foundations, medical councils, associations, publishers, and government bodies.

False negatives usually occur when a Faculty/School/College of Medicine is embedded inside a parent university and not separately represented as an OpenAlex institution.

Broad-mode false-positive risk examples found: **55**. False-negative risk examples found: **33**. See `outputs/false_positive_negative_audit.json`.

## 5. What the authors endpoint provides for 3 sample institutions

### Lusaka Apex Medical University (ZM)

- OpenAlex ID: https://openalex.org/I3133036570
- Institution type: education
- Authors matched by last known institution: 331
- Provides: disambiguated author profiles, ORCID when available, works/citations, last known institutions, affiliation history where available, topics, and works API URL.
- Does not provide: official staff directory, employment verification, guaranteed department/faculty membership, or perfectly complete historical affiliations.

### University of Medical Sciences and Technology (SD)

- OpenAlex ID: https://openalex.org/I145354842
- Institution type: education
- Authors matched by last known institution: 998
- Provides: disambiguated author profiles, ORCID when available, works/citations, last known institutions, affiliation history where available, topics, and works API URL.
- Does not provide: official staff directory, employment verification, guaranteed department/faculty membership, or perfectly complete historical affiliations.

### Sefako Makgatho Health Sciences University (ZA)

- OpenAlex ID: https://openalex.org/I2802393258
- Institution type: education
- Authors matched by last known institution: 2094
- Provides: disambiguated author profiles, ORCID when available, works/citations, last known institutions, affiliation history where available, topics, and works API URL.
- Does not provide: official staff directory, employment verification, guaranteed department/faculty membership, or perfectly complete historical affiliations.


## Bottom line

OpenAlex has enough data for a reproducible retrieval audit and candidate discovery workflow. It does not reliably expose a complete official list of African medical schools or embedded faculties. The best approach is a two-layer audit: (1) strict institution retrieval for high-confidence schools, and (2) works/authors affiliation analysis to discover embedded faculties inside broader universities.
