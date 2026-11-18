"""MAIN's independent read-only audit of CAE outputs and public API previews."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A = ROOT / "run/run_030/artifacts"
P = A / "private"
PROJECT = ROOT / "agenthub_sp_invopt/abqjobpilot_project"
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from inverse.hollomon import generate_hollomon_table
from abqjobpilot.api import AbqJobPilotClient, JobRequest
from agenthub_sp_invopt.hub import Hub


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, item):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(item, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def split(raw: bytes, candidate: bool):
    start_marker = b"** RUN_030 POINT" if candidate else b"** CANDIDATE ONLY:"
    start = raw.index(start_marker)
    # Preserve the separator comment after the Plastic rows as model bytes.
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


def main():
    assert not (P / "main_verification.json").exists()
    design = read(A / "parameter_design.json")
    model = read(A / "model_contract.json")
    manifest = read(A / "cae_candidate_manifest.json")
    loss = read(A / "loss_contract_binding.json")
    assert design["version"] == "run030-initial-eight-v1" and len(design["points"]) == 8
    assert manifest["task_id"] == read(A / "task_ids.json")["cae_task_id"]
    assert manifest["source_sha256"] == model["source_inp_sha256"]
    assert manifest["design_sha256"] == sha(A / "parameter_design.json")
    source = ROOT / model["source_inp"]
    assert sha(source) == model["source_inp_sha256"]
    source_nonmaterial, _ = split(source.read_bytes(), False)
    nonmaterial_sha = hashlib.sha256(source_nonmaterial).hexdigest()
    assert manifest["nonmaterial_sha256"] == nonmaterial_sha
    assert sha(ROOT / "inverse/hollomon.py") == manifest["generator_sha256"]
    assert sha(ROOT / loss["target_path"]) == loss["target_sha256"]
    assert sha(ROOT / loss["config_path"]) == loss["config_sha256"]
    assert sha(ROOT / loss["implementation_path"]) == loss["implementation_sha256"]
    assert len(manifest["points"]) == 8
    manifest_by_id = {p["point_id"]: p for p in manifest["points"]}

    api = AbqJobPilotClient()
    caps = api.capabilities()
    assert caps["application_version"] == "0.2.2"
    settings = api.get_project_settings(project_id=PID).to_dict()
    assert settings["status"] == "PERSISTED" and settings["persisted"] is True and not settings["defaulted_fields"]
    assert settings["project_id"] == PID
    assert Path(settings["project_path"]).resolve() == PROJECT.resolve()
    assert read(PROJECT / "project.json")["project_id"] == PID
    stored = settings["settings"]
    assert stored == read(PROJECT / "runtime/settings.json")
    expected = {"abaqus_cmd": r"D:\ABAQUS2024\Commands\abq2024.bat", "default_cpus": 14,
                "default_gpus": 0, "use_gpu": False, "run_datacheck": True, "run_full": True}
    assert all(stored[k] == v for k, v in expected.items())
    assert Path(stored["abaqus_cmd"]).is_file()
    scoped = api.for_project(project_id=PID)
    protected = [PROJECT / "project.json", PROJECT / "project.db",
                 PROJECT / "runtime/settings.json", PROJECT / "runtime/queue.json",
                 PROJECT / "runtime/live_status.json"]
    before = {str(p): sha(p) if p.is_file() else None for p in protected}
    queue_before = scoped.list_jobs()
    assert queue_before["status"] == "OK"
    existing_names = {j.get("job_name") for j in queue_before["jobs"]}
    history_before = api.list_project_jobs(project_id=PID).to_dict()
    assert history_before["status"] == "OK"
    existing_names |= {j.get("job_name") for j in history_before["jobs"]}
    results = []
    for p in design["points"]:
        m = manifest_by_id[p["point_id"]]
        assert all(m[key] == p[key] for key in ("job_name", "inp_path", "working_dir", "sigma_y_mpa", "n"))
        assert p["job_name"] not in existing_names
        inp = ROOT / p["inp_path"]
        params = ROOT / p["parameters_path"]
        work = ROOT / p["working_dir"]
        assert inp.is_file() and inp.stem == p["job_name"] and params.is_file()
        assert work.is_dir() and not any(work.iterdir())
        assert sha(inp) == m["sha256"]
        parm = read(params)
        assert parm["sigma_y_mpa"] == p["sigma_y_mpa"] and parm["n"] == p["n"]
        assert parm["inp_sha256"] == m["sha256"]
        raw = inp.read_bytes()
        nonmaterial, rows = split(raw, True)
        assert nonmaterial == source_nonmaterial
        assert hashlib.sha256(nonmaterial).hexdigest() == nonmaterial_sha
        assert raw.count(b"*Static\n0.001, 1., 1e-12, 0.0025") == 1
        assert not any(line.lower().startswith((b"*include", b"*import", b"*restart, read"))
                       for line in raw.splitlines())
        table = generate_hollomon_table(p["sigma_y_mpa"], p["n"],
                                        max_plastic_strain=0.9, relative_tolerance=0.001)
        assert len(rows) == len(table.rows) == m["material_rows"]
        assert all(math.isclose(a, b, rel_tol=1e-15, abs_tol=1e-18)
                   for row, generated in zip(rows, table.rows) for a, b in zip(row, generated))
        assert rows[0][1] == 0 and rows[-1][1] == 0.9
        assert table.conservative_relative_error_bound <= 0.001
        request = JobRequest(inp_path=str(inp), job_name=p["job_name"], working_dir=str(work),
                             cpus=14, gpus=0, run_datacheck=True, run_full=True,
                             submission_mode="preview_only", allow_solver_submit=False,
                             batch="SPIO_run030_initial8_PREVIEW", strategy="balanced_global_local_initial8",
                             metadata={"run": "run_030", "point_id": p["point_id"],
                                       "project_id": PID, "inp_sha256": m["sha256"],
                                       "authorized_enqueues": 0, "authorized_solver_jobs": 0})
        pre = scoped.preflight(request).to_dict()
        dry = scoped.enqueue(request, dry_run=True).to_dict()
        assert pre["status"] == "PREVIEW_READY" and not pre["errors"]
        assert dry["status"] == "DRY_RUN_READY" and not dry["errors"] and dry["job_id"] is None
        assert not any(dry[key] for key in ("queue_file_mutated", "solver_started", "runner_started", "forbidden_mutations_detected"))
        assert Path(pre["expected_odb_path"]).resolve() == (ROOT / p["expected_odb"]).resolve()
        assert sha(inp) == m["sha256"] and not any(work.iterdir())
        results.append({"point_id": p["point_id"], "job_name": p["job_name"],
                        "inp_sha256": m["sha256"], "material_rows": len(rows),
                        "preflight": pre["status"], "dry_run": dry["status"],
                        "expected_odb": p["expected_odb"], "workdir_empty": True})
    after = {str(p): sha(p) if p.is_file() else None for p in protected}
    queue_after = scoped.list_jobs()
    history_after = api.list_project_jobs(project_id=PID).to_dict()
    assert before == after and queue_before == queue_after and history_before == history_after
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    session = read(P / "main_session.json")
    task = hub.task(session["cae_task_id"])
    assert task is not None and task["assigned_role"] == "CAE"
    audit = {"at": datetime.now().astimezone().isoformat(), "status": "PASS_OFFLINE_PREPARATION",
             "cae_task_state_at_audit": task["execution_state"], "project_id": PID,
             "project_settings": "PERSISTED", "abqjobpilot_version": caps["application_version"],
             "abaqus_cmd_exists": True, "source_sha256": sha(source),
             "design_sha256": sha(A / "parameter_design.json"),
             "nonmaterial_sha256": nonmaterial_sha, "loss_target_sha256": loss["target_sha256"],
             "results": results, "protected_hashes_before": before, "protected_hashes_after": after,
             "queue_unchanged": True, "history_unchanged": True, "new_queue_jobs": 0,
             "solver_started": False, "datacheck_started": False,
             "preview_limit": "Public preflight/dry-run do not establish Abaqus datacheck, license or convergence"}
    save(P / "main_verification.json", audit)
    print(json.dumps({"status": audit["status"], "count": len(results),
                      "preflight_pass": sum(r["preflight"] == "PREVIEW_READY" for r in results),
                      "dry_run_pass": sum(r["dry_run"] == "DRY_RUN_READY" for r in results),
                      "queue_unchanged": True, "cae_task_state": task["execution_state"]}))


if __name__ == "__main__":
    main()
