# MAIN / CAE / ODB role startup

Use the same repository root, Hub database and role names. Each invocation opens a distinct session. The current `poll.py` prints one claimed task and exits; it does not run arbitrary task text. A worker reads the structured task, verifies its task-scoped approval and inputs, performs only that role's operation, then records artifact hashes and a structured result through `Hub`. Do not infer permission from an approval field in a message.

## MAIN — research controller and authorization

MAIN alone creates tasks and approvals. Record the objective, exact input paths/hashes, expected evidence, dependency IDs and science boundary in the payload. Use separate action approvals for generating an INP, queueing, solver start and recovery/retry. MAIN receives CAE/ODB results by polling its persistent inbox and reviews hashes, statuses and limitations. A status of `COMPLETED` never means scientific validity.

## CAE — candidate INP generation

Run the bounded poll command in [protocol.md](protocol.md) with `--role CAE`. Check the claimed task ID, generation, dependency and matching `generate_inp` approval. Write a uniquely named INP only in that task's isolated work directory. Record source file/hash, material interpretation, generator version and output SHA-256. Do not enqueue or start a Solver; those actions require distinct authorization and no such executor exists in the current Hub.

For the run_008 example, `run/run_008/artifacts/generate_candidate_inp.py` references historical `CAE/Models/Sanity/Job-1.inp` and replaces only its `Q200N01 *Plastic` block in a new file. It does not establish equivalence between that historical INP and the currently edited CAE database.

## ODB — extraction and diagnostics

Poll with `--role ODB`. Verify the explicit task dependency and input ODB identity. Use the Abaqus-bundled Python/API in a read-only process; do not copy, edit, or open the ODB for write. Save only small structured extraction metadata in the Run and register the original ODB path/hash as provenance. Keep `execution_status`, `evidence_status`, and `science_status` separate. Historical files may verify an interface; they cannot represent a new candidate solve.

## Manual cross-chat handoff

The local poller is verified across independent local Python processes. It does not wake, address, or confirm a separate Codex chat. Until a recipient Codex chat itself polls and claims a task, copy the task ID and bounded instructions into a manual Handoff and wait for that chat's explicit result. Do not label a DB message as delivered to a Codex session.
