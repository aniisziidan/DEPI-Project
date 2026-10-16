"""Write BigBoxPizza_Source_Register.csv (UTF-8, RFC-4180 quoting) from sources_data.py."""
import csv
import os
import sys

import sources_data as SD

FIELDS = [("source_id", "id"), ("title", "title"), ("organisation", "org"), ("url_or_path", "url"), ("publication_or_revision_date", "pub_date"),
          ("access_date", "access_date"), ("access_method", "method"), ("relevant_extract", "extract"), ("claim_supported", "claim"),
          ("primary_or_secondary", "ptype"), ("evidence_classification", "evidence"), ("confidence", "confidence"), ("limitation", "limitation")]


def write(path):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        w.writerow([h for h, _ in FIELDS])
        for s in sorted(SD.SOURCES, key=lambda x: x["id"]):
            w.writerow([str(s[k]).replace("\r", " ").replace("\n", " ") for _, k in FIELDS])
    return path


def validate(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    hdr, body = rows[0], rows[1:]
    assert all(len(r) == len(hdr) for r in body), "ragged CSV"
    ids = [r[0] for r in body]
    assert len(ids) == len(set(ids)), "duplicate source IDs"
    assert all(r[0].startswith("S") for r in body)
    ev = hdr.index("evidence_classification")
    allowed = {"VERIFIED_OFFICIAL", "VERIFIED_QUOTE", "VERIFIED_SUPPLIER", "VERIFIED_MARKET", "CALCULATED", "ESTIMATED", "ASSUMED", "UNRESOLVED"}
    assert all(r[ev] in allowed for r in body), "evidence class outside the eight allowed labels"
    return dict(rows=len(body), columns=len(hdr), unique_ids=len(set(ids)))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "BigBoxPizza_Source_Register.csv")
    write(out)
    print(out, validate(out))
