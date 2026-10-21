"""Analyze extracted run_014 ODB histories and compare with historical model data."""
import csv
import datetime as dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
JOB = ROOT / "run/run_014/artifacts/solver/SPIO_R014_Q200_N010"
HIST = ROOT / "run/run_005/artifacts/punch_force_displacement.csv"
EXTRACT = OUT / "private/extraction_attempt02.json"

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def save_json(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    extract = json.loads(EXTRACT.read_text(encoding="utf-8"))
    assert extract["status"] == "PASS" and extract["odb"]["isReadOnly"] is True
    assert extract["diagnostic_data"]["jobStatus"] == "JOB_STATUS_COMPLETED_SUCCESSFULLY"
    assert extract["source_sha256_before"] == extract["source_sha256_after"]
    step_name = "Step_Punch_Displacement"
    step = extract["steps"][step_name]
    rp = step["history_regions"]["Node ASM_SPT.1"]
    u = np.asarray(rp["outputs"]["U2"]["data"], dtype=float)
    rf = np.asarray(rp["outputs"]["RF2"]["data"], dtype=float)
    frames = step["frame_diagnostics"]
    assert len(u) == len(rf) == len(frames) == step["frame_count"]
    assert np.array_equal(u[:, 0], rf[:, 0])
    assert np.allclose(u[:, 0], [f["time"] for f in frames], rtol=0, atol=1e-7)
    field_u_error = max(abs(f["rp_field"]["U"][1] - x[1]) for f, x in zip(frames, u))
    field_rf_error = max(abs(f["rp_field"]["RF"][1] - x[1]) for f, x in zip(frames, rf))
    assert field_u_error < 1e-7 and field_rf_error < 1e-4
    d = -u[:, 1]
    force = -rf[:, 1]
    assert np.all(np.diff(d) > 0) and np.all(force >= -1e-10)
    with (OUT / "punch_history_raw.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["step", "step_time_model", "U2_raw_model_length", "RF2_raw_model_force"])
        writer.writerows((step_name, float(t), float(uv), float(rv)) for t, uv, rv in zip(u[:, 0], u[:, 1], rf[:, 1]))
    with (OUT / "punch_force_displacement.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["step", "step_time_model", "displacement_model_length", "force_model_force"])
        writer.writerows((step_name, float(t), float(x), float(y)) for t, x, y in zip(u[:, 0], d, force))

    with HIST.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    old_d = np.asarray([float(x["displacement_model_length"]) for x in rows])
    old_f = np.asarray([float(x["force_model_force"]) for x in rows])
    assert np.all(np.diff(old_d) > 0)
    assert abs(d[0] - old_d[0]) < 1e-12 and abs(d[-1] - old_d[-1]) < 1e-9
    old_interpolated = np.interp(d, old_d, old_f)
    delta = force - old_interpolated
    with (OUT / "historical_comparison.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["displacement_model_length", "new_force_model", "historical_force_linear_interp_model", "new_minus_historical_model"])
        writer.writerows((float(x), float(y), float(z), float(w)) for x, y, z, w in zip(d, force, old_interpolated, delta))

    energies = step["history_regions"]["Assembly ASSEMBLY"]["outputs"]
    energy_final = {key: float(info["data"][-1][1]) for key, info in energies.items()}
    energy_times_equal = all(np.array_equal(np.asarray(info["data"])[:, 0], u[:, 0]) for info in energies.values())
    rp_work = float(np.trapezoid(force, d))
    peeq_saved_max = max(f["peeq_max"] for f in frames if f["peeq_max"] is not None)
    peeq_final = frames[-1]["peeq_max"]
    msg_lines = (JOB / "SPIO_R014_Q200_N010.msg").read_text(encoding="utf-8", errors="replace").splitlines()
    sta_lines = (JOB / "SPIO_R014_Q200_N010.sta").read_text(encoding="utf-8", errors="replace").splitlines()
    log_text = (JOB / "SPIO_R014_Q200_N010.log").read_text(encoding="utf-8", errors="replace")
    attempts = []
    for line in sta_lines:
        parts = line.split()
        if len(parts) >= 9 and parts[0].isdigit() and parts[1].isdigit():
            attempts.append({"step": int(parts[0]), "increment": int(parts[1]), "attempt_token": parts[2],
                             "unsuccessful": "U" in parts[2], "step_time": float(parts[7]), "dt": float(parts[8])})
    current_attempt = None
    warning_events = []
    for index, line in enumerate(msg_lines):
        if re.search(r"INCREMENT\s+\d+\s+STARTS", line):
            match = re.search(r"INCREMENT\s+(\d+)\s+STARTS\.\s+ATTEMPT NUMBER\s+(\d+)", line)
            if match:
                current_attempt = {"increment": int(match.group(1)), "attempt": int(match.group(2))}
        if "***WARNING:" in line:
            event = {"line": index + 1, "text": line.strip(), "attempt": current_attempt}
            if current_attempt:
                matched = [a for a in attempts if a["increment"] == current_attempt["increment"] and int(a["attempt_token"].rstrip("U")) == current_attempt["attempt"]]
                event["sta_unsuccessful"] = matched[0]["unsuccessful"] if len(matched) == 1 else None
            warning_events.append(event)
    patterns = {
        "negative_eigenvalue_headers": "***WARNING: THE SYSTEM MATRIX",
        "large_strain_increment_headers": "***WARNING: THE STRAIN INCREMENT HAS EXCEEDED",
        "plasticity_not_attempted_headers": "***WARNING: THE STRAIN INCREMENT IS SO LARGE",
        "excessive_distortion_headers": "***WARNING: EXCESSIVE DISTORTION",
        "zero_moment_headers": "***WARNING: THERE IS ZERO MOMENT",
        "element_distortion_lines": "IS DISTORTING EXCESSIVELY",
        "all_msg_warning_headers": "***WARNING:",
        "msg_error_headers": "***ERROR",
    }
    counts = {key: sum(pattern in line for line in msg_lines) for key, pattern in patterns.items()}
    flagged = [event for event in warning_events if event["text"].startswith((patterns["negative_eigenvalue_headers"], patterns["excessive_distortion_headers"]))]
    old_peak = float(old_f.max())
    new_peak = float(force.max())
    comparison = {
        "reference": "Historical Sanity Job-1 model F-D, run_005; not experimental data",
        "historical_csv": str(HIST.relative_to(ROOT)).replace("\\", "/"),
        "historical_csv_sha256": sha(HIST),
        "historical_odb": "CAE/Models/Sanity/Job-1.odb",
        "historical_odb_sha256": sha(ROOT / "CAE/Models/Sanity/Job-1.odb"),
        "new_odb_sha256": extract["source_sha256_after"],
        "method": "Linear interpolation of historical model force onto each new model displacement; common displacement endpoints; no smoothing, baseline shift, abs or 2*pi; descriptive model-to-model difference only.",
        "new_samples": len(d), "historical_samples": len(old_d),
        "new_end_force": float(force[-1]), "historical_end_force": float(old_f[-1]),
        "end_force_new_minus_historical": float(force[-1] - old_f[-1]),
        "new_peak_force": new_peak, "historical_peak_force": old_peak,
        "peak_force_new_minus_historical": new_peak - old_peak,
        "max_abs_curve_difference": float(np.max(np.abs(delta))),
        "max_abs_curve_difference_displacement": float(d[np.argmax(np.abs(delta))]),
        "rms_curve_difference": float(np.sqrt(np.mean(delta**2))),
        "new_area_force_displacement": rp_work,
        "historical_area_force_displacement": float(np.trapezoid(old_f, old_d)),
    }
    summary = {
        "observed_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        "task_id": "35b07ba1-22ad-48a7-b859-2d99199ed419",
        "execution_status": "COMPLETED_WITH_WARNINGS",
        "extraction_status": "PASS",
        "science_status": "NOT_EVALUATED",
        "job_status_odb": extract["diagnostic_data"],
        "sample_count": len(d), "frame_count": len(frames), "time_range_model": [float(u[0, 0]), float(u[-1, 0])],
        "raw_U2_end": float(u[-1, 1]), "raw_RF2_end": float(rf[-1, 1]),
        "positive_displacement_end": float(d[-1]), "positive_force_end": float(force[-1]),
        "sign_rule": "d=-U2, F=-RF2; no abs, no baseline shift, no 2*pi",
        "units": "Unverified model length/force/time units",
        "history_field_U2_max_abs_error": field_u_error,
        "history_field_RF2_max_abs_error": field_rf_error,
        "history_time_axes_identical": True,
        "rp_identity_evidence": "Candidate INP ASM_SPT.set_punch_rp, rigid-body ref node, and ODB Node ASM_SPT.1; RP field output matches history",
        "peeq": {"quantity": "PEEQ at saved-frame field values; not PE11 or total strain",
                 "final_max": peeq_final, "all_saved_frames_max": peeq_saved_max,
                 "candidate_table_pmax": 0.9, "pmax_minus_observed_max": 0.9 - peeq_saved_max,
                 "within_candidate_table_range": peeq_saved_max <= 0.9,
                 "available_each_frame": all(f["peeq_count"] is not None for f in frames),
                 "final_value_count": frames[-1]["peeq_count"]},
        "energy": {"final": energy_final, "time_axis_matches_rp": energy_times_equal,
                   "integral_F_dd_trapezoid": rp_work,
                   "integral_vs_ALLWK_abs_difference": abs(rp_work - energy_final["ALLWK"]),
                   "ETOTAL_max_abs": max(abs(float(x[1])) for x in energies["ETOTAL"]["data"]),
                   "full_contact_energy_balance": "NOT_VERIFIED: contact-specific terms not available"},
        "convergence": {"sta_completed": "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in "\n".join(sta_lines),
                        "log_completed": "Abaqus JOB SPIO_R014_Q200_N010 COMPLETED" in log_text,
                        "accepted_increments": sum(not x["unsuccessful"] for x in attempts),
                        "rejected_attempts": sum(x["unsuccessful"] for x in attempts),
                        "msg_warning_counts": counts,
                        "negative_eigenvalue_or_distortion_events": flagged,
                        "note": "STA U attempts are rejected trial increments; warning context does not prove accepted final mesh quality."},
        "comparison": comparison,
        "source_sha256": {"extraction_json": sha(EXTRACT), "new_odb": extract["source_sha256_after"],
                          "new_inp": sha(ROOT / "run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp"),
                          "historical_csv": sha(HIST)},
        "limitations": ["Historical Sanity curve is a model comparator, not experimental Loss.",
                        "Stress/length/force unit declaration remains unverified.",
                        "No mesh or increment sensitivity study; material physical validity not established.",
                        "Runner Full process aggregation retained UNCONFIRMED for transient PID14320; current read-safety evidence supports read-only open."],
    }
    save_json("diagnostics.json", summary)
    save_json("warning_events.json", {"warning_events": warning_events, "counts": counts, "sta_attempts": attempts})
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.grid": True, "grid.alpha": 0.2})
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(d, force, label="run_014 candidate solve", linewidth=2)
    ax.plot(old_d, old_f, label="run_005 historical Sanity", linewidth=1.5, alpha=0.85)
    ax.set_xlabel("Punch displacement (model length units; -U2)")
    ax.set_ylabel("Punch force (model force units; -RF2)")
    ax.set_title("Punch force–displacement: two model results")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "force_displacement_comparison.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"samples": len(d), "end_force": float(force[-1]), "peeq_max": peeq_saved_max,
                      "comparison": comparison, "warning_counts": counts,
                      "rejected_attempts": summary["convergence"]["rejected_attempts"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
