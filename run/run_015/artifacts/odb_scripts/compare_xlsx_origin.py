"""Pointwise reconciliation of a private XLSX cell export and Origin column export."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx-raw", required=True)
    ap.add_argument("--xlsx-audit", required=True)
    ap.add_argument("--origin-export", required=True)
    ap.add_argument("--origin-source", required=True)
    ap.add_argument("--origin-graph-labels")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    raw_path = Path(args.xlsx_raw).resolve()
    audit_path = Path(args.xlsx_audit).resolve()
    origin_path = Path(args.origin_export).resolve()
    source_path = Path(args.origin_source).resolve()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with raw_path.open(newline="", encoding="utf-8") as stream:
        xlsx = list(csv.DictReader(stream))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    export = json.loads(origin_path.read_text(encoding="utf-8"))
    if len(export["pages"]) != 1 or len(export["pages"][0]["sheets"]) != 1:
        raise ValueError("ambiguous Origin page/sheet inventory")
    sheet = export["pages"][0]["sheets"][0]
    columns = sheet["columns"]
    if len(columns) != 2 or len(xlsx) != audit["point_count"]:
        raise ValueError("ambiguous columns or XLSX point count")
    count = len(xlsx)
    if any(len(c["data"]) != count or c["Rows"] != count for c in columns):
        raise ValueError("Origin column count mismatch")
    details = []
    stats = []
    for index, field in enumerate(("raw_displacement", "raw_load")):
        origin_values = columns[index]["data"]
        per_col = []
        for i, (row, item) in enumerate(zip(xlsx, origin_values), start=1):
            if not isinstance(item, list) or len(item) != 1:
                raise ValueError("non-scalar Origin cell at %d" % i)
            xval = Decimal(row[field])
            oval = Decimal(str(item[0]))
            delta = abs(xval - oval)
            scale = max(abs(xval), abs(oval))
            rel = delta / scale if scale else Decimal(0)
            per_col.append((xval, oval, delta, rel))
            if index == 0:
                details.append({"point_index": i, "xlsx_source_row": row["source_row"],
                                "xlsx_x_cell": row["source_x_cell"], "xlsx_y_cell": row["source_y_cell"]})
            details[i - 1].update({field + "_xlsx": str(xval), field + "_origin": str(oval),
                                field + "_abs_diff": str(delta), field + "_relative_diff": str(rel)})
        worst_abs = max(range(count), key=lambda i: per_col[i][2])
        worst_rel = max(range(count), key=lambda i: per_col[i][3])
        stats.append({"column_index": index, "xlsx_field": field,
                      "origin_name": columns[index].get("Name"),
                      "origin_dataset": columns[index].get("dataset"),
                      "point_count": count,
                      "xlsx_min": str(min(v[0] for v in per_col)),
                      "xlsx_max": str(max(v[0] for v in per_col)),
                      "origin_min": str(min(v[1] for v in per_col)),
                      "origin_max": str(max(v[1] for v in per_col)),
                      "max_abs_diff": str(per_col[worst_abs][2]),
                      "max_abs_diff_point_index": worst_abs + 1,
                      "max_relative_diff": str(per_col[worst_rel][3]),
                      "max_relative_diff_point_index": worst_rel + 1,
                      "exact_numeric_decimal_match_count": sum(v[2] == 0 for v in per_col),
                      "max_relative_difference_definition": "abs(XLSX-Origin) / max(abs(XLSX), abs(Origin)); 0 at both-zero"})
    with (out / "xlsx_origin_pointwise.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    report = {
        "status": "NUMERIC_RECONCILIATION_COMPLETE_SOURCE_PROVENANCE_UNKNOWN",
        "xlsx_source_relative_path": audit.get("source_relative_path"),
        "xlsx_source_sha256": audit["source_sha256_after"],
        "xlsx_raw_relative_path": str(raw_path), "xlsx_raw_sha256": digest(raw_path),
        "origin_source_relative_path": str(source_path),
        "origin_source_sha256": digest(source_path),
        "origin_export_relative_path": str(origin_path), "origin_export_sha256": digest(origin_path),
        "reader": export.get("reader"), "readonly": export.get("readonly"),
        "origin_page": export["pages"][0].get("Name"), "origin_sheet": sheet.get("Name"),
        "origin_sheet_allocated_rows": sheet.get("Rows"),
        "origin_column_rows": [c.get("Rows") for c in columns],
        "origin_column_labels": [{k: c.get(k) for k in ("Name", "LongName", "Units", "Comments", "Type", "dataset")} for c in columns],
        "origin_graph_count": len(export.get("graphs", [])),
        "point_count": count, "statistics": stats,
        "pointwise_private_csv": "xlsx_origin_pointwise.csv",
        "interpretation": "Compare original XLSX cell numeric strings against Origin exported scalars in source order. Differences may reflect decimal serialization; this is a numeric, not provenance, test.",
        "source_provenance": "UNKNOWN",
        "processing_history": "UNKNOWN",
        "canonical_recommendation": "Use the row-mapped raw XLSX numeric series as a content-addressed candidate and the OPJU export as numeric corroboration. Preserve both source hashes and all unit labels. Physical units, original-record provenance and processing history require separate verification.",
        "formal_loss": None,
    }
    if args.origin_graph_labels:
        label_path = Path(args.origin_graph_labels).resolve()
        lookup = {x["name"]: x["text"] for x in json.loads(label_path.read_text(encoding="utf-8"))}
        def unit(label):
            match = re.search(r"\(([^()]*)\)\s*$", label or "")
            return match.group(1).strip() if match else None
        y_conflict = unit(audit.get("raw_y_label")) != unit(lookup.get("YL"))
        report["cross_source_unit_conflict"] = {
            "origin_graph_labels_relative_path": str(label_path),
            "origin_graph_labels_sha256": digest(label_path),
            "xlsx_x_header": audit.get("raw_x_label"),
            "xlsx_y_header": audit.get("raw_y_label"),
            "origin_graph_x_label": lookup.get("XB"),
            "origin_graph_y_label": lookup.get("YL"),
            "y_unit_conflict": y_conflict,
            "resolution_required": y_conflict,
        }
        report["experimental_force_unit_confirmed"] = False
        if y_conflict:
            report["canonical_recommendation"] = "Use the row-mapped raw XLSX numeric series as a content-addressed candidate and the OPJU export as numeric corroboration. Keep the conflicting Y labels and both source hashes. Do not promote XLSX force_n to physically confirmed N, identify either file as the original instrument record, or compute FE Loss until the unit conflict and alignment are resolved."
    (out / "xlsx_origin_reconciliation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "point_count": count, "statistics": stats}, ensure_ascii=False))


if __name__ == "__main__":
    main()
