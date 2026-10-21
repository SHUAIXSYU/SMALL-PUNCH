# SP-InvOpt AgentHub CLI

This CLI is a thin JSON interface to `hub.py`. It uses only the selected Python's standard library and the same SQLite file as the Python API. Every invocation is a separate process. It does not start Abaqus, enqueue a job, or notify another Codex chat.

```powershell
$Py = 'D:\XianLab\envs\torch-gpu\python.exe'
$Cli = 'E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\cli.py'
$Db = 'E:\Projects\SMALL-PUNCH\agenthub_sp_invopt\runtime\sp_invopt.sqlite3'
& $Py -B $Cli --db $Db audit
& $Py -B $Cli --db $Db register --role MAIN --name main-local
& $Py -B $Cli --db $Db register --role AGENTHUB --name runtime-maintainer
& $Py -B $Cli --db $Db register --role CAE --name cae-local
& $Py -B $Cli --db $Db register --role ODB --name odb-local
```

Save the returned `agent_id` and `session_id` in the actor's own workspace. JSON task payloads and messages are data; no command is executed from them.

`AGENTHUB` is the runtime maintenance identity. Its sessions are stored separately from research worker sessions and cannot create, claim, approve, or complete scientific tasks. MAIN owns research decisions; CAE and ODB perform assigned tasks.

## MAIN

```powershell
& $Py -B $Cli --db $Db create --actor 'MAIN:main-local' --role CAE --kind prepare_inp --payload-file 'E:\Projects\SMALL-PUNCH\path\request.json' --key 'unique-study-task-v1'
& $Py -B $Cli --db $Db approve --actor 'MAIN:main-local' --task '<task-id>' --action generate_inp
& $Py -B $Cli --db $Db message --sender 'MAIN:main-local' --task '<task-id>' --to CAE --body-file 'E:\Projects\SMALL-PUNCH\path\message.json' --key 'unique-message-v1'
& $Py -B $Cli --db $Db messages --session '<main-session-id>'
& $Py -B $Cli --db $Db task --task '<task-id>'
```

Use `--depends '<parent-task-id>'` on `create` to require a completed parent. A repeated task key returns the existing task when the role, kind, and payload match. A distinct approval is needed for each action; approval does not execute that action. The Hub has no queue or Solver executor.

## CAE and ODB

```powershell
& $Py -B $Cli --db $Db inbox --session '<worker-session-id>'
& $Py -B $Cli --db $Db messages --session '<worker-session-id>'
& $Py -B $Cli --db $Db claim --session '<worker-session-id>' --task '<task-id>' --key 'worker-attempt-v1'
```

Save the claim response as a JSON lease file before work. Keep the lease file private: it contains the claim token. Call `heartbeat --lease-file '<lease.json>'` while working. Record each small output with `artifact --lease-file '<lease.json>' --path '<output-file>' --version 'generator-v1' --provenance-file '<provenance.json>'`, then call `finish --lease-file '<lease.json>' --result-file '<result.json>' --evidence-state RECORDED --science-state NOT_EVALUATED`. Artifacts record an absolute path, version and SHA-256. Do not put an actual ODB or large Solver output in Git.

On an actual failure, use `fail --lease-file '<lease.json>' --code '<stable-code>' --detail '<diagnosis>'`. The task becomes `FAILED`; `diagnostics --task '<task-id>'` returns the retained failure record. Do not call `finish` with a fabricated zero error.

`poll.py` is a bounded alternative for inbox polling and atomic claim. It is a local Python process, not a Codex conversation wakeup. A separate Codex chat must actually execute the poll/claim to count as cross-chat receipt.

## Recovery and trust boundary

Expired leases become `RECOVERY_REQUIRED`. MAIN must check that the worker has stopped and preserve diagnostic evidence, grant `recover_retry` for that task, then use `recover --actor '<main-agent-id>' --task '<task-id>' --worker-stopped-confirmed`. The flag records MAIN's assertion; the Hub cannot inspect an arbitrary worker process. The CLI has no queue-write or Solver-start command.

The database and session IDs are on the same local filesystem. The role checks prevent accidental cross-role operations by cooperative actors; this is not an adversarial authentication boundary for an untrusted process with direct database access. Keep the SQLite file and lease files in a trusted workspace and do not edit the database directly.
