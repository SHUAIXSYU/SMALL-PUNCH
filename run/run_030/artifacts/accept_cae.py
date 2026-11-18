"""MAIN receives the real CAE completion and verifies all Hub evidence hashes."""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A = ROOT / "run/run_030/artifacts"
P = A / "private"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from agenthub_sp_invopt.hub import Hub


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    with Path(p).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def main():
    assert not (P / "main_cae_acceptance.json").exists()
    session = read(P / "main_session.json")
    task_id = session["cae_task_id"]
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3", lease_seconds=3600)
    task = hub.task(task_id)
    assert task["assigned_role"] == "CAE" and task["execution_state"] == "COMPLETED"
    assert task["evidence_state"] == "RECORDED" and task["science_state"] == "NOT_EVALUATED"
    result = json.loads(task["result"])
    assert result["execution_status"] == "COMPLETED_PREPARATION_ONLY"
    assert result["candidate_count"] == result["preflight_passed"] == result["dry_run_passed"] == 8
    assert result["new_enqueues"] == result["datacheck_starts"] == result["solver_starts"] == 0
    assert result["queue_unchanged"] and result["settings_unchanged"]
    receipt = read(P / "cae/agenthub_receipt.json")
    assert receipt["task_id"] == task_id and receipt["execution_state"] == "COMPLETED"
    identity = hub.session_identity(receipt["session_id"])
    assert identity["role"] == "CAE" and identity["agent_id"] == receipt["agent_id"]
    with hub.connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT path,sha256,producer,version FROM artifacts WHERE task_id=?", (task_id,))]
    assert len(rows) == receipt["hub_artifacts_registered"] >= 24
    assert all(r["producer"] == identity["agent_id"] for r in rows)
    for r in rows:
        path = Path(r["path"])
        assert path.is_file() and path.resolve().is_relative_to(ROOT.resolve())
        assert sha(path) == r["sha256"]
    messages = hub.poll_messages(session["identity"])
    matched = [m for m in messages if m["task_id"] == task_id and m["sender"] == identity["agent_id"]]
    assert len(matched) == 1
    body = json.loads(matched[0]["body"])
    assert body["task_id"] == task_id and body["candidate_count"] == 8
    assert hub.verify_chain()
    output = {
        "at": datetime.now().astimezone().isoformat(), "status": "REAL_CAE_ACCEPTED",
        "cae_task_id": task_id, "cae_agent_id": identity["agent_id"],
        "cae_session_id": identity["session_id"], "hub_generation": receipt["generation"],
        "registered_artifacts": len(rows), "verified_artifacts": len(rows),
        "main_received_message_id": matched[0]["message_id"],
        "message_body": body, "audit_chain_valid": True,
        "no_queue_or_solver": True,
    }
    save(P / "main_cae_acceptance.json", output)
    print(json.dumps({"status": output["status"], "task_id": task_id,
                      "artifacts": len(rows), "message_id": output["main_received_message_id"]}))


if __name__ == "__main__":
    main()
