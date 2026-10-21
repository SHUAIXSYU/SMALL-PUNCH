"""Non-solver, separate-process CLI acceptance against one persistent SQLite file."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "private"
PRIVATE.mkdir(exist_ok=True)
DB = PRIVATE / "cli_acceptance.sqlite3"
CLI = ROOT / "agenthub_sp_invopt" / "cli.py"


def call(*args, deny=None):
    proc = subprocess.run([sys.executable, "-B", str(CLI), "--db", str(DB), *map(str, args)],
                          text=True, capture_output=True, timeout=20)
    if deny is not None:
        assert proc.returncode == 2 and deny in proc.stderr, (args, proc.returncode, proc.stderr)
        return {"denied": deny}
    assert proc.returncode == 0, (args, proc.returncode, proc.stderr)
    return json.loads(proc.stdout)


def data(name, content):
    path = PRIVATE / name
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if DB.exists():
        raise SystemExit("ACCEPTANCE_DB_EXISTS_REFUSE_OVERWRITE")
    main_id = call("register", "--role", "MAIN", "--name", "run009-main")
    cae_id = call("register", "--role", "CAE", "--name", "run009-cae")
    odb_id = call("register", "--role", "ODB", "--name", "run009-odb")
    payload = data("cae_request.json", {"simulation": True, "operation": "write mock INP metadata", "solver": "FORBIDDEN"})
    task1 = call("create", "--actor", main_id["agent_id"], "--role", "CAE", "--kind", "mock_inp", "--payload-file", payload, "--key", "run009-cae-v1")
    t1 = task1["task_id"]
    duplicate_task = call("create", "--actor", main_id["agent_id"], "--role", "CAE", "--kind", "mock_inp", "--payload-file", payload, "--key", "run009-cae-v1")
    assert duplicate_task["task_id"] == t1
    call("create", "--actor", cae_id["agent_id"], "--role", "CAE", "--kind", "forbidden", "--payload-file", payload, "--key", "denied", deny="CREATE_DENIED")
    call("approve", "--actor", main_id["agent_id"], "--task", t1, "--action", "generate_inp")
    body = data("main_to_cae.json", {"simulation": True, "task_id": t1})
    msg = call("message", "--sender", main_id["agent_id"], "--task", t1, "--to", "CAE", "--body-file", body, "--key", "main-cae-v1")
    assert call("message", "--sender", main_id["agent_id"], "--task", t1, "--to", "CAE", "--body-file", body, "--key", "main-cae-v1")["message_id"] == msg["message_id"]
    assert len(call("messages", "--session", cae_id["session_id"])) == 1
    assert call("messages", "--session", cae_id["session_id"]) == []
    assert any(x["task_id"] == t1 for x in call("inbox", "--session", cae_id["session_id"]))
    call("claim", "--session", odb_id["session_id"], "--task", t1, "--key", "wrong-role", deny="CLAIM_DENIED")
    lease1 = call("claim", "--session", cae_id["session_id"], "--task", t1, "--key", "cae-claim")
    lease1_file = data("cae_lease.json", lease1)
    call("claim", "--session", cae_id["session_id"], "--task", t1, "--key", "duplicate", deny="TASK_NOT_CLAIMABLE")
    mock_inp = PRIVATE / "SIMULATED_ONLY.inp.txt"
    mock_inp.write_text("SIMULATED_ONLY; NO_ABAQUS_INPUT_OR_SOLVER\n", encoding="utf-8")
    provenance = data("cae_provenance.json", {"simulation": True, "source": "run009 fixture", "version": "mock-v1"})
    a1 = call("artifact", "--lease-file", lease1_file, "--path", mock_inp, "--provenance-file", provenance)
    assert a1["sha256"] == sha(mock_inp)
    result1 = data("cae_result.json", {"simulation": True, "artifact_sha256": a1["sha256"], "solver_started": False, "science": "NOT_EVALUATED"})
    call("finish", "--lease-file", lease1_file, "--result-file", result1, "--science-state", "NOT_EVALUATED")
    call("finish", "--lease-file", lease1_file, "--result-file", result1, deny="LEASE_INVALID")
    payload2 = data("odb_request.json", {"simulation": True, "input_task": t1, "operation": "read mock evidence"})
    task2 = call("create", "--actor", main_id["agent_id"], "--role", "ODB", "--kind", "mock_odb_read", "--payload-file", payload2, "--key", "run009-odb-v1", "--depends", t1)
    t2 = task2["task_id"]
    assert any(x["task_id"] == t2 for x in call("inbox", "--session", odb_id["session_id"]))
    lease2 = call("claim", "--session", odb_id["session_id"], "--task", t2, "--key", "odb-claim")
    lease2_file = data("odb_lease.json", lease2)
    mock_result = data("mock_odb_result.json", {"simulation": True, "input_sha256": sha(mock_inp), "physical_result": "NOT_EVALUATED", "source": "SIMULATED_ONLY.inp.txt"})
    a2 = call("artifact", "--lease-file", lease2_file, "--path", mock_result, "--provenance-file", provenance)
    result2 = data("odb_result.json", {"simulation": True, "artifact_sha256": a2["sha256"], "physics": "NOT_EVALUATED"})
    call("finish", "--lease-file", lease2_file, "--result-file", result2, "--science-state", "NOT_EVALUATED")
    call("message", "--sender", odb_id["agent_id"], "--task", t2, "--to", "MAIN", "--body-file", result2, "--key", "odb-main-v1")
    received = call("messages", "--session", main_id["session_id"])
    assert len(received) == 1 and received[0]["task_id"] == t2
    assert call("messages", "--session", main_id["session_id"]) == []
    assert call("audit")["audit_hash_chain_valid"] is True
    report = {"scope": "SIMULATED_ONLY_NO_SOLVER", "database": str(DB.relative_to(ROOT)).replace("\\", "/"),
              "task_ids": {"CAE": t1, "ODB": t2}, "artifact_sha256": {"CAE": a1["sha256"], "ODB": a2["sha256"]},
              "checks": ["separate_processes", "shared_sqlite", "task_idempotency", "message_dedup", "message_receipt", "role_denial", "exclusive_claim", "duplicate_finish_denial", "artifact_hash", "dependency", "main_delivery", "audit_chain"],
              "execution": "PASS", "science": "NOT_EVALUATED", "solver_started": False}
    data("cli_acceptance_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
