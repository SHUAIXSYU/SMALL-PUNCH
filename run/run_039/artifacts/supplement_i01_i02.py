"""Append the two earlier run_030 jobs to the real ODB task scope."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_039"
sys.path[:0] = [str(ROOT), r"D:\Projects\abqjobpilot"]
from abqjobpilot.api import AbqJobPilotClient
from agenthub_sp_invopt.hub import Hub


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main():
    assert sys.executable.lower() == r"d:\xianlab\envs\torch-gpu\python.exe"
    task = read(RUN / "artifacts/task_ids.json")["odb_task_id"]
    prepared = read(ROOT / "run/run_030/artifacts/prepared_batch.json")
    api = AbqJobPilotClient().for_project(project_id="b87d2cd6-8519-4ac3-bae6-7eb989fb2dae")
    jobs = api.list_jobs()["jobs"]
    entries = []
    for pid in ("I01", "I02"):
        point = next(x for x in prepared["points"] if x["point_id"] == pid)
        job = next(x for x in jobs if x["job_name"] == point["job_name"])
        inp = ROOT / point["inp_path"]
        odb = ROOT / point["expected_odb"]
        assert sha(inp) == point["inp_sha256"] and odb.is_file()
        assert job["raw_status"] in {"COMPLETED_OK", "COMPLETED_WITH_WARNINGS"}
        assert job["return_code"] == 0 and job["final_verdict"] == "SUCCESS"
        assert job["started_at"] and job["ended_at"]
        assert (job["cpus"], job["gpus"], job["run_datacheck"], job["run_full"]) == (14, 0, True, True)
        assert not (Path(job["work_dir"]) / f"{job['job_name']}.lck").exists()
        assert api.status(job_id=job["queue_id"]).to_dict()["status"] == "COMPLETED"
        entries.append({"point_id": pid, "job_name": job["job_name"],
                        "queue_id": job["queue_id"], "inp_path": str(inp),
                        "inp_sha256": sha(inp), "odb_path": str(odb),
                        "odb_sha256": sha(odb), "duration_sec": job["duration_sec"],
                        "numeric_version": "run030-standard-m0025-hollomon-v1",
                        "loss_version": "run017-exploratory-fd-v1"})
    body = {"at": datetime.now().astimezone().isoformat(), "run": "run_039",
            "task_id": task, "supplement": "Complete the same-version 22-point dataset",
            "i01": "Verify prior real ODB result in run/run_032/artifacts/private/odb and source hashes; reuse if unchanged",
            "i02": "No prior ODB extraction located; perform real Abaqus Python read-only extraction and frozen Loss or set null with reason",
            "jobs": entries,
            "new_output_dir": "run/run_039/artifacts/private/odb/I02",
            "restrictions": "No Solver, Datacheck, enqueue, retry, sealed tensile data, source modification, or commit/push"}
    path = RUN / "artifacts/i01_i02_supplement.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(body, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3")
    main = hub.register("MAIN", "codex-main-run039-doe-audit")
    hub.message(task, main["agent_id"], "ODB", body,
                "run039-i01-i02-22-point-supplement-v1")
    assert hub.verify_chain()
    print(json.dumps({"task_id": task, "supplement_path": str(path),
                      "i01_queue_id": entries[0]["queue_id"],
                      "i02_queue_id": entries[1]["queue_id"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
