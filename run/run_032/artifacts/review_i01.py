"""MAIN's independent, read-only I01 gate review before any I02 enqueue."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_032"
A = RUN / "artifacts"
P = A / "private"
ODB = P / "odb"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub


def now():
    return datetime.now().astimezone().isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def save_once(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def main():
    review_path = A / "main_i01_gate.json"
    assert not review_path.exists(), "Review already performed; do not redo the gate"
    session = read(P / "main_session.json")
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    main = session["identity"]
    review_id = session["review_task_id"]
    odb_id = session["odb_task_id"]
    assert hub.task(review_id)["execution_state"] == "CLAIMED"
    assert hub.task(review_id)["lease_session"] == main["session_id"]
    odb_task = hub.task(odb_id)
    assert odb_task and odb_task["execution_state"] == "COMPLETED"
    assert odb_task["evidence_state"] == "RECORDED"
    assert odb_task["lease_agent"] == "ODB:codex-local-01a15d5e-f6e8-7373-8991-ae275dfd3b40"
    result = read(ODB / "result.json")
    assert json.loads(odb_task["result"]) == result
    assert result["status"] == "ODB_COMPLETE_NUMERICAL_WARNING_MAIN_REVIEW_REQUIRED"
    audit = read(P / "execution_audit.json")
    auth = read(ROOT / "run/run_031/artifacts/authorization.json")
    batch = read(ROOT / "run/run_030/artifacts/prepared_batch.json")
    point = batch["points"][0]
    assert result["task_id"] == odb_id and result["point_id"] == "I01"
    assert result["job_name"] == point["job_name"] == audit["job_name"]
    assert result["queue_id"] == audit["queue_id"]
    assert result["project_id"] == auth["scope"]["project_id"]
    assert result["inp_sha256"] == point["inp_sha256"] == sha(ROOT / point["inp_path"])
    assert result["odb_sha256"] == audit["files"]["odb"]["sha256"]
    assert sha(ROOT / audit["files"]["odb"]["path"]) == result["odb_sha256"]
    assert result["configured_cpus"] == 14 and result["configured_gpus"] == 0
    assert result["datacheck_status"]["command_return_code"] == 0
    assert result["full_status"]["command_return_code"] == 0
    assert result["full_status"]["queue_status"] == "COMPLETED"
    assert result["full_status"]["odb_job_status"] == "JOB_STATUS_COMPLETED_SUCCESSFULLY"
    assert result["actual_runtime_s"] == audit["duration_sec"] == 210

    manifest = read(ODB / "manifest.json")
    assert manifest["task_id"] == odb_id and manifest["job_name"] == point["job_name"]
    for entry in manifest["files"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"]
        if Path(entry["path"]).name != "result.json":
            assert entry["path"] in result["artifact_hashes"]
            assert result["artifact_hashes"][entry["path"]] == entry["sha256"]
    assert len(manifest["files"]) == manifest["file_count"]
    assert sha(ODB / "result.json") == sha(ROOT / "run/run_032/artifacts/private/odb/result.json")

    binding = read(ROOT / "run/run_030/artifacts/loss_contract_binding.json")
    for path_key, hash_key in (("config_path", "config_sha256"),
                               ("target_path", "target_sha256"),
                               ("implementation_path", "implementation_sha256"),
                               ("loss_identity_path", "loss_identity_sha256")):
        assert sha(ROOT / binding[path_key]) == binding[hash_key]
    assert result["loss_binding_sha256"] == sha(ROOT / "run/run_030/artifacts/loss_contract_binding.json")
    assert result["loss_contract_sha256"] == binding["config_sha256"]
    assert result["loss_version"] == batch["loss_version"] == "run017-exploratory-fd-v1"

    with (ODB / "aligned_241.csv").open(newline="", encoding="utf-8-sig") as f:
        aligned = list(csv.DictReader(f))
    with (ROOT / binding["target_path"]).open(newline="", encoding="utf-8-sig") as f:
        source = list(csv.DictReader(f))
    assert len(source) == 339 and len(aligned) == 241
    assert result["loss_point_count"] == len(aligned)
    assert result["fd_window_coverage"]["covers_fixed_window"] is True
    assert result["fd_window_coverage"]["start_m"] <= 0
    assert result["fd_window_coverage"]["end_m"] >= 0.0012
    sq = 0.0
    for i, row in enumerate(aligned):
        x = float(row["displacement_m"])
        target = float(row["target_force_n"])
        fe = float(row["fe_interpolated_force_n"])
        residual = float(row["residual_fe_minus_target_n"])
        assert math.isfinite(x) and math.isfinite(target) and math.isfinite(fe)
        assert math.isclose(x, float(source[i]["displacement_m"]), abs_tol=1e-15)
        assert math.isclose(target, float(source[i]["force_n"]), abs_tol=1e-10)
        assert math.isclose(residual, fe - target, abs_tol=1e-9)
        assert 0 <= x <= 0.0012
        sq += residual * residual
    rmse = math.sqrt(sq / len(aligned))
    nrmse = rmse / 1428.9
    loss = nrmse * nrmse
    assert math.isclose(loss, result["loss_or_null"], rel_tol=1e-12)
    assert math.isclose(rmse, result["rmse_n_or_null"], rel_tol=1e-12)
    assert math.isclose(nrmse, result["nrmse_or_null"], rel_tol=1e-12)

    numerical = read(ODB / "numeric_review.json")
    diagnostics = read(ODB / "diagnostics.json")
    assert numerical["blocking_issues"] == result["numerical_blocking_issues"] == []
    assert diagnostics["identity_checks"] and all(diagnostics["identity_checks"].values())
    assert result["accepted_increments"] == 402
    assert result["rejected_attempts"] == result["cutback_increments"] == 0
    assert result["max_saved_peeq"] < 0.85 < result["material_table_max_plastic_strain"] == 0.9
    assert result["actual_runtime_s"] < 1200
    assert result["contact_transition_review"]["missing_contact_frames"] == 0
    assert result["local_fd_jump_review"]["negative_force_step_count"] == 0
    assert not result["warning_events_by_accepted_or_rejected"]["rejected"]
    accepted = result["warning_events_by_accepted_or_rejected"]["accepted"]
    assert len(accepted) == 1 and accepted[0]["class"] == "ZERO_MOMENT"
    dat = result["warning_events_by_accepted_or_rejected"]["dat"]
    assert len(dat) == 1 and "PATH BASED TRACKING" in dat[0]["text"]
    dat_text = (ROOT / audit["files"]["dat"]["path"]).read_text(errors="replace")
    assert "PATH BASED TRACKING CANNOT BE USED WITH ANALYTICAL RIGID" in dat_text
    assert "STATE BASED TRACKING ALGORITHM WILL BE USED" in dat_text
    assert not any("NEGATIVE_EIGEN" in x or "DISTORT" in x or "LARGE_STRAIN" in x
                   for x in result["numerical_review_warnings"])
    # The observed accepted warning is the already known baseline class. The
    # predeclared protocol calls for MAIN review, not automatic stop.
    warnings = ["ACCEPTED_ZERO_MOMENT_REVIEWED_BASELINE_LIKE",
                "DAT_CONTACT_TRACKING_STATE_BASED_FALLBACK",
                "HISTORICAL_RUNNER_PROCESS_EVIDENCE_UNCONFIRMED"]
    decision = {"at": now(), "status": "PASS_I01_EXPLORATORY_GATE_WITH_WARNINGS",
                "gate_scope": "run030 pilot protocol numerical eligibility for next frozen Job; not physical validation",
                "review_task_id": review_id, "odb_task_id": odb_id,
                "real_odb_agent": odb_task["lease_agent"],
                "queue_id": result["queue_id"], "job_name": result["job_name"],
                "inp_sha256": result["inp_sha256"], "odb_sha256": result["odb_sha256"],
                "loss_version": result["loss_version"], "loss": loss,
                "rmse_n": rmse, "nrmse": nrmse, "loss_status": "EXPLORATORY_PROVISIONAL",
                "accepted_increments": result["accepted_increments"],
                "rejected_attempts": result["rejected_attempts"],
                "cutback_increments": result["cutback_increments"],
                "max_saved_peeq": result["max_saved_peeq"],
                "material_table_pmax": result["material_table_max_plastic_strain"],
                "runtime_s": result["actual_runtime_s"],
                "warnings": warnings,
                "blocking_issues": [], "I02_enqueue_gate_open": True,
                "I02_solver_start": "USER_GUI_ONLY",
                "historical_process_evidence_gap_retained": True,
                "sealed_tensile_accessed": False}
    save_once(review_path, decision)
    messages = hub.poll_messages(main)
    assert any(m["task_id"] == odb_id and m["sender"] == odb_task["lease_agent"]
               for m in messages), "No real ODB inbox message received"
    save_once(P / "main_inbox_receipt.json", {"at": now(), "odb_task_id": odb_id,
                                                 "received_message_ids": [m["message_id"] for m in messages if m["task_id"] == odb_id]})
    hub.artifact(review_id, main["agent_id"], review_path,
                 {"run": "run_032", "scope": "I01 frozen exploratory gate", "odb_task_id": odb_id}, version="run032-v1")
    hub.artifact(review_id, main["agent_id"], ODB / "result.json",
                 {"run": "run_032", "producer": odb_task["lease_agent"]}, version="run032-v1")
    hub.message(review_id, main["agent_id"], "MAIN", decision, "run032-i01-main-gate-v1")
    hub.finish(session["review_lease"], decision, evidence_state="RECORDED",
               science_state="WARNING")
    assert hub.verify_chain()
    print(json.dumps({"status": decision["status"], "loss": loss,
                      "I02_gate_open": True, "review_task_id": review_id}, ensure_ascii=False))


if __name__ == "__main__":
    main()
