# OpenAlex Scrapper

Small Python service/CLI to retrieve medical-school-like institutions in Africa using the OpenAlex Institutions API.

## Why this approach

OpenAlex institutions are universities and other organizations that authors use as affiliations.

OpenAlex supports filters such as `country_code`, `continent`, and `type`, but it does not have a dedicated `medical_school` institution type. This project therefore retrieves institution records using:

- African country codes
- `type:education`
- medical search terms like `medical school`, `school of medicine`, `faculty of medicine`, `college of medicine`, and `health sciences`
- a final local name filter to reduce unrelated institutions

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run as an API

```bash
uvicorn app:app --reload --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Test without internet using bundled sample data:

```bash
curl 'http://127.0.0.1:8000/medical-schools/africa?sample=true&max_results=5' | python -m json.tool
```

Real OpenAlex test:

```bash
curl 'http://127.0.0.1:8000/medical-schools/africa?max_results=25&per_page=50&mailto=YOUR_EMAIL@example.com' | python -m json.tool
```

## Run as a CLI

Offline sample:

```bash
python cli.py --sample --max-results 5
```

Real OpenAlex call:

```bash
python cli.py --max-results 25 --per-page 50 --mailto YOUR_EMAIL@example.com
```

## Direct OpenAlex curl for debugging

```bash
curl 'https://api.openalex.org/institutions?search=medical%20school&filter=type:education,country_code:DZ%7CAO%7CBJ%7CBW%7CBF%7CBI%7CCV%7CCM%7CCF%7CTD%7CKM%7CCD%7CCG%7CCI%7CDJ%7CEG%7CGQ%7CER%7CSZ%7CET%7CGA%7CGM%7CGH%7CGN%7CGW%7CKE%7CLS%7CLR%7CLY%7CMG%7CMW%7CML%7CMR%7CMU%7CMA%7CMZ%7CNA%7CNE%7CNG%7CRW%7CST%7CSN%7CSC%7CSL%7CSO%7CZA%7CSS%7CSD%7CTZ%7CTG%7CTN%7CUG%7CZM%7CZW&per-page=5' | python -m json.tool
```

## Notes

- For production use, add caching because OpenAlex responses can be large.
- Add your email via `mailto` or `OPENALEX_MAILTO` to use the OpenAlex polite pool.
- This is a first-pass retriever, not a verified canonical directory of all African medical schools.
