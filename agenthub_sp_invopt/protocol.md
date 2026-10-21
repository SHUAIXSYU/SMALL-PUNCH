# SP-InvOpt AgentHub protocol v1

## Authority and identities

The SQLite file `runtime/sp_invopt.sqlite3` is the sole state authority. Register each independent process/session with `Hub.register(role, name)`; records contain `agent_id` and a fresh `session_id`. Allowed roles are `MAIN`, `CAE`, and `ODB`. MAIN alone creates tasks and grants approvals. CAE may claim only CAE tasks; ODB may claim only ODB tasks. Task text and JSON are data, never shell commands or instructions to dynamically import code.

## Task/message envelope

Tasks store an immutable JSON payload, role, kind, idempotency key, dependencies and separate `execution_state`, `evidence_state`, and `science_state`. A reused task idempotency key returns its original task only when role, kind and payload are identical; different payloads fail closed. A dependency is claimable only after every parent task is `COMPLETED`.

Message bodies are JSON values. Each `Hub.message(task, sender, recipient_role, body, idempotency_key)` transaction persists matching OUTBOX and INBOX rows and one append-only event. The same key/body is idempotent; a changed body conflicts. A receiving process calls `poll_messages(identity)`; each session receives a durable receipt once. A database INBOX row or a local process receipt does not prove another Codex conversation received it.

The process adapter performs a bounded poll and transactional claim:

```powershell
$Py='D:\XianLab\envs\torch-gpu\python.exe'
$Hub='E:\Projects\SMALL-PUNCH\agenthub_sp_invopt'
& $Py -B "$Hub\poll.py" --db "$Hub\runtime\sp_invopt.sqlite3" --role CAE --name "CAE-local" --seconds 30
```

This starts a local Python worker session, not a persistent background service and not a Codex-session notifier. Continue with manual Handoff unless the destination Codex chat itself confirms receipt and claim. No cross-session delivery was configured in this Run.

## Claims, leases and recovery

Claims use SQLite `BEGIN IMMEDIATE`, bind agent/session/token/generation and a finite lease, and reject a second claimant. Heartbeat renews only the matching live lease. Expiry becomes `RECOVERY_REQUIRED`; it does not imply the process stopped. MAIN must record a recovery decision only after independently confirming worker termination. `recover(..., worker_stopped_confirmed=True)` records that assertion; false is rejected. New claim increments the generation. Hub recovery does not requeue an AbqJobPilot item.

## Task-scoped permissions

MAIN approvals are independent rows keyed by task and action: `generate_inp`, `verify_inp`, `enqueue`, `start_solver`, and `recover_retry`. One action never authorizes another. The current Run implements candidate file generation and verification. There is no queue-write, solver-start or retry executor in this Hub; the external-action guard rejects even an approved queue/solver action with `EXTERNAL_ACTION_DISABLED_IN_RUN008`. AbqJobPilot remains the Project/Queue/Runner/history owner.

## Evidence and scientific status

`Hub.artifact` records resolved artifact path, SHA-256, producer, provenance and creation event. Audit events are append-only and SHA-256 chained; call `verify_chain()` for integrity. Large source files are referenced in place and are never copied. Execution success means the assigned software task finished. Evidence status means specified files were recorded. Science status remains `WARNING` or `NOT_EVALUATED` unless independent scientific validation exists. An old ODB interface scan cannot become candidate-solve evidence.

AbqJobPilot identities (`project_id`, `queue_id`, `job_name`, `INP` and `ODB`) are separate from Hub task IDs and Run IDs. Candidate identity is `SPIO_R008_Q200_N010_Candidate`, with one isolated input/work directory. A Queue record does not exist in this Run.
