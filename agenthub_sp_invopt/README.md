# SP-InvOpt AgentHub (run_008)

Independent standard-library SQLite ledger adapted from verified patterns in `E:\Projects\Stage-5\RL-LAM-AgentHub` (SQLite `BEGIN IMMEDIATE`, leases, idempotency, task-scoped evidence and hash-chained audit events). No Stage-5 code/database is loaded or modified. Roles: MAIN (create, approve), CAE (candidate input generation), ODB (read-only result extraction). Execution, evidence and science states are independent.

The single source of truth is the run-local SQLite file. `poll.py` opens a real independent process session, polls an inbox, and transactionally claims one task. This verifies process polling and exclusive claim; it does **not** send notifications to or prove receipt by another Codex conversation. Use manual Handoff unless the recipient session visibly polls and claims.

Approvals are task scoped and distinct: `generate_inp`, `verify_inp`, `enqueue`, `start_solver`, `recover_retry`. A MAIN approval for one action does not authorize another. There is no enqueue/solver implementation in this Hub. The AbqJobPilot adapter is deliberately a separate preview/read-only layer.

```powershell
$Py='D:\XianLab\envs\torch-gpu\python.exe'
$Hub='E:\Projects\SMALL-PUNCH\agenthub_sp_invopt'
& $Py -B -c "import sys; sys.path.insert(0,r'$Hub'); from hub import Hub; h=Hub(r'$Hub\runtime\sp_invopt.sqlite3'); print(h.verify_chain())"
& $Py -B "$Hub\poll.py" --db "$Hub\runtime\sp_invopt.sqlite3" --role CAE --name "CAE-local" --seconds 30
```

The isolated SQLite database contains task and session state and must not be shared with Stage-5. Messages are durable records, not delivery receipts. Lease timeout moves work to `RECOVERY_REQUIRED`; a MAIN recovery approval and confirmed stopped worker are required before reset. Artifact records bind path, SHA-256 and provenance. No AgentHub API starts Abaqus.

Run 009 adds a JSON [CLI](CLI.md), explicit artifact version, persistent failure diagnosis, and stronger task-holder checks. See [the validation report](../run/run_009/summary.md). These additions retain the existing SQLite ledger and its completed Run 008 records.
