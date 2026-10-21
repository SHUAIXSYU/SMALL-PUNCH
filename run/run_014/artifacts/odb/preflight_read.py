"""Independent, read-only identity and file-safety check for run_014 ODB."""
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "agenthub_sp_invopt"))
sys.path.insert(0, r"D:\Projects\abqjobpilot")
from hub import Hub
from abqjobpilot.api.client import AbqJobPilotClient

OUT = Path(__file__).resolve().parent
TASK_ID = "35b07ba1-22ad-48a7-b859-2d99199ed419"

def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def main():
    task = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3").task(TASK_ID)
    payload = json.loads(task["payload"])
    inp = Path(payload["inp_path"])
    odb = Path(payload["odb_path"])
    terminal = json.loads(Path(payload["solver_evidence"]).read_text(encoding="utf-8"))
    client = AbqJobPilotClient().for_project(project_id=payload["project_id"])
    status = client.status(job_id=payload["queue_id"]).to_dict()
    outputs = client.locate_outputs(job_id=payload["queue_id"]).to_dict()
    queue = json.loads((ROOT / "agenthub_sp_invopt/abqjobpilot_project/runtime/queue.json").read_text(encoding="utf-8"))
    matches = [item for item in queue["jobs"] if item.get("queue_id") == payload["queue_id"]]
    lock = odb.with_suffix(".lck")
    before = {"size": odb.stat().st_size, "mtime_ns": odb.stat().st_mtime_ns, "sha256": sha(odb)}
    after = {"size": odb.stat().st_size, "mtime_ns": odb.stat().st_mtime_ns, "sha256": sha(odb)}
    checks = {
        "task_pending_or_claimed": task["execution_state"] in {"PENDING", "CLAIMED"},
        "inp_hash": sha(inp) == payload["inp_sha256"],
        "odb_hash": before["sha256"] == payload["odb_sha256"] == after["sha256"],
        "odb_stable_two_reads": before == after,
        "single_queue_identity": len(matches) == 1,
        "queue_completed_with_warnings": len(matches) == 1 and matches[0]["status"] == "COMPLETED_WITH_WARNINGS" and matches[0]["return_code"] == 0,
        "job_name": len(matches) == 1 and matches[0]["job_name"] == payload["job_name"],
        "public_status_complete": status["status"] == "COMPLETED",
        "public_paths_match": Path(outputs["expected_odb_path"]).resolve() == odb.resolve() and Path(status["inp_path"]).resolve() == inp.resolve(),
        "lock_absent": not lock.exists() and not status["lock_exists"] and not outputs["lock_exists"],
        "terminal_identity": terminal["queue_id"] == payload["queue_id"] and terminal["inp_sha256"] == payload["inp_sha256"],
        "terminal_safe_to_open": terminal["odb_safe_to_open"] is True,
    }
    result = {
        "observed_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        "task_id": TASK_ID, "project_id": payload["project_id"], "queue_id": payload["queue_id"],
        "job_name": payload["job_name"], "checks": checks, "safe_to_open": all(checks.values()),
        "inp_sha256": sha(inp), "odb_before": before, "odb_after": after,
        "public_status": status, "public_outputs": outputs,
        "queue_record": matches[0] if len(matches) == 1 else matches,
        "runner_warning_preserved": terminal.get("tracked_processes", {}).get("FULL_RUNNING", {}).get("state"),
        "independent_read_safety": terminal.get("independent_read_safety"),
        "source_evidence": payload["solver_evidence"],
    }
    (OUT / "preflight_read.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"safe_to_open": result["safe_to_open"], "checks": checks, "runner_warning_preserved": result["runner_warning_preserved"]}, ensure_ascii=False))
    if not result["safe_to_open"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
