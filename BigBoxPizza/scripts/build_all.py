"""Reproducible end-to-end build of every BigBoxPizza deliverable.

    python3 BigBoxPizza/scripts/build_all.py

Steps
 1. Geometry diagrams + report charts (loading_model.py, charts.py)
 2. Formula workbook (build_model.py) → outputs/_build_formulas.xlsx
 3. LibreOffice headless recalculation + validation against the Python engine (validate_model.py)
    → BigBoxPizza_US_Landed_Cost_Model.xlsx (recalculated, formulas + cached values)
    → outputs/validation_report.md / .json
 4. Source register CSV (build_source_register.py)
 5. Markdown deliverables (write_reports.py, write_docs.py)
 6. QA validation checklist, brief §21 (qa_checklist.py) → outputs/qa_validation_checklist.md
    (check_urls.py is network-dependent and run separately; its last result is read from outputs/url_check.json)
No hidden state: every step reads only inputs.py, sources_data.py, registers.py and the evidence folder.
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_model  # noqa: E402
import build_source_register  # noqa: E402
import charts  # noqa: E402
import qa_checklist  # noqa: E402
import validate_model  # noqa: E402
import write_docs  # noqa: E402
import write_reports  # noqa: E402


def main():
    out = os.path.join(PROJ, "outputs")
    os.makedirs(out, exist_ok=True)
    print("1/6 charts")
    charts.main(out)
    print("2/6 workbook (formulas)")
    tmp = os.path.join(out, "_build_formulas.xlsx")
    build_model.main(tmp)
    print("3/6 recalculation + validation (LibreOffice)")
    final = os.path.join(PROJ, "BigBoxPizza_US_Landed_Cost_Model.xlsx")
    res = validate_model.main(tmp, final, os.path.join(out, "validation_report.md"))
    print("    status", res["status"], "errors", res["error_count"], "engine mismatches", res["engine_mismatch_count"])
    if res["status"] != "PASS":
        raise SystemExit("Validation failed – see outputs/validation_report.md")
    os.remove(tmp)
    print("4/6 source register")
    csvp = os.path.join(PROJ, "BigBoxPizza_Source_Register.csv")
    build_source_register.write(csvp)
    print("    ", build_source_register.validate(csvp))
    print("5/6 Markdown deliverables")
    write_reports.main(PROJ)
    write_docs.main(PROJ)
    print("6/6 QA validation checklist")
    overall, stat = qa_checklist.main()
    if stat.get("FAIL"):
        raise SystemExit("QA checklist has FAIL items – see outputs/qa_validation_checklist.md")
    print("done")


if __name__ == "__main__":
    main()
