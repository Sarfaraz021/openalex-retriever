# OpenAlex Retrieval Audit — African Medical Schools

Generated at: 2026-05-26T20:37:11.761761+00:00

## Executive summary

OpenAlex is useful for discovering African medical-school-like institutions, but it should not be treated as a canonical directory of medical schools. Its Institutions entity mainly represents organizations appearing in scholarly affiliation metadata, including universities, hospitals, government bodies, research institutes, NGOs, companies, and other entities.

The audit supports a cautious conclusion: OpenAlex has strong bibliographic and affiliation metadata, but it does not consistently expose embedded faculties, departments, schools, or colleges inside parent universities as standalone institution records. Therefore, medical-school discovery needs a two-layer approach: institution retrieval for standalone entities, plus works/authors affiliation analysis for embedded units.

## Confidence and limitations

| Area | Assessment |
|---|---|
| OpenAlex architecture and institution model | High confidence: OpenAlex Institutions represent affiliation organizations, not only schools/universities. |
| Dedicated `medical_school` type | Confirmed absent in this audit approach; no dedicated `medical_school` institution type was available. |
| Embedded faculty limitation | High confidence, but not absolute: many faculties/schools appear embedded under broader universities, while some are standalone records. |
| African institution count | Run-specific API count: 4,022 returned by `filter=continent:africa` at the time of this run. This should be treated as dynamic, not a permanent total. |
| Specific author counts | Run-specific counts from the Authors endpoint at the time of this run. They may change as OpenAlex updates. |
| ROR coverage | Not universal. Many institutions have ROR IDs, but not all OpenAlex institution records should be assumed to have one. |
| Two-layer strategy | Sound methodology for retrieval auditing, but still requires manual validation for final ground truth. |

## 1. African institution coverage by country and type

At the time of this run, `filter=continent:africa` returned **4,022** OpenAlex institution records. This is a live API-derived count and should be treated as a snapshot, not a fixed coverage guarantee.

Top countries by institution count:

| Country entity | Country | Count |
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

Interpretation: OpenAlex’s African institution coverage is broad and mixed. It includes education institutions, but also many non-school entities. This explains why a medical keyword search can return hospitals, research institutes, NGOs, councils, associations, and companies alongside universities/colleges.

## 2. Why strict keyword filtering returns a small list

- OpenAlex does not expose a dedicated `medical_school` institution type.
- Strict retrieval only captures entities whose institution names contain strong signals such as `medical university`, `college of medicine`, `school of medicine`, or `faculty of medicine`.
- Many faculties/schools may be represented only as part of a parent university record or through author/works affiliation metadata, not as standalone institution records.
- Broad terms like `medical`, `health`, `nursing`, and `pharmacy` improve recall but introduce many non-school entities.

Strategy comparison from this run:

| Strategy | Count | Category counts | Confidence counts |
|---|---:|---|---|
| strict_high_confidence_only | 13 | {'medical_school': 13} | {'high': 13} |
| balanced_strict_medium_plus | 24 | {'medical_school': 13, 'medical_school_candidate': 11} | {'high': 13, 'medium': 11} |
| broad_discovery_low_plus | 92 | {'medical_school': 13, 'related_medical_institution': 55, 'unknown_or_related': 13, 'medical_school_candidate': 11} | {'high': 13, 'low': 67, 'medium': 12} |

Interpretation: strict keyword filtering returns a smaller but more defensible list. Broad retrieval should be used for discovery and audit comparison, not as the final medical-school list.

## 3. Query strategy for embedded faculties/schools

Recommended retrieval strategy:

1. Use `strict_high_confidence_only` for a defensible standalone-institution core list.
2. Use `balanced_strict_medium_plus` for a practical review list that includes health-sciences/nursing/pharmacy candidates.
3. Use `broad_discovery_low_plus` only as a discovery layer to inspect what strict retrieval is excluding.
4. For embedded faculties, combine institution search with works/authors affiliation queries against broader parent universities.

Embedded probe used:

`GET /works?filter=authorships.institutions.continent:africa&search=<term>&group_by=authorships.institutions.id`

This can surface parent universities appearing in medicine/nursing/health-sciences works when the specific faculty/school is not a standalone OpenAlex institution. It is a discovery signal, not proof that every embedded faculty is fully represented.

## 4. Main false positives and false negatives

False positives usually come from medical keywords in non-school entities, such as:

- hospitals and medical centres
- research institutes and research councils
- NGOs/foundations
- medical councils and associations
- publishers, companies, and government bodies

False negatives usually occur when:

- a Faculty/School/College of Medicine is embedded inside a parent university record
- OpenAlex records the parent university but not the sub-unit
- the institution name lacks explicit terms like `medicine`, `medical`, or `health sciences`
- author affiliations mention departments/faculties in raw affiliation text, but the normalized institution remains the parent university

Broad-mode risk counts from this run:

- False-positive risk examples found: **55**
- False-negative risk examples found: **33**

See `outputs/false_positive_negative_audit.json` for the exact examples.

## 5. What the authors endpoint provides for 3 sample institutions

The Authors endpoint provides useful bibliographic author metadata linked to institutions, but it should not be treated as a complete staff/faculty directory.

### Lusaka Apex Medical University (ZM)

- OpenAlex ID: https://openalex.org/I3133036570
- Institution type: education
- Authors matched by `last_known_institutions.id` at time of run: 331
- Provides: disambiguated author profiles, ORCID when available, works/citations, last known institutions, affiliation history where available, topics, and works API URL.
- Does not provide: official staff directory, employment verification, guaranteed department/faculty membership, or perfectly complete historical affiliations.

### University of Medical Sciences and Technology (SD)

- OpenAlex ID: https://openalex.org/I145354842
- Institution type: education
- Authors matched by `last_known_institutions.id` at time of run: 998
- Provides: disambiguated author profiles, ORCID when available, works/citations, last known institutions, affiliation history where available, topics, and works API URL.
- Does not provide: official staff directory, employment verification, guaranteed department/faculty membership, or perfectly complete historical affiliations.

### Sefako Makgatho Health Sciences University (ZA)

- OpenAlex ID: https://openalex.org/I2802393258
- Institution type: education
- Authors matched by `last_known_institutions.id` at time of run: 2,094
- Provides: disambiguated author profiles, ORCID when available, works/citations, last known institutions, affiliation history where available, topics, and works API URL.
- Does not provide: official staff directory, employment verification, guaranteed department/faculty membership, or perfectly complete historical affiliations.

## Bottom line

OpenAlex has enough data for a reproducible retrieval audit and candidate discovery workflow, but it does not reliably expose a complete official list of African medical schools or embedded faculties. The best approach is a cautious two-layer audit: (1) strict institution retrieval for high-confidence standalone schools, and (2) works/authors affiliation analysis to discover possible embedded faculties inside broader universities.

The output should be considered a structured candidate/audit dataset, not final ground truth without manual validation.