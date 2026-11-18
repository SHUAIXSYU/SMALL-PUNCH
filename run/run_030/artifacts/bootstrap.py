"""Freeze the offline 16-evaluation pilot and dispatch eight CAE inputs."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from math import exp, log
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_030"
ART = RUN / "artifacts"
PRIVATE = ART / "private"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from agenthub_sp_invopt.hub import Hub

TZ = timezone(timedelta(hours=8))
PID = "b87d2cd6-8519-4ac3-bae6-7eb989fb2dae"
SOURCE = ROOT / "run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp"
SOURCE_SHA = "dae9345bc60973c27edec498dfbd27f269e1f5bbe151316918862954faac40c9"


def now() -> str:
    return datetime.now(TZ).isoformat()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def save(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    assert not (RUN / "run.json").exists()
    assert sha(SOURCE) == SOURCE_SHA
    loss_identity = ROOT / "run/run_017/artifacts/loss_contract_identity.json"
    ident = json.loads(loss_identity.read_text(encoding="utf-8"))
    config = ROOT / ident["path"]
    cfg = json.loads(config.read_text(encoding="utf-8"))
    target = ROOT / cfg["target"]
    assert sha(config) == ident["sha256"]
    assert sha(target) == cfg["target_sha256"]
    assert sha(ROOT / ident["implementation"]) == ident["implementation_sha256"]
    assert cfg["source_rows_count"] == 339 and cfg["selected_points"] == 241
    assert cfg["window_m"] == [0.0, 0.0012] and cfg["force_reference_n"] == 1428.9
    assert cfg["version"] == "run017-exploratory-fd-v1"
    review = json.loads((ROOT / "run/run_029/artifacts/private/main_review.json").read_text(encoding="utf-8"))
    assert review["decision"] == "PASS_CENTER_ADJACENT_REFINEMENT_ONLY"
    assert review["run025_original_qualification"] == "BLOCKED_V01_NUMERICAL_QUALIFICATION_UNCHANGED"
    source_text = SOURCE.read_text(encoding="utf-8")
    assert source_text.count("*Static\n0.001, 1., 1e-12, 0.0025") == 1
    assert source_text.count("*Step, name=Step_Punch_Displacement, nlgeom=YES, inc=999999") == 1

    start = now()
    baseline = {
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "remote": git("remote", "-v"),
        "working_tree": git("status", "--short"),
    }
    # Four deliberately stratified global points plus four targeted points.
    # Both branches later receive all eight common evaluations; none is an answer.
    coordinates = [
        ("I01", "GLOBAL", 0.125, 0.875),
        ("I02", "LOCAL", 0.120, 0.200),
        ("I03", "GLOBAL", 0.375, 0.375),
        ("I04", "LOCAL", 0.180, 0.320),
        ("I05", "GLOBAL", 0.625, 0.625),
        ("I06", "LOCAL", 0.240, 0.160),
        ("I07", "GLOBAL", 0.875, 0.125),
        ("I08", "LOCAL", 0.300, 0.280),
    ]
    points = []
    for point_id, region, x, y in coordinates:
        job = f"SPIO_R030_{point_id}_{region[0]}"
        sigma = 150.0 * exp(x * log(1000.0 / 150.0))
        n = 0.02 + 0.48 * y
        assert 150 <= sigma <= 1000 and 0.02 <= n <= 0.5
        inp = ART / "candidates" / job / f"{job}.inp"
        params = inp.parent / "parameters.json"
        work = ART / "solver" / job
        assert not inp.exists() and not params.exists() and not work.exists()
        points.append({
            "point_id": point_id, "region": region, "x": x, "y": y,
            "sigma_y_mpa": sigma, "n": n, "job_name": job,
            "inp_path": rel(inp), "parameters_path": rel(params),
            "working_dir": rel(work), "expected_odb": rel(work / f"{job}.odb"),
        })
    assert len({(p["sigma_y_mpa"], p["n"]) for p in points}) == 8
    design = {
        "version": "run030-initial-eight-v1", "frozen_at": start,
        "selection_method": "Four deterministic 4-stratum global pairs and four targeted low-Loss-region points; coordinates set before new FE results",
        "basis": "SPT-only run022 observed low-Loss L04 (200 MPa, n=0.124); no sealed tensile data",
        "global_fraction": 0.5, "local_fraction": 0.5,
        "global_rule": "x stratum midpoints 0.125,0.375,0.625,0.875; y permutation 0.875,0.375,0.625,0.125",
        "local_rule": "predeclared x=0.12,0.18,0.24,0.30 and y=0.20,0.32,0.16,0.28 near observed SPT lower-Loss zone; no post-score reselection",
        "coordinates": {"x": "ln(sigma_y_mpa/150)/ln(1000/150)", "y": "(n-0.02)/0.48"},
        "bounds": {"sigma_y_mpa": [150, 1000], "n": [0.02, 0.50], "status": "ENGINEERING_EXPLORATORY_NOT_TENSILE_PRIOR"},
        "fixed": {"E_pa": 210000000000, "nu": 0.3, "max_plastic_strain": 0.9,
                  "material_model": "candidate-true-total-hollomon-v1", "relative_tolerance": 0.001},
        "points": points, "authorized_solver_jobs": 0, "authorized_enqueues": 0,
    }
    save(ART / "parameter_design.json", design)
    model = {
        "version": "run030-standard-m0025-hollomon-v1", "frozen_at": start,
        "source_inp": rel(SOURCE), "source_inp_sha256": SOURCE_SHA,
        "source_run": "run_027", "center_numerical_check": "run_029 PASS_CENTER_ADJACENT_REFINEMENT_ONLY",
        "static_step": {"solver": "Abaqus/Standard", "initial_increment": 0.001,
                        "maximum_increment": 0.0025, "minimum_increment": 1e-12,
                        "total_time": 1.0, "maximum_increments": 999999},
        "resources": {"cpus": 14, "gpus": 0, "datacheck": True, "full_analysis": True},
        "material": design["fixed"],
        "model_reuse": "Exact source bytes outside candidate material table and candidate-only comments; geometry, mesh, contact, BC, displacement loading and physical output unchanged",
        "scope_limit": "Only center adjacent increment check passed; other parameters require individual numerical review",
    }
    save(ART / "model_contract.json", model)
    loss = {
        "version": cfg["version"], "loss_identity_path": rel(loss_identity), "loss_identity_sha256": sha(loss_identity),
        "config_path": rel(config), "config_sha256": sha(config),
        "target_path": rel(target), "target_sha256": sha(target),
        "implementation_path": ident["implementation"], "implementation_sha256": ident["implementation_sha256"],
        "source_rows": 339, "window_m": [0, 0.0012], "points": 241,
        "F_ref_n": 1428.9, "weights": "equal", "interpolation": "linear FE to fixed experimental grid; no extrapolation",
        "sign": "u=-Punch RP U2, F=-Punch RP RF2; experimental signs unchanged",
        "zero_shift": 0, "compliance_recorrection": False,
        "score_status": "EXPLORATORY_PROVISIONAL; not physical validation",
    }
    save(ART / "loss_contract_binding.json", loss)
    budget = {
        "version": "run030-sixteen-pilot-v1", "frozen_at": start,
        "total_unique_new_fe_cap": 16, "authorized_now": 0, "automatic_retries": 0,
        "stage_a": {"count": 8, "points": [p["point_id"] for p in points], "gate_after": 4,
                    "common_to": ["BO", "DE"], "submission": "One Job per human-reviewed queue start"},
        "stage_b": {"algorithm": "BO", "new_fe_cap": 4, "proposal": "Sequential one-at-a-time GP Matern-5/2 ARD expected improvement on normalized x,y; seed 2301; future candidates depend on own observed results only"},
        "stage_c": {"algorithm": "DE", "new_fe_cap": 4, "proposal": "Four trials from shared 8-point population, rand/1/bin F=0.7 CR=0.9, seed 2302, no polish; this is half a generation, not DE convergence"},
        "fairness": "Both branches see same eight initial evaluations, then only their own new evaluations; same four-new-FE cap per branch; failed attempts consume budget; no superiority claim from one seed",
        "duplicates": "Exact parameter/model/precision/Loss cache hit uses no new FE; no silent cross-branch disclosure; bounded proposal regeneration then MAIN review",
        "stop": "Any failed or uncertain phase, incomplete 0-1.2mm curve, PEEQ beyond table, unresolved accepted-state severe warning or new systematic contact/curve anomaly pauses further submissions; no automatic retry or imputed zero Loss",
        "numerical_control": "One Job in Queue at a time; local Runner auto-fail-stop unavailable; fresh ownership/recovery/output checks required before each authorization use",
        "cost_planning": "Reference run029 center wall time 253 s at 14 CPUs; broad-domain cost unknown. Planning only: 4-20 min/Job, eight 32-160 min, sixteen 64-320 min, allocated 14-core time not measured CPU use",
    }
    save(ART / "budget_protocol.json", budget)
    odb = {
        "version": "run030-odb-result-envelope-v1", "status": "FUTURE_READ_ONLY_PROTOCOL",
        "required": ["point_id", "job_name", "queue_id", "inp_sha256", "odb_sha256", "project_id",
                     "datacheck_status", "full_status", "actual_runtime_s", "punch_rp_identity",
                     "raw_u2_rf2_step_time_csv", "positive_fd_csv", "fd_window_coverage",
                     "max_saved_peeq", "material_table_max_plastic_strain", "accepted_increments",
                     "rejected_attempts", "warning_events_by_accepted_or_rejected",
                     "contact_transition_review", "local_fd_jump_review", "loss_contract_sha256",
                     "loss_or_null", "loss_status", "artifact_hashes", "science_status"],
        "loss_failure_rule": "null, not zero or finite penalty, on failed/incomplete/invalid FE; MAIN reviews before more Jobs",
        "no_curve_modification": "No per-Job shift, crop, smoothing, compliance adjustment, or interpolation extrapolation",
    }
    save(ART / "odb_result_protocol.json", odb)
    run = {
        "schema_version": "1.0", "run_id": "run_030", "stage": "16-evaluation exploratory inversion offline preparation",
        "objective": "Freeze one precision/model/Loss contract and prepare eight shared initial FE candidates without queue or solver",
        "status": "RUNNING", "start_time": start, "end_time": None,
        "python_interpreter": sys.executable, "python_version": sys.version.split()[0], "git": baseline,
        "inputs": [{"path": rel(p), "sha256": sha(p)} for p in
                   [SOURCE, ROOT / "inverse/hollomon.py", loss_identity, config, target,
                    ROOT / "run/run_029/artifacts/private/main_review.json"]],
        "outputs": [], "validation": [], "errors": [],
    }
    save(RUN / "run.json", run)
    save(RUN / "checkpoints/start.json", {"at": start, "git": baseline, "design_sha256": sha(ART / "parameter_design.json"), "source_sha256": SOURCE_SHA})
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    identity = hub.register("MAIN", "codex-main-run030-preparation")
    main_task = hub.create_task(identity["agent_id"], "MAIN", "prepare_sixteen_pilot",
                                {"run": "run_030", "new_solver_authorization": 0, "design_sha256": sha(ART / "parameter_design.json")},
                                "run030-main-preparation-v1")["task_id"]
    lease = hub.claim(main_task, identity, "run030-main-claim-v1")
    payload = {
        "run": "run_030", "main_task_id": main_task, "scope": "Prepare exactly eight INPs offline, no queue or solver",
        "design_path": rel(ART / "parameter_design.json"), "design_sha256": sha(ART / "parameter_design.json"),
        "model_contract_path": rel(ART / "model_contract.json"), "model_contract_sha256": sha(ART / "model_contract.json"),
        "source_inp_absolute": str(SOURCE), "source_sha256": SOURCE_SHA,
        "generator": "inverse/hollomon.py", "generator_sha256": sha(ROOT / "inverse/hollomon.py"),
        "points": points, "project_id": PID,
        "requirements": [
            "Real CAE Codex session must claim this Hub task, use a long lease and return a persistent result message to MAIN",
            "Generate exact eight unique INPs from run027 source, changing only candidate comments and *Plastic table generated by inverse/hollomon.py; retain *Static 0.001,1,1e-12,0.0025 and all nonmaterial bytes",
            "For each candidate write parameters JSON, verify full hash, table p=0..0.9 monotonic and error bound <=0.001, unique empty work directory, no relative INCLUDE/external model dependency",
            "Use AbqJobPilot 0.2.2 public preflight and enqueue(dry_run=True) with explicit project/job/workdir/14CPU/0GPU/Datacheck+Full; verify queue/Settings/source identity unchanged",
            "Register artifacts and structured result in AgentHub; do not enqueue, datacheck, solver, optimize or read sealed tensile data",
        ],
        "new_enqueues_authorized": 0, "new_solver_jobs_authorized": 0,
    }
    cae_task = hub.create_task(identity["agent_id"], "CAE", "prepare_eight_initial_inps", payload,
                               "run030-cae-eight-preparation-v1")["task_id"]
    hub.approve(cae_task, identity["agent_id"], "generate_inp")
    hub.approve(cae_task, identity["agent_id"], "verify_inp")
    hub.message(cae_task, identity["agent_id"], "CAE", payload, "run030-cae-dispatch-v1")
    save(PRIVATE / "main_session.json", {"identity": identity, "lease": lease, "main_task_id": main_task, "cae_task_id": cae_task})
    save(ART / "task_ids.json", {"main_task_id": main_task, "cae_task_id": cae_task})
    assert hub.verify_chain()
    print(json.dumps({"status": "RUNNING", "run": "run_030", "cae_task_id": cae_task,
                      "design_sha256": sha(ART / "parameter_design.json"), "points": len(points)}))


if __name__ == "__main__":
    main()
