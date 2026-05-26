# OpenAlex Retriever

A Python CLI, FastAPI service, and reproducible audit toolkit for retrieving and evaluating medical-school-like institutions in Africa using the official OpenAlex API.

This is **API-based data retrieval**, not HTML scraping.

## Why classification is needed

OpenAlex does not expose a dedicated `medical_school` institution type. A broad search for terms like `medical`, `medicine`, or `health sciences` returns useful but mixed results, including:

- medical universities and colleges
- faculties/schools of medicine
- health sciences universities
- research institutes
- hospitals and medical centres
- councils, associations, NGOs, and publishers

This project improves precision by classifying every result into:

- `medical_school` — high-confidence school/university/college/faculty match
- `medical_school_candidate` — medium-confidence teaching institution candidate
- `related_medical_institution` — relevant medical institution, but not a school
- `unknown_or_related` — weak or unclear match

Each row includes `category`, `confidence`, `is_medical_school`, `matched_keyword`, and a human-readable `reason`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional environment variables:

```bash
export OPENALEX_MAILTO=your_email@example.com
export OPENALEX_API_KEY=your_openalex_api_key
```

## Run tests

```bash
pytest -q
```

## Run the retrieval audit

Peter's requested audit should be run with:

```bash
python scripts/audit_openalex.py --mailto YOUR_EMAIL@example.com --max-results 200
```

Or, if `OPENALEX_MAILTO` is already exported:

```bash
python scripts/audit_openalex.py --max-results 200
```

The audit writes reproducible evidence into `outputs/`:

```text
outputs/openalex_retrieval_audit_report.md
outputs/audit_manifest.json
outputs/coverage_by_country_type.json
outputs/coverage_by_country.csv
outputs/coverage_by_type.csv
outputs/coverage_country_type_matrix.csv
outputs/query_strategy_comparison.json
outputs/strict_high_confidence_only.csv
outputs/balanced_strict_medium_plus.csv
outputs/broad_discovery_low_plus.csv
outputs/embedded_faculty_strategy_audit.json
outputs/false_positive_negative_audit.json
outputs/authors_endpoint_sample_audit.json
```

The audit answers:

1. OpenAlex coverage of African institutions by country and type.
2. Why strict keyword filtering returns a small medical-school list.
3. Query strategies for embedded faculties, colleges, and schools inside broader universities.
4. Main false positives and false negatives.
5. What the authors endpoint provides for three sample institutions.

## Run as an API

```bash
uvicorn app:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Strict medical-school candidates only, using offline sample data:

```bash
curl 'http://127.0.0.1:8000/medical-schools/africa?sample=true&strict_only=true&min_confidence=medium' | python -m json.tool
```

Broad mode, including related institutions:

```bash
curl 'http://127.0.0.1:8000/medical-schools/africa?sample=true&strict_only=false&min_confidence=low' | python -m json.tool
```

Live OpenAlex strict test:

```bash
curl 'http://127.0.0.1:8000/medical-schools/africa?max_results=50&per_page=50&strict_only=true&min_confidence=medium&mailto=YOUR_EMAIL@example.com' | python -m json.tool
```

Filter to one country:

```bash
curl 'http://127.0.0.1:8000/medical-schools/africa?country_code=NG&strict_only=true&max_results=25&mailto=YOUR_EMAIL@example.com' | python -m json.tool
```

Filter to high-confidence only:

```bash
curl 'http://127.0.0.1:8000/medical-schools/africa?strict_only=true&min_confidence=high&max_results=25&mailto=YOUR_EMAIL@example.com' | python -m json.tool
```

## Run as a CLI

Strict JSON output:

```bash
python cli.py --max-results 50 --per-page 50 --mailto YOUR_EMAIL@example.com
```

CSV export:

```bash
python cli.py --max-results 100 --format csv --output african_medical_schools.csv --mailto YOUR_EMAIL@example.com
```

Country-specific CSV export:

```bash
python cli.py --country-code NG --country-code ZA --max-results 100 --format csv --output ng_za_medical_schools.csv --mailto YOUR_EMAIL@example.com
```

Broad discovery mode:

```bash
python cli.py --no-strict-only --min-confidence low --max-results 100 --output broad_medical_institutions.json --mailto YOUR_EMAIL@example.com
```

Offline sample mode:

```bash
python cli.py --sample --no-save
```

## Output fields

Each result includes:

```text
openalex_id
display_name
country_code
type
homepage_url
works_count
cited_by_count
ror
source_query
category
confidence
is_medical_school
matched_keyword
reason
```

## Recommended workflow for Peter's task

1. Run `scripts/audit_openalex.py` first to generate the audit report and evidence files.
2. Use strict/balanced retrieval for a defensible candidate list.
3. Use broad retrieval and embedded works/authors probes to understand false positives and false negatives.
4. Manually verify edge cases because OpenAlex does not provide a canonical `medical_school` entity type.

## Limitations

This project produces a reproducible audit and high-quality candidate list, not a guaranteed official directory of every medical school in Africa. Accuracy depends on OpenAlex institution naming, ROR metadata, author affiliation metadata, and search coverage.
