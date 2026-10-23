"""Read-only SPT source-unit and fixed-window audit, without FE residuals."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


S = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
     "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_xlsx(path):
    with zipfile.ZipFile(path) as z:
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        sheets = workbook.findall("m:sheets/m:sheet", S)
        if len(sheets) != 1:
            raise ValueError("unexpected sheet count")
        sheet_name = sheets[0].get("name")
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in tree.findall("m:si", S):
                shared.append("".join(node.text or "" for node in si.findall(".//m:t", S)))
        tree = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        cells = {}
        for cell in tree.findall(".//m:sheetData/m:row/m:c", S):
            ref = cell.get("r")
            v = cell.find("m:v", S)
            f = cell.find("m:f", S)
            raw = v.text if v is not None else None
            typ = cell.get("t", "n")
            value = shared[int(raw)] if typ == "s" and raw is not None else raw
            cells[ref] = {"raw": raw, "value": value, "type": typ, "formula": f.text if f is not None else None}
        a_label, b_label = cells["A1"]["value"], cells["B1"]["value"]
        points = []
        for row in range(2, 341):
            a, b = cells.get("A" + str(row)), cells.get("B" + str(row))
            if not a or not b or a["type"] != "n" or b["type"] != "n" or a["formula"] or b["formula"]:
                raise ValueError("missing or nonliteral pair at row %d" % row)
            points.append((row, Decimal(a["raw"]), Decimal(b["raw"]), a["raw"], b["raw"]))
        if len(cells) != 2 * (len(points) + 1):
            raise ValueError("unexpected populated cells")
        chart = ET.fromstring(z.read("xl/charts/chart1.xml"))
        refs = [node.text for node in chart.findall(".//c:f", S) if node.text]
        caches = []
        for cache in chart.findall(".//c:numCache", S):
            caches.append([Decimal(node.text) for node in cache.findall("c:pt/c:v", S)])
        return sheet_name, a_label, b_label, points, refs, caches


def decline_metrics(points, full_peak):
    diffs = [points[i + 1][2] - points[i][2] for i in range(len(points) - 1)]
    dx = [points[i + 1][1] - points[i][1] for i in range(len(points) - 1)]
    if not all(v > 0 for v in dx):
        raise ValueError("non-increasing displacement")
    slopes = [dy / dd for dy, dd in zip(diffs, dx)]
    neg = [v for v in diffs if v < 0]
    largest_contiguous = Decimal(0)
    run_drop = Decimal(0)
    run_len = 0
    marker = None
    for i, dy in enumerate(diffs):
        if dy < 0:
            run_drop -= dy
            run_len += 1
            largest_contiguous = max(largest_contiguous, run_drop)
            if marker is None and run_len >= 3 and run_drop >= full_peak * Decimal("0.01"):
                marker = {"first_source_row": points[i - run_len + 1][0], "last_source_row": points[i + 1][0],
                          "cumulative_drop_raw_y": str(run_drop)}
        else:
            run_drop = Decimal(0)
            run_len = 0
    return {"adjacent_interval_count": len(diffs), "negative_increment_count": len(neg),
            "total_negative_variation_raw_y": str(-sum(neg, Decimal(0))),
            "largest_one_step_drop_raw_y": str(-min(neg)) if neg else "0",
            "largest_contiguous_drop_raw_y": str(largest_contiguous),
            "sustained_drop_marker_1pct_peak_3_steps": marker,
            "min_slope_raw_y_per_mm": str(min(slopes)) if slopes else None,
            "max_slope_raw_y_per_mm": str(max(slopes)) if slopes else None}


def main():
    ap = argparse.ArgumentParser()
    for field in ("workspace", "xlsx", "opju", "origin-export", "graph-labels", "inventory", "declaration", "criteria", "output"):
        ap.add_argument("--" + field, required=True)
    args = ap.parse_args()
    root = Path(args.workspace).resolve()
    paths = {key: Path(getattr(args, key.replace("-", "_"))).resolve() for key in
             ("xlsx", "opju", "origin-export", "graph-labels", "inventory", "declaration", "criteria", "output")}
    out = paths["output"]
    out.mkdir(parents=True, exist_ok=True)
    inventory = json.loads(paths["inventory"].read_text(encoding="utf-8"))
    expected = {entry["path"].replace("\\", "/"): entry["sha256"] for entry in inventory["files"]}
    xlsx_sha, opju_sha = sha(paths["xlsx"]), sha(paths["opju"])
    if expected[paths["xlsx"].relative_to(root).as_posix()] != xlsx_sha or expected[paths["opju"].relative_to(root).as_posix()] != opju_sha:
        raise ValueError("SPT source hash mismatch")
    criteria = json.loads(paths["criteria"].read_text(encoding="utf-8"))
    window_start, window_end = (Decimal(str(v)) for v in criteria["candidate_window_displacement_mm_inclusive"])
    declaration = json.loads(paths["declaration"].read_text(encoding="utf-8"))
    sheet, a_label, b_label, points, chart_refs, caches = read_xlsx(paths["xlsx"])
    x = [p[1] for p in points]
    y = [p[2] for p in points]
    full_peak = max(y)
    peak_rows = [p[0] for p in points if p[2] == full_peak]
    first_peak = next(i for i, p in enumerate(points) if p[2] == full_peak)
    first_postpeak_decrease = next((points[i + 1][0] for i in range(first_peak, len(points) - 1) if y[i + 1] < y[i]), None)
    window = [p for p in points if window_start <= p[1] <= window_end]
    if not window or window[0][1] != window_start or window[-1][1] != window_end:
        raise ValueError("fixed window endpoints not measured")
    if not all(b > a for a, b in zip(x, x[1:])):
        raise ValueError("displacement not strictly increasing")
    chart_checks = [len(c) == len(points) and all(a == b for a, b in zip(c, vals)) for c, vals in zip(caches, (x, y))]
    export = json.loads(paths["origin-export"].read_text(encoding="utf-8"))
    if len(export["pages"]) != 1 or len(export["pages"][0]["sheets"]) != 1:
        raise ValueError("ambiguous SPT Origin export")
    osheet = export["pages"][0]["sheets"][0]
    cols = osheet["columns"]
    if len(cols) != 2 or any(len(c["data"]) != len(points) for c in cols):
        raise ValueError("Origin point count mismatch")
    stats = []
    for ci, values in enumerate((x, y)):
        exported = [Decimal(str(item[0])) for item in cols[ci]["data"]]
        absolute = [abs(a - b) for a, b in zip(values, exported)]
        relative = [d / max(abs(a), abs(b)) if max(abs(a), abs(b)) else Decimal(0)
                    for a, b, d in zip(values, exported, absolute)]
        stats.append({"column": cols[ci]["Name"], "type_code": cols[ci]["Type"], "row_count": cols[ci]["Rows"],
                      "max_abs_numeric_difference": str(max(absolute)), "max_relative_numeric_difference": str(max(relative)),
                      "exact_decimal_match_count": sum(v == 0 for v in absolute)})
    labels = {item["name"]: item["text"] for item in json.loads(paths["graph-labels"].read_text(encoding="utf-8"))}
    if labels.get("XB") != "Displacement(mm)" or labels.get("YL") != "load(mm)":
        raise ValueError("Origin graph labels differ from expected auditable evidence")
    if a_label != "displacement (mm)" or b_label != "load (N)":
        raise ValueError("XLSX headers differ from expected auditable evidence")
    raw_csv = out / "spt_source_points.csv"
    with raw_csv.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["source_row", "displacement_mm_raw", "load_raw", "source_x_cell", "source_y_cell"])
        for row, _, _, xv, yv in points:
            writer.writerow([row, xv, yv, "A" + str(row), "B" + str(row)])
    report = {
        "status": "SPT_SOURCE_WINDOW_AUDITED_FORCE_UNIT_UNRESOLVED",
        "source_sha256_before": {"xlsx": xlsx_sha, "opju": opju_sha},
        "source_sha256_after": {"xlsx": sha(paths["xlsx"]), "opju": sha(paths["opju"])},
        "source_unchanged": sha(paths["xlsx"]) == xlsx_sha and sha(paths["opju"]) == opju_sha,
        "source_paths_relative": [paths["xlsx"].relative_to(root).as_posix(), paths["opju"].relative_to(root).as_posix()],
        "origin_export_relative_path": paths["origin-export"].relative_to(root).as_posix(),
        "origin_export_sha256": sha(paths["origin-export"]),
        "origin_graph_labels_relative_path": paths["graph-labels"].relative_to(root).as_posix(),
        "origin_graph_labels_sha256": sha(paths["graph-labels"]),
        "declaration_relative_path": paths["declaration"].relative_to(root).as_posix(),
        "declaration_sha256": sha(paths["declaration"]),
        "prefe_criteria_relative_path": paths["criteria"].relative_to(root).as_posix(),
        "prefe_criteria_sha256": sha(paths["criteria"]),
        "xlsx": {"sheet": sheet, "headers": {"A1": a_label, "B1": b_label},
                 "point_count": len(points), "source_rows": [points[0][0], points[-1][0]],
                 "chart_references": chart_refs, "chart_cache_numeric_matches_cells": chart_checks},
        "origin": {"page": export["pages"][0]["Name"], "sheet": osheet["Name"],
                   "column_labels": [{k: c.get(k) for k in ("Name", "LongName", "Units", "Comments", "Type", "Rows", "dataset")} for c in cols],
                   "plot_datasets": [p.get("dataset") for g in export.get("graphs", []) for layer in g.get("layers", []) for p in layer.get("plots", [])],
                   "graph_axes": {"XB": labels["XB"], "YL": labels["YL"]}, "numeric_comparison": stats},
        "force_unit_conflict": {"xlsx_B1": b_label, "origin_YL": labels["YL"],
                                "word_load_dimensionally_inconsistent_with_mm": True,
                                "resolution": "UNKNOWN; XLSX N is a candidate claim, not independently confirmed by the declaration or OPJU column Units"},
        "collaborator_declaration": {"class": declaration["evidence_class"],
                                     "displacement": declaration["displacement"],
                                     "correction": declaration["correction"],
                                     "geometry_mm": {"thickness": declaration["specimen_thickness_mm"],
                                                     "diameter": declaration["specimen_diameter_mm"],
                                                     "lower_support_hole": declaration["lower_support_hole_diameter_mm"]},
                                     "force_unit_stated": False,
                                     "algorithm_independently_verified": False},
        "full_curve": {"x_min_mm": str(min(x)), "x_max_mm": str(max(x)),
                       "peak_load_raw_y": str(full_peak), "peak_source_rows": peak_rows,
                       "peak_x_mm_first": str(points[first_peak][1]),
                       "first_postpeak_decrease_source_row": first_postpeak_decrease,
                       "end_load_raw_y": str(y[-1]),
                       "peak_to_end_decline_fraction": str((full_peak - y[-1]) / full_peak),
                       "decline_metrics": decline_metrics(points, full_peak)},
        "fixed_window": {"bounds_mm": [str(window_start), str(window_end)],
                         "point_count": len(window), "source_rows": [window[0][0], window[-1][0]],
                         "end_load_raw_y": str(window[-1][2]),
                         "peak_in_window": str(max(p[2] for p in window)),
                         "global_peak_after_window": points[first_peak][1] > window_end,
                         "decline_metrics": decline_metrics(window, full_peak)},
        "damage_or_fracture_observation": "UNKNOWN; no DIC, crack or fracture record in allowed source evidence",
        "window_physical_status": "PROVISIONAL; pre-peak/no sustained load decline cannot prove undamaged material",
        "fe_residual_used": False,
        "formal_loss": None,
    }
    (out / "spt_source_window.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot([float(v) for v in x], [float(v) for v in y], label="SPT source numeric series")
    ax.axvspan(float(window_start), float(window_end), color="tab:blue", alpha=0.1, label="Frozen 0-1.2 mm window")
    ax.axvline(float(points[first_peak][1]), color="tab:orange", ls="--", label="Source global peak")
    ax.set_xlabel("Displacement (mm, XLSX label and Origin graph)")
    ax.set_ylabel("Load value (unit conflict: XLSX N; Origin graph mm)")
    ax.set_title("SPT source-only window diagnostic; damage status unknown")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "spt_source_window.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"point_count": len(points), "window_points": len(window),
                      "peak_after_window": report["fixed_window"]["global_peak_after_window"],
                      "window_negative_increments": report["fixed_window"]["decline_metrics"]["negative_increment_count"],
                      "force_unit_confirmed": False, "source_unchanged": report["source_unchanged"]}))


if __name__ == "__main__":
    main()
