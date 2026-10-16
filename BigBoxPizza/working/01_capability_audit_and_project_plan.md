# Capability & input audit, project plan

## Research start
- Started: **2026-10-15T23:47:06Z** (UTC). Valuation date used in the model: 2026-10-16.

## Project files found at start
- `README.md` (client repository readme), `ezstart_network write up.pdf` (unrelated to this project).
- Uploaded quotation: one-page image PDF (no text layer; "Microsoft: Print To PDF", author "Mahmoud Bakr", created 2026-09-23 16:04 +03:00). Preserved as `evidence/NFC-OFFER-2026-0120_original.pdf` (SHA-256 identical to the upload) and transcribed visually from a 400-dpi render.
- No existing spreadsheets or calculations.

## Tools available
- Python 3.13, openpyxl 3.1.5, pandas, pypdf, pdfplumber, Pillow; matplotlib installed from PyPI.
- LibreOffice 24.2 with Python-UNO, used for headless recalculation of the workbook.
- poppler (pdftoppm, pdftotext).

## Research capabilities tested
| Method | Result |
|---|---|
| Web search tool | Worked; returns page titles, URLs and extracts. Used for all research |
| Page-fetch tool | Failed for every host tried (DNS resolution error, including Wikipedia) |
| Direct HTTP (curl) to hts.usitc.gov, ecfr.gov, federalregister.gov, api.census.gov, cbp.gov, rulings.cbp.gov, cbe.org.eg, nilecarton.com | Blocked by the environment's network policy (403 at the egress proxy) |
| Package registry (PyPI) | Worked |
| One-shot reachability check of every source URL (`scripts/check_urls.py`, 16-Oct-2026) | All 70 source hosts denied by the egress policy (proxy CONNECT 403); no source page could be opened |

Consequence: official documents were read through search-engine extracts, never by opening the page. Every source records this access method, and confidence levels are capped accordingly. Census trade statistics (USA Trade Online / API) could not be queried; import-unit values were taken from the AD/CVD petition data instead.

## Project plan (executed)
| Step | Workstreams | Status |
|---|---|---|
| 1 | Audit, quotation extraction, structure | Done |
| 2 | Supplier & quotation (A), product engineering (B) | Done – supplier identity UNVERIFIED |
| 3 | Classification & tariffs (F), compliance (G) | Done – broker confirmation pending |
| 4 | Containers (C), origin (D), freight (E), destination (H) | Done – estimates, no quotes |
| 5 | Market & competitors (I), suppliers (M) | Done – listings, no buyer quotes |
| 6 | Landed cost (J), pricing (K), IOR structures (L) | Done (workbook) |
| 7 | RFQ pack (N), workbook (O), deliverables | Done |
| 8 | QA validation | Done – workbook validation PASS; formal checklist in `outputs/qa_validation_checklist.md` |

## Missing-information register
See `BigBoxPizza_Assumptions_and_Gaps.md` and the workbook sheet "Quote Requests & Missing Data" (19 items, ranked).

## Network note for the client
The environment's network policy denied direct access to the official hosts above. To allow direct retrieval in a future session, add those domains under the cloud environment's network settings (Allowed domains).
