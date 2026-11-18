# Installed Runner abnormal-stop audit

Result: **AUTO_STOP_UNAVAILABLE**. Examined local installation `D:\Projects\abqjobpilot`, application 0.2.2, clean Git HEAD `7012133e7cc0176bb3e56fc24d7154ee3b90bb81`. This is a local code audit, not a GitHub-main assumption. Source hashes are in runner_fake_tests.json; installation/settings evidence is in admission.json.

No live Python GUI process was observed in the process census. Consequently this audit identifies the installed GUI/Runner code, not a currently loaded GUI window. Before manual execution the user must open this installation and the specified SP-InvOpt Project. No GUI interaction was performed.

| Question | Observed implementation |
| --- | --- |
| Datacheck failure | runner_core.py:292–314 returns from the current job before Full Analysis; outer loop ignores the returned result and continues. |
| Full Analysis failure | runner_core.py:329–353 returns an unsuccessful result; outer loop does not inspect it. Next queued job is eligible. |
| COMPLETED_WITH_WARNINGS | No batch-stop branch. Warnings do not block subsequent jobs. |
| Stop After Current Job | runner_core.py:400–417 sets a boolean and tests it only at the next loop boundary. A request arriving after that check can allow the next selected job to execute. start() also resets a preexisting stop flag. This is not atomic single-step approval. |
| GUI Start Queue | gui_app.py:2215–2233 counts all QUEUED/DATACHECK_OK records, confirms the entire executable queue, and starts the runner; filters/selection do not restrict execution. |
| True review-before-next | No per-job acknowledgement gate exists in this loop. Manual timely stop can leave later jobs queued, but is not a reliable automatic interlock. |
| Exit/interruption | Unselected jobs remain persisted QUEUED. Normal stop preserves them; an exception exits the loop. Runner thread is daemon=True; closing/crashing GUI is not a safe Solver stop and may leave current process ownership/recovery uncertainty. Do not close GUI as a control method or clear locks. |

Seven deterministic in-memory checks exercised installed code with execution, queue reads/writes and live-status writes replaced by fakes. Datacheck failure, Full failure and warning cases each continued through four fake jobs. Timely manual stop left three queued; a stop deliberately inserted after the boundary check still permitted the selected job. A synthetic exception left unselected jobs queued. Failed datacheck skipped the same job's Full phase. No actual Runner.start, Solver, subprocess launch or runtime mutation was used by these tests. These tests establish control-flow behavior, not real GUI timing or crash recovery correctness.

The user explicitly permits all four enqueue operations even without fail-stop. This supersedes the prior run_020 suggestion to release jobs individually, but does not create an automatic guard. Clicking Start Queue may execute all four consecutively, including after failures/warnings. Recommend attended manual monitoring; if guaranteed review between jobs is required, establish and verify a controlled single-job execution mechanism before starting. This Run does not modify the external software or queue order to implement such a mechanism.

Execution/retry authority remains exactly one Datacheck+Full attempt per frozen Job, user GUI start only, no automatic retry, no fifth Job or center recompute. Solver outcomes and subsequent ODB/scientific analysis have not yet occurred.
