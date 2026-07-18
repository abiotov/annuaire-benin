<div align="center">

# 🇧🇯 Annuaire Bénin

**Benin's national business directory: 500,000 raw rows turned into a clean, measured, queryable database.**

[![CI](https://github.com/abiotov/annuaire-benin/actions/workflows/ci.yml/badge.svg)](https://github.com/abiotov/annuaire-benin/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)

*This is the English summary. The [French README](README.md) is the reference document, and all project docs are in French: the project is about Beninese data.*

**[→ Open the interactive economic atlas](https://abiotov.github.io/annuaire-benin/atlas/)**

</div>

---

West African business directories exist, but only in raw form: Excel exports where the same company appears four times, where the activity is a free-text sentence, and where phone numbers mix two national numbering plans. This project takes such an export (Benin's, about 235,000 real businesses) and turns it, one measured step at a time, into a usable database: every conversion is counted, every anomaly is qualified, every merge is proven.

## The numbers

| Measure | Value |
|---|---:|
| Raw rows ingested | 496,729 (in 50 s) |
| Phone numbers migrated to the 2024 ten-digit plan (E.164) | 386,893 (77.9%) |
| Numbers truncated by the source export, detected and flagged | 109,780 (22.1%) |
| Exact + fuzzy deduplication | 235,360 entities, then 235,107 final businesses |
| Hand-annotated ground truth for record linkage | 420 pairs (95 same, 325 different) |
| Measured merge precision (calibrated threshold) | 83.1% (vs 51.8% before calibration) |
| Activity classification | 334 registry labels → 25 sectors, 100% coverage |
| Tests | 77 unit tests + Playwright smoke tests in CI |

## What makes it interesting

- **A real data-forensics story.** All source phone values are exactly 8 characters long; 22% start with "01", a prefix that did not exist in the old plan. Proof (documented with digit-distribution evidence) that the source export truncated new 10-digit numbers: those numbers are unrecoverable, and the pipeline flags them instead of inventing digits.
- **Measured record linkage.** Multi-channel blocking (280,377 candidate pairs out of 27 billion possible), a decomposed similarity score, and a threshold calibrated against a hand-annotated ground truth. An LLM arbitration layer was evaluated against that ground truth first, and **rejected for automatic merging** (insufficient precision, tiny positive sample); it now serves as a triage step for human review. Knowing when not to deploy is also a result.
- **Classification without a model.** Profiling revealed the "activity" field is a closed vocabulary of 334 registry labels, not free text: an exhaustive, fully reviewed mapping table beats any classifier here, with 100% coverage and zero model error.
- **A published, product-grade atlas.** Choropleth of all 77 communes directly on OpenStreetMap (vendored Leaflet, country mask, street-level zoom), three metrics (volume, per-1,000-inhabitants using INSAE census data, and a fixed-scale location quotient), a 25-sector small-multiples panorama, commune comparison, per-commune top neighbourhoods, CSV export, sortable table, shareable URLs, light/dark themes.
- **French natural-language search, two layers.** An embedded interpreter (a 414-keyword lexicon derived from the classification table, 77 communes, an intent grammar) answers instantly and offline; free-form questions are translated into structured intents by Gemini through a Cloudflare Worker that keeps its key server-side. The LLM never produces a number: everything is recomputed from the page's aggregates, and AI-interpreted answers are labeled as such.
- **Privacy by construction.** The source file contains personal data and is never published; the repo and the atlas only ever expose aggregates. No GPS coordinates exist in the registry, so the map shows commune-level densities, never individual businesses.

## Pipeline

```
private Excel source (never committed)
        |
   [1] Ingestion + contact validation     <- annuaire_benin/contacts, ingest.py
   [2] Deduplication (record linkage)     <- annuaire_benin/dedupe (calibrated + arbitrated)
   [3] Activity classification            <- annuaire_benin/classify (334 -> 25, exhaustive)
        |
   clean SQLite database (235,107 businesses)
        |
   [4] Economic atlas                     <- annuaire_benin/atlas -> GitHub Pages
   [5] Natural-language search            <- embedded interpreter + Cloudflare Worker (LLM as parser)
```

## Quick start

```bash
git clone https://github.com/abiotov/annuaire-benin.git
cd annuaire-benin
pip install -e ".[dev]"

pytest          # 77 unit tests
ruff check .    # lint

# Ingest a source workbook into SQLite
python -m annuaire_benin.ingest path/to/source.xlsx --db data/annuaire.db
```

Without the private source file, tests and code remain fully runnable: they never depend on it.

## License

[MIT](LICENSE). Map boundaries: [geoBoundaries](https://www.geoboundaries.org/) (public domain). Basemap: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. Population: INSAE, RGPH-4 2013 census.
