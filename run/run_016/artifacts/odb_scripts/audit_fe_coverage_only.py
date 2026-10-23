"""Read existing FE displacement coverage and warnings without a residual or Loss."""
import argparse
import csv
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
    ap = argparse.ArgumentParser()
    for name in ("workspace", "fe-csv", "diagnostics", "inventory", "criteria", "output"):
        ap.add_argument("--" + name, required=True)
    args = ap.parse_args()
    root = Path(args.workspace).resolve()
    fe_path = Path(args.fe_csv).resolve()
    diag_path = Path(args.diagnostics).resolve()
    inventory_path = Path(args.inventory).resolve()
    criteria_path = Path(args.criteria).resolve()
    out = Path(args.output).resolve()
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    expected = {v["path"].replace("\\", "/"): v["sha256"] for v in inventory["files"]}
    if sha(fe_path) != expected[fe_path.relative_to(root).as_posix()]:
        raise ValueError("FE CSV hash mismatch")
    criteria = json.loads(criteria_path.read_text(encoding="utf-8"))
    with fe_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    diagnostics = json.loads(diag_path.read_text(encoding="utf-8"))
    x = [float(row["displacement_model_length"]) for row in rows]
    if len(rows) != diagnostics["sample_count"] or not all(b > a for a, b in zip(x, x[1:])):
        raise ValueError("FE frame count or displacement ordering mismatch")
    end_mm = x[-1] * 1000.0
    bound_mm = float(criteria["candidate_window_displacement_mm_inclusive"][1])
    result = {
        "status": "EXISTING_FE_COVERAGE_REVIEW_ONLY",
        "fe_csv_relative_path": fe_path.relative_to(root).as_posix(),
        "fe_csv_sha256": sha(fe_path),
        "diagnostics_relative_path": diag_path.relative_to(root).as_posix(),
        "diagnostics_sha256": sha(diag_path),
        "prefe_criteria_relative_path": criteria_path.relative_to(root).as_posix(),
        "prefe_criteria_sha256": sha(criteria_path),
        "sample_count": len(rows),
        "model_displacement_min": min(x),
        "model_displacement_max": max(x),
        "displacement_strictly_increasing": True,
        "current_user_unit_declaration": "FE N-m-Pa in current study; historical run_014 physical units were unverified",
        "conditional_end_displacement_mm": end_mm,
        "fixed_window_end_mm": bound_mm,
        "endpoint_gap_mm": end_mm - bound_mm,
        "coverage_within_1e_minus_6_mm": end_mm >= bound_mm - 1e-6,
        "odb_job_status": diagnostics["job_status_odb"],
        "run014_execution_status": diagnostics["execution_status"],
        "run014_science_status": diagnostics["science_status"],
        "peeq_saved_frames_max": diagnostics["peeq"]["all_saved_frames_max"],
        "peeq_is_damage_measure": False,
        "rejected_attempts": diagnostics["convergence"]["rejected_attempts"],
        "negative_eigenvalue_warning_headers": diagnostics["convergence"]["msg_warning_counts"]["negative_eigenvalue_headers"],
        "excessive_distortion_warning_headers": diagnostics["convergence"]["msg_warning_counts"]["excessive_distortion_headers"],
        "physical_damage_absence_proven": False,
        "model_numerical_sufficiency_proven": False,
        "force_values_used_for_residual": False,
        "residual_computed": False,
        "formal_loss": None,
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"samples": len(rows), "end_mm": end_mm,
                      "covered": result["coverage_within_1e_minus_6_mm"],
                      "residual_computed": False}))


if __name__ == "__main__":
    main()
