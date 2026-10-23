"""Create private, row-mapped candidate curve from audited XLSX XML cells.

This only converts an explicitly evidenced displacement unit; it never alters
zero, compliance, order, signs, outliers, or sampling.
"""
import argparse
import csv
import datetime as dt
from decimal import Decimal
import hashlib
import json
from pathlib import Path

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--private-output", required=True)
    p.add_argument("--sheet", required=True)
    p.add_argument("--x-column", required=True)
    p.add_argument("--y-column", required=True)
    p.add_argument("--first-row", type=int, required=True)
    p.add_argument("--last-row", type=int, required=True)
    p.add_argument("--x-unit", choices=["mm", "m"], required=True)
    p.add_argument("--y-unit", choices=["N"], required=True)
    args = p.parse_args()
    source = Path(args.source).resolve()
    out = Path(args.private_output).resolve()
    data = json.loads((out / "xlsx_cells_full.json").read_text(encoding="utf-8"))
    audit = json.loads((out / "xlsx_audit.json").read_text(encoding="utf-8"))
    assert args.sheet in data
    assert sha(source) == audit["source_sha256_before"] == audit["source_sha256_after"]
    cells = {x["ref"]: x for x in data[args.sheet]["cells"]}
    x_header = cells[args.x_column + str(args.first_row - 1)]["value"]
    y_header = cells[args.y_column + str(args.first_row - 1)]["value"]
    assert args.x_unit.lower() in x_header.lower() and args.y_unit.lower() in y_header.lower()
    scale = Decimal("0.001") if args.x_unit == "mm" else Decimal("1")
    points = []
    for row in range(args.first_row, args.last_row + 1):
        xr, yr = args.x_column + str(row), args.y_column + str(row)
        x, y = cells[xr], cells[yr]
        if x["type"] != "n" or y["type"] != "n" or x["raw_v"] is None or y["raw_v"] is None:
            raise ValueError("non-numeric or missing point at row %d" % row)
        if x["formula"] is not None or y["formula"] is not None:
            raise ValueError("formula point at row %d" % row)
        displacement = Decimal(x["raw_v"])
        force = Decimal(y["raw_v"])
        points.append({"source_row": row, "source_x_cell": xr, "source_y_cell": yr,
                       "raw_displacement": x["raw_v"], "raw_load": y["raw_v"],
                       "displacement_m": str(displacement * scale), "force_n": str(force),
                       "sample_id": None,
                       "source_file": source.name, "source_sheet": args.sheet,
                       "processing_status": "UNIT_CONVERSION_ONLY; ZERO_AND_COMPLIANCE_UNVERIFIED"})
    raw_path = out / "xlsx_raw_points.csv"
    with raw_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["source_file", "source_sheet", "source_row", "source_x_cell", "source_y_cell", "raw_displacement", "raw_load"])
        writer.writeheader()
        for x in points:
            writer.writerow({k: x[k] for k in writer.fieldnames})
    candidate_path = out / "xlsx_candidate_points.csv"
    with candidate_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["displacement_m", "force_n", "sample_id", "source_file", "source_sheet", "source_row", "source_x_cell", "source_y_cell", "processing_status"])
        writer.writeheader()
        for x in points:
            writer.writerow({k: x[k] for k in writer.fieldnames})
    displacements = [Decimal(x["raw_displacement"]) for x in points]
    loads = [Decimal(x["raw_load"]) for x in points]
    peak = max(loads)
    peak_rows = [x["source_row"] for x, v in zip(points, loads) if v == peak]
    chart = audit["charts"]
    chart_checks = []
    for item in chart:
        for series in item["series"]:
            xcache = series.get("category", {}).get("cached_values", [])
            ycache = series.get("value", {}).get("cached_values", [])
            chart_checks.append({"category_cache_count": len(xcache), "value_cache_count": len(ycache),
                                 "category_cache_matches_cells": len(xcache) == len(points) and all(Decimal(v) == x for v, x in zip(xcache, displacements)),
                                 "value_cache_matches_cells": len(ycache) == len(points) and all(Decimal(v) == y for v, y in zip(ycache, loads))})
    sheet = next(s for s in audit["sheets"] if s["name"] == args.sheet)
    audit.update({
        "status": "XLSX_AUDIT_COMPLETE_ALIGNMENT_UNVERIFIED",
        "semantic_review_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        "curve_count_evidenced": 1,
        "independent_sample_count_evidenced": None,
        "source_row_range": [args.first_row, args.last_row],
        "point_count": len(points),
        "raw_x_label": x_header, "raw_y_label": y_header,
        "source_units": {"displacement": args.x_unit, "load": args.y_unit},
        "conversion": "displacement_m = raw_displacement_mm * 0.001; force_n = raw_load_N; no other changes",
        "point_mapping": {"raw": raw_path.name, "candidate": candidate_path.name},
        "values": {"first_displacement_mm": str(displacements[0]), "last_displacement_mm": str(displacements[-1]),
                   "first_load_n": str(loads[0]), "last_load_n": str(loads[-1]),
                   "peak_load_n": str(peak), "peak_source_rows": peak_rows},
        "displacement_strictly_increasing": all(b > a for a, b in zip(displacements, displacements[1:])),
        "load_decrease_after_peak_observed": any(b < a for a, b in zip(loads, loads[1:])),
        "chart_cache_checks": chart_checks,
        "formula_count": sheet["formula_count"],
        "hidden_row_count": len(sheet["hidden_rows"]),
        "hidden_column_span_count": len(sheet["hidden_columns"]),
        "experimental_zero_location": None,
        "displacement_sensor_definition": None,
        "machine_compliance_correction": None,
        "load_cell_calibration_and_sign": None,
        "specimen_and_fixture_conditions": None,
        "loading_unloading_branch_proven": False,
        "notes": [
            "The sheet identifies a displacement/load curve but gives no specimen or replicate identifier.",
            "Monotonic displacement with post-peak load decrease does not establish an unloading branch.",
            "No automatic zero shift, smoothing, point deletion, or sample averaging was performed.",
            "N–m–Pa for FE is a current user declaration; it does not identify the experimental sensor or zero.",
        ],
    })
    (out / "xlsx_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert sha(source) == audit["source_sha256_before"]
    print(json.dumps({"status": audit["status"], "point_count": len(points), "chart_cache_matches": all(all(v for k, v in x.items() if k.endswith("_matches_cells")) for x in chart_checks), "source_unchanged": True}, ensure_ascii=False))

if __name__ == "__main__":
    main()
