"""MAIN independently validates 20 frozen INPs and public API previews."""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_033"
A = RUN / "artifacts"
P = A / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
RT = PROJECT / "runtime"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from inverse.hollomon import generate_hollomon_table
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from abqjobpilot.recovery_assessment import assess_runtime
from abqjobpilot.runtime_coordination import runner_ownership_state
from agenthub_sp_invopt.hub import Hub

TERMINAL = {"COMPLETED_OK", "COMPLETED_WITH_WARNINGS", "FAILED_FATAL", "FAILED_NUMERICAL",
            "FAILED_INPUT", "FAILED_LICENSE", "DATACHECK_FAILED",
            "DATACHECK_FAILED_INVALID_GPU_OPTION", "SKIPPED", "CANCELLED"}


def now():
    return datetime.now().astimezone().isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def save_once(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def split(raw: bytes, marker: bytes):
    start = raw.index(marker)
    end = raw.index(b"** \n** INTERACTION PROPERTIES", start)
    block = raw[start:end]
    plastic = block.index(b"*Plastic\n") + len(b"*Plastic\n")
    rows = []
    for line in block[plastic:].splitlines():
        if line.lstrip().startswith(b"**"):
            break
        if line.strip():
            rows.append(tuple(float(piece.strip()) for piece in line.split(b",")))
    return raw[:start] + raw[end:], rows


def process_conflicts():
    cmd = "Get-CimInstance Win32_Process -ErrorAction Stop | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress"
    raw = json.loads(subprocess.check_output(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd], encoding="utf-8", errors="replace"))
    procs = raw if isinstance(raw, list) else [raw]
    return [p for p in procs if re.search(r"^(standard|explicit|pre|package|abq.*|smap.*)\.exe$", p.get("Name") or "", re.I)
            or ((p.get("Name") or "").lower() in ("python.exe", "pythonw.exe", "cmd.exe")
                and "spio_r033_" in (p.get("CommandLine") or "").lower())]


def main():
    assert not (A / "prepared_batch.json").exists()
    assert not (P / "main_preflight.json").exists()
    doe_file = A / "doe_design.json"
    doe = read(doe_file)
    prior_file = ROOT / "run/run_030/artifacts/prepared_batch.json"
    prior = read(prior_file)
    manifest_file = A / "cae_candidate_manifest.json"
    manifest = read(manifest_file)
    cae_result = read(A / "cae_result.json")
    auth = read(A / "authorization_scope.json")
    session = read(P / "main_session.json")
    assert auth["doe_design_sha256"] == sha(doe_file)
    assert doe["run030_batch_sha256"] == sha(prior_file)
    assert manifest["design_sha256"] == sha(doe_file)
    assert cae_result["manifest_sha256"] == sha(manifest_file)
    assert len(manifest["points"]) == 14 and len(doe["new_points"]) == 14
    assert len(doe["existing_frozen"]) == 6 and len(doe["batch_order"]) == 20
    assert manifest["task_id"] == session["cae_task_id"] == cae_result["task_id"]
    assert cae_result["agent_id"].startswith("CAE:")
    assert cae_result["candidate_count"] == 14
    assert cae_result["execution_status"] == "COMPLETED_GENERATION_ONLY"
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=7200)
    cae_task = hub.task(session["cae_task_id"])
    assert cae_task["execution_state"] == "COMPLETED" and cae_task["evidence_state"] == "RECORDED"
    assert cae_task["lease_agent"] == cae_result["agent_id"]
    assert json.loads(cae_task["result"]) == cae_result
    assert hub.task(session["review_task_id"])["execution_state"] == "PENDING"

    model = read(ROOT / "run/run_030/artifacts/model_contract.json")
    loss = read(ROOT / "run/run_030/artifacts/loss_contract_binding.json")
    source = ROOT / model["source_inp"]
    assert sha(source) == model["source_inp_sha256"] == manifest["source_sha256"]
    source_nonmaterial, _ = split(source.read_bytes(), b"** CANDIDATE ONLY:")
    nonmaterial_sha = hashlib.sha256(source_nonmaterial).hexdigest()
    assert manifest["nonmaterial_sha256"] == nonmaterial_sha
    assert sha(ROOT / "inverse/hollomon.py") == manifest["generator_sha256"]
    assert sha(ROOT / loss["target_path"]) == loss["target_sha256"]
    assert sha(ROOT / loss["config_path"]) == loss["config_sha256"]
    assert sha(ROOT / loss["implementation_path"]) == loss["implementation_sha256"]
    assert prior["numeric_version"] == doe["numeric_version"] == auth["numeric_version"]
    assert prior["loss_version"] == doe["loss_version"] == auth["loss_version"]

    m_by_id = {p["point_id"]: p for p in manifest["points"]}
    p_by_id = {p["point_id"]: p for p in prior["points"][2:]}
    d_by_id = {p["point_id"]: p for p in doe["new_points"]}
    assert len(m_by_id) == 14 and len(p_by_id) == 6 and len(d_by_id) == 14
    assert set(doe["batch_order"]) == set(p_by_id) | set(d_by_id)
    points = []
    for point_id in doe["batch_order"]:
        if point_id in p_by_id:
            p = p_by_id[point_id]
            m = next(x for x in read(ROOT / "run/run_030/artifacts/cae_candidate_manifest.json")["points"]
                     if x["point_id"] == point_id)
            candidate_marker = b"** RUN_030 POINT"
            origin = "run030_frozen_reuse"
            expected_sha = p["inp_sha256"]
            expected_params_sha = p["parameters_sha256"]
        else:
            p = d_by_id[point_id]
            m = m_by_id[point_id]
            candidate_marker = b"** RUN_033 POINT"
            origin = "run033_new_doe"
            expected_sha = m["sha256"]
            expected_params_sha = m["parameters_sha256"]
            assert all(m[k] == p[k] for k in ("job_name", "inp_path", "working_dir", "sigma_y_mpa", "n", "x", "y"))
        assert len(p["job_name"]) <= 80 and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", p["job_name"])
        inp = ROOT / p["inp_path"]
        params_path = ROOT / p["parameters_path"]
        work = ROOT / p["working_dir"]
        assert inp.is_file() and inp.stem == p["job_name"] and params_path.is_file()
        assert work.is_dir() and not any(work.iterdir())
        assert sha(inp) == expected_sha and sha(params_path) == expected_params_sha
        params = read(params_path)
        assert params["sigma_y_mpa"] == p["sigma_y_mpa"] and params["n"] == p["n"]
        assert params["inp_sha256"] == expected_sha
        raw = inp.read_bytes()
        nonmaterial, rows = split(raw, candidate_marker)
        assert nonmaterial == source_nonmaterial
        assert hashlib.sha256(nonmaterial).hexdigest() == nonmaterial_sha
        assert raw.count(b"*Static\n0.001, 1., 1e-12, 0.0025") == 1
        assert b"U2" in raw and b"RF2" in raw
        assert not any(line.lower().startswith((b"*include", b"*import", b"*restart, read"))
                       for line in raw.splitlines())
        table = generate_hollomon_table(p["sigma_y_mpa"], p["n"],
                                        max_plastic_strain=0.9, relative_tolerance=0.001)
        assert len(rows) == len(table.rows) == m["material_rows"]
        assert all(math.isclose(a, b, rel_tol=1e-15, abs_tol=1e-18)
                   for row, generated in zip(rows, table.rows) for a, b in zip(row, generated))
        assert rows[0][1] == 0 and rows[-1][1] == 0.9
        assert table.conservative_relative_error_bound <= 0.001
        points.append({"point_id": point_id, "origin": origin,
                       "region": p["region"], "x": p["x"], "y": p["y"],
                       "sigma_y_mpa": p["sigma_y_mpa"], "n": p["n"],
                       "job_name": p["job_name"], "inp_path": p["inp_path"],
                       "inp_sha256": expected_sha,
                       "parameters_path": p["parameters_path"],
                       "parameters_sha256": expected_params_sha,
                       "working_dir": p["working_dir"],
                       "expected_odb": p["expected_odb"],
                       "material_rows": len(rows),
                       "nonmaterial_sha256": nonmaterial_sha})
    assert len(points) == len({p["job_name"] for p in points}) == 20
    assert len({(p["sigma_y_mpa"], p["n"]) for p in points}) == 20
    assert len({p["working_dir"] for p in points}) == 20
    assert len({p["inp_sha256"] for p in points}) == 20

    api = AbqJobPilotClient()
    caps = api.capabilities()
    assert caps["application_version"] == "0.2.2"
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert settings["status"] == "PERSISTED" and settings["persisted"] is True
    assert not settings["defaulted_fields"] and settings["project_id"] == PID
    assert Path(settings["project_path"]).resolve() == PROJECT.resolve()
    assert read(PROJECT / "project.json")["project_id"] == PID
    stored = settings["settings"]
    assert stored == read(RT / "settings.json")
    expected = {"abaqus_cmd": r"D:\ABAQUS2024\Commands\abq2024.bat",
                "default_cpus": 14, "default_gpus": 0, "use_gpu": False,
                "run_datacheck": True, "run_full": True}
    assert all(stored[k] == v for k, v in expected.items())
    assert Path(stored["abaqus_cmd"]).is_file()
    runtime = assess_runtime(RT, project_db=PROJECT / "project.db")
    owner = runner_ownership_state(RT)
    assert runtime["status"] == "CLEAN" and runtime["live_phase"] == "IDLE"
    assert owner["state"] == "ABSENT" and not runtime["lock_files"]
    assert not runtime["errors"] and not runtime["running_queue_ids"]
    assert not process_conflicts()
    scoped = api.for_project(project_id=PID)
    protected = [PROJECT / "project.json", PROJECT / "project.db",
                 RT / "settings.json", RT / "queue.json", RT / "live_status.json"]
    before = {str(p): sha(p) if p.is_file() else None for p in protected}
    q_before = scoped.list_jobs()
    h_before = api.list_project_jobs(project_id=PID).to_dict()
    assert q_before["status"] == h_before["status"] == "OK"
    assert not q_before["errors"] and not h_before["errors"]
    assert all(j.get("raw_status") in TERMINAL for j in q_before["jobs"])
    existing = {j["job_name"] for j in q_before["jobs"]} | {j["job_name"] for j in h_before["jobs"]}
    assert not existing.intersection(p["job_name"] for p in points)
    previews = []
    for p in points:
        req = JobRequest(inp_path=str(ROOT / p["inp_path"]), job_name=p["job_name"],
                         working_dir=str(ROOT / p["working_dir"]), cpus=14, gpus=0,
                         run_datacheck=True, run_full=True,
                         submission_mode="preview_only", allow_solver_submit=False,
                         batch="run033_twenty_doe_preview", strategy="authorized_serial_batch",
                         metadata={"run": "run_033", "point_id": p["point_id"],
                                   "project_id": PID, "inp_sha256": p["inp_sha256"],
                                   "automatic_retries": 0})
        pre = scoped.preflight(req).to_dict()
        dry = scoped.enqueue(req, dry_run=True).to_dict()
        assert pre["status"] == "PREVIEW_READY" and not pre["errors"]
        assert dry["status"] == "DRY_RUN_READY" and not dry["errors"]
        assert dry["job_id"] is None
        assert not any(dry[k] for k in ("queue_file_mutated", "solver_started", "runner_started", "forbidden_mutations_detected"))
        assert Path(pre["expected_odb_path"]).resolve() == (ROOT / p["expected_odb"]).resolve()
        assert sha(ROOT / p["inp_path"]) == p["inp_sha256"]
        assert not any((ROOT / p["working_dir"]).iterdir())
        previews.append({"point_id": p["point_id"], "job_name": p["job_name"],
                         "inp_sha256": p["inp_sha256"], "preflight": pre,
                         "dry_run": dry})
    after = {str(p): sha(p) if p.is_file() else None for p in protected}
    assert before == after
    assert q_before == scoped.list_jobs()
    assert h_before == api.list_project_jobs(project_id=PID).to_dict()

    prepared = {"version": "run033-twenty-input-batch-v1", "frozen_at": now(),
                "status": "ALL_PREVIEWS_PASS_QUEUE_PENDING", "project_id": PID,
                "project_path": str(PROJECT),
                "doe_design_sha256": sha(doe_file),
                "authorization_scope_sha256": sha(A / "authorization_scope.json"),
                "cae_task_id": session["cae_task_id"],
                "cae_manifest_sha256": sha(manifest_file),
                "numeric_version": prior["numeric_version"],
                "loss_version": prior["loss_version"],
                "cpus": 14, "gpus": 0, "run_datacheck": True,
                "run_full": True, "automatic_retries": 0,
                "solver_start": "USER_GUI_ONLY",
                "batch_order": doe["batch_order"], "points": points,
                "new_enqueues": 0, "new_solver_starts": 0}
    save_once(A / "prepared_batch.json", prepared)
    audit = {"at": now(), "status": "PASS_ALL_TWENTY_PREVIEWS",
             "cae_real_session": cae_result["session_id"],
             "cae_task_id": session["cae_task_id"],
             "project_settings_status": settings["status"],
             "abqjobpilot_version": caps["application_version"],
             "runner": runtime, "owner": owner,
             "source_sha256": sha(source), "nonmaterial_sha256": nonmaterial_sha,
             "doe_design_sha256": sha(doe_file),
             "loss_target_sha256": loss["target_sha256"],
             "all_20_input_sha256": {p["job_name"]: p["inp_sha256"] for p in points},
             "previews": previews,
             "protected_hashes_before": before, "protected_hashes_after": after,
             "queue_unchanged": True, "history_unchanged": True,
             "new_queue_jobs": 0, "solver_started": False,
             "datacheck_started": False,
             "preview_limit": "Public preflight/dry-run cannot prove future convergence or physical validity"}
    save_once(P / "main_preflight.json", audit)
    review = session["review_task_id"]
    lease = hub.claim(review, session["identity"], "run033-main-review-twenty-claim-v1")
    save_once(P / "main_review_lease.json", lease)
    messages = hub.poll_messages(session["identity"])
    assert any(m["task_id"] == session["cae_task_id"] and m["sender"] == cae_result["agent_id"]
               for m in messages), "No real CAE inbox message received"
    save_once(P / "main_cae_inbox_receipt.json", {"at": now(),
                                                  "message_ids": [m["message_id"] for m in messages if m["task_id"] == session["cae_task_id"]]})
    for path in (manifest_file, A / "cae_result.json", A / "prepared_batch.json", P / "main_preflight.json"):
        hub.artifact(review, session["identity"]["agent_id"], path,
                     {"run": "run_033", "scope": "all 20 static inputs and public previews"}, version="run033-v1")
    result = {"status": "PASS_ALL_TWENTY_PREVIEWS",
              "prepared_batch_sha256": sha(A / "prepared_batch.json"),
              "cae_task_id": session["cae_task_id"],
              "input_count": 20, "preflight_passed": 20, "dry_run_passed": 20,
              "new_enqueues": 0, "solver_starts": 0,
              "all_workdirs_empty": True, "all_input_hashes_verified": True,
              "queue_unchanged": True, "science_state": "NOT_EVALUATED"}
    save_once(A / "main_review_result.json", result)
    hub.artifact(review, session["identity"]["agent_id"], A / "main_review_result.json",
                 {"run": "run_033", "scope": "MAIN review decision"}, version="run033-v1")
    hub.message(review, session["identity"]["agent_id"], "MAIN", result,
                "run033-all-twenty-preview-result-v1")
    hub.finish(lease, result, evidence_state="RECORDED", science_state="NOT_EVALUATED")
    assert hub.verify_chain()
    print(json.dumps({"status": result["status"], "prepared_batch_sha256": result["prepared_batch_sha256"],
                      "preflight": 20, "dry_run": 20, "queue_unchanged": True}))


if __name__ == "__main__":
    main()
