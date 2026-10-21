"""Check run_014 ODB deliverables and write their hash manifest/result."""
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
NAMES = [
    "preflight_read.py", "preflight_read.json", "extract_readonly.py",
    "analyze_results.py", "punch_history_raw.csv", "punch_force_displacement.csv",
    "historical_comparison.csv", "energy_history.csv", "peeq_saved_frames.csv",
    "diagnostics.json", "warning_events.json", "force_displacement_comparison.png",
    "report.md", "private/extraction_attempt01.json", "private/extraction_attempt02.json",
]

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    report = json.loads((OUT / "diagnostics.json").read_text(encoding="utf-8"))
    preflight = json.loads((OUT / "preflight_read.json").read_text(encoding="utf-8"))
    extract = json.loads((OUT / "private/extraction_attempt02.json").read_text(encoding="utf-8"))
    assert preflight["safe_to_open"] and all(preflight["checks"].values())
    assert extract["status"] == "PASS" and extract["odb"]["isReadOnly"] is True
    assert extract["source_sha256_before"] == extract["source_sha256_after"] == preflight["odb_after"]["sha256"]
    assert report["extraction_status"] == "PASS" and report["science_status"] == "NOT_EVALUATED"
    for name in ("punch_history_raw.csv", "punch_force_displacement.csv", "energy_history.csv", "peeq_saved_frames.csv"):
        with (OUT / name).open(newline="", encoding="utf-8") as stream:
            assert len(list(csv.DictReader(stream))) == report["sample_count"]
    assert (OUT / "force_displacement_comparison.png").stat().st_size > 10000
    source_odb = ROOT / "run/run_014/artifacts/solver/SPIO_R014_Q200_N010/SPIO_R014_Q200_N010.odb"
    assert sha(source_odb) == extract["source_sha256_after"]
    result = {
        "task_id": report["task_id"], "queue_id": preflight["queue_id"],
        "job_name": preflight["job_name"], "project_id": preflight["project_id"],
        "execution_status": report["execution_status"], "extraction_status": "PASS",
        "evidence_status": "RECORDED", "science_status": "NOT_EVALUATED",
        "odb_sha256": extract["source_sha256_after"],
        "inp_sha256": report["source_sha256"]["new_inp"],
        "historical_csv_sha256": report["source_sha256"]["historical_csv"],
        "sample_count": report["sample_count"], "end_force_model": report["positive_force_end"],
        "peak_force_model": report["comparison"]["new_peak_force"],
        "end_force_difference_new_minus_historical_model": report["comparison"]["end_force_new_minus_historical"],
        "max_abs_curve_difference_model": report["comparison"]["max_abs_curve_difference"],
        "rms_curve_difference_model": report["comparison"]["rms_curve_difference"],
        "peeq_max_saved_frames": report["peeq"]["all_saved_frames_max"],
        "peeq_within_candidate_pmax_0p9": report["peeq"]["within_candidate_table_range"],
        "accepted_increments": report["convergence"]["accepted_increments"],
        "rejected_attempts": report["convergence"]["rejected_attempts"],
        "negative_eigenvalue_warning_headers": report["convergence"]["msg_warning_counts"]["negative_eigenvalue_headers"],
        "excessive_distortion_warning_headers": report["convergence"]["msg_warning_counts"]["excessive_distortion_headers"],
        "runner_full_process_aggregation": preflight["runner_warning_preserved"],
        "experimental_loss": None,
        "report": "run/run_014/artifacts/odb/report.md",
        "diagnostics": "run/run_014/artifacts/odb/diagnostics.json",
        "limitations": report["limitations"],
    }
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    names = NAMES + ["finalize_odb.py", "result.json"]
    manifest = {
        "created_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        "task_id": result["task_id"],
        "files": [{"path": str((OUT / name).relative_to(ROOT)).replace("\\", "/"),
                   "sha256": sha(OUT / name), "size": (OUT / name).stat().st_size,
                   "private": name.startswith("private/")} for name in names],
        "source_odb_sha256": result["odb_sha256"],
        "source_inp_sha256": result["inp_sha256"],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"validated": True, "file_count": len(names), "result_sha256": sha(OUT / "result.json"),
                      "manifest_sha256": sha(OUT / "manifest.json")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
