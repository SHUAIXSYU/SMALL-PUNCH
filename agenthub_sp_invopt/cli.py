"""JSON CLI for the local SP-InvOpt AgentHub ledger.

This is a trusted-local-process interface. A session ID is a routing handle,
not an operating-system security credential.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hub import Hub, HubError


def _json_file(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Existing or new SP-InvOpt SQLite file")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("register"); p.add_argument("--role", required=True, choices=("MAIN", "AGENTHUB", "CAE", "ODB")); p.add_argument("--name", required=True)
    p = sub.add_parser("create"); p.add_argument("--actor", required=True); p.add_argument("--role", required=True, choices=("MAIN", "CAE", "ODB")); p.add_argument("--kind", required=True); p.add_argument("--payload-file", required=True); p.add_argument("--key", required=True); p.add_argument("--depends", action="append", default=[])
    p = sub.add_parser("approve"); p.add_argument("--actor", required=True); p.add_argument("--task", required=True); p.add_argument("--action", required=True, choices=("generate_inp", "verify_inp", "enqueue", "start_solver", "recover_retry"))
    p = sub.add_parser("inbox"); p.add_argument("--session", required=True)
    p = sub.add_parser("messages"); p.add_argument("--session", required=True)
    p = sub.add_parser("claim"); p.add_argument("--session", required=True); p.add_argument("--task", required=True); p.add_argument("--key", required=True)
    p = sub.add_parser("heartbeat"); p.add_argument("--lease-file", required=True)
    p = sub.add_parser("artifact"); p.add_argument("--lease-file", required=True); p.add_argument("--path", required=True); p.add_argument("--provenance-file", required=True); p.add_argument("--version", default="1")
    p = sub.add_parser("finish"); p.add_argument("--lease-file", required=True); p.add_argument("--result-file", required=True); p.add_argument("--evidence-state", default="RECORDED"); p.add_argument("--science-state", default="NOT_EVALUATED")
    p = sub.add_parser("fail"); p.add_argument("--lease-file", required=True); p.add_argument("--code", required=True); p.add_argument("--detail", required=True); p.add_argument("--retryable", action="store_true")
    p = sub.add_parser("recover"); p.add_argument("--actor", required=True); p.add_argument("--task", required=True); p.add_argument("--worker-stopped-confirmed", action="store_true")
    p = sub.add_parser("message"); p.add_argument("--sender", required=True); p.add_argument("--task", required=True); p.add_argument("--to", required=True, choices=("MAIN", "CAE", "ODB")); p.add_argument("--body-file", required=True); p.add_argument("--key", required=True)
    p = sub.add_parser("task"); p.add_argument("--task", required=True)
    p = sub.add_parser("diagnostics"); p.add_argument("--task", required=True)
    sub.add_parser("audit")
    args = parser.parse_args(argv)
    hub = Hub(args.db)
    try:
        cmd = args.command
        if cmd == "register": result = hub.register(args.role, args.name)
        elif cmd == "create": result = hub.create_task(args.actor, args.role, args.kind, _json_file(args.payload_file), args.key, args.depends)
        elif cmd == "approve": hub.approve(args.task, args.actor, args.action); result = {"approved": args.action, "task_id": args.task}
        elif cmd == "inbox": result = hub.inbox(hub.session_identity(args.session))
        elif cmd == "messages": result = hub.poll_messages(hub.session_identity(args.session))
        elif cmd == "claim": result = hub.claim(args.task, hub.session_identity(args.session), args.key)
        elif cmd == "heartbeat": result = {"lease_until": hub.heartbeat(_json_file(args.lease_file))}
        elif cmd == "artifact":
            lease = _json_file(args.lease_file)
            result = hub.artifact(lease["task_id"], lease["agent_id"], args.path, _json_file(args.provenance_file), version=args.version)
        elif cmd == "finish":
            hub.finish(_json_file(args.lease_file), _json_file(args.result_file), evidence_state=args.evidence_state, science_state=args.science_state)
            result = {"execution_state": "COMPLETED"}
        elif cmd == "fail": result = {"failure_id": hub.fail(_json_file(args.lease_file), args.code, args.detail, retryable=args.retryable), "execution_state": "FAILED"}
        elif cmd == "recover":
            hub.recover(args.task, args.actor, worker_stopped_confirmed=args.worker_stopped_confirmed)
            result = {"execution_state": "PENDING", "task_id": args.task}
        elif cmd == "message": result = hub.message(args.task, args.sender, args.to, _json_file(args.body_file), args.key)
        elif cmd == "task": result = hub.task(args.task)
        elif cmd == "diagnostics": result = hub.diagnostics(args.task)
        else: result = {"audit_hash_chain_valid": hub.verify_chain()}
        _print(result)
        return 0
    except (HubError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
