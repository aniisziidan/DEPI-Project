# BigBoxPizza – Egypt → US pizza-box import: due-diligence package

**Verdict: NO-GO under modeled conditions** (see the report §1 and §18).

| Deliverable | File |
|---|---|
| 1. Executive decision report | `BigBoxPizza_US_Market_and_Landed_Cost_Report.md` |
| 2. Excel financial model (formula-driven, recalculated) | `BigBoxPizza_US_Landed_Cost_Model.xlsx` |
| 3. Source register (UTF-8 CSV) | `BigBoxPizza_Source_Register.csv` |
| 4. Assumptions and unresolved questions | `BigBoxPizza_Assumptions_and_Gaps.md` |
| 5. Supplier and logistics RFQ pack | `BigBoxPizza_RFQ_Pack.md` |
| 6. Calculation audit trail | `BigBoxPizza_Calculation_Audit.md` |
| 7. Scripts (reproducible build) | `scripts/` – run `python3 BigBoxPizza/scripts/build_all.py` |
| Evidence | `evidence/` – original NFC quotation PDF (SHA-256 ecfdf33b…f91b0), page render, verbatim transcription |
| Outputs | `outputs/` – charts, loading schematics, `validation_report.md` (workbook recalculation), `qa_validation_checklist.md` (formal QA, brief §21), `url_check.json` (source URL check) |
| Working notes | `working/` – capability audit, project plan, research log |

Workbook validation: PASS – 30,785 formula cells, 0 errors, 189 engine cases equal to the independent Python engine.

Requirements to rebuild: Python 3.11+, openpyxl, matplotlib, LibreOffice (headless, with python3-uno).
