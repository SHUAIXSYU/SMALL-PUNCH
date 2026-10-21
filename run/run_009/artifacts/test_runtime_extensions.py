"""Focused failure, version, and authorization checks for the shared Hub API."""
from __future__ import annotations

import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "agenthub_sp_invopt"))
from hub import Hub, HubError


class RuntimeExtensionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent / "private")
        self.root = Path(self.tmp.name)
        self.hub = Hub(self.root / "hub.sqlite3", lease_seconds=2)
        self.main = self.hub.register("MAIN", "controller")
        self.cae = self.hub.register("CAE", "writer")
        self.odb = self.hub.register("ODB", "reader")

    def tearDown(self):
        self.tmp.cleanup()

    def task(self, key="case", depends=()):
        return self.hub.create_task(self.main["agent_id"], "CAE", "mock", {"simulation": True}, key, depends)["task_id"]

    def test_artifact_version_is_explicit_and_stable(self):
        task = self.task()
        lease = self.hub.claim(task, self.cae, "claim")
        output = self.root / "simulated.txt"
        output.write_text("SIMULATED_ONLY", encoding="utf-8")
        record = self.hub.artifact(task, self.cae["agent_id"], output, {"simulation": True}, version="mock-v1")
        self.assertEqual(record["version"], "mock-v1")
        self.assertEqual(self.hub.artifact(task, self.cae["agent_id"], output, {"simulation": True}, version="mock-v1")["artifact_id"], record["artifact_id"])
        with self.assertRaisesRegex(HubError, "VERSION_CONFLICT"):
            self.hub.artifact(task, self.cae["agent_id"], output, {"simulation": True}, version="mock-v2")
        self.hub.finish(lease, {"simulation": True}, science_state="NOT_EVALUATED")

    def test_failure_diagnosis_persists_without_zero_error(self):
        task = self.task()
        lease = self.hub.claim(task, self.cae, "claim")
        failure = self.hub.fail(lease, "SIMULATED_READ_ERROR", "fixture deliberately failed", retryable=False)
        self.assertEqual(self.hub.task(task)["execution_state"], "FAILED")
        self.assertEqual(self.hub.task(task)["science_state"], "NOT_EVALUATED")
        self.assertEqual(self.hub.diagnostics(task)[0]["failure_id"], failure)
        with self.assertRaisesRegex(HubError, "LEASE_INVALID"):
            self.hub.finish(lease, {"error": 0})

    def test_dependency_change_conflicts_with_task_key(self):
        parent = self.task("parent")
        child = self.task("child", (parent,))
        self.assertIsNotNone(child)
        with self.assertRaisesRegex(HubError, "IDEMPOTENCY_CONFLICT"):
            self.task("child", ())

    def test_same_role_but_not_task_holder_cannot_record_evidence_or_message(self):
        task = self.task()
        other = self.hub.register("CAE", "other")
        lease = self.hub.claim(task, self.cae, "claim")
        output = self.root / "simulated.txt"
        output.write_text("SIMULATED_ONLY", encoding="utf-8")
        with self.assertRaisesRegex(HubError, "ARTIFACT_LEASE_REQUIRED"):
            self.hub.artifact(task, other["agent_id"], output, {"simulation": True})
        with self.assertRaisesRegex(HubError, "MESSAGE_TASK_DENIED"):
            self.hub.message(task, other["agent_id"], "MAIN", {"simulation": True}, "wrong-sender")
        self.hub.finish(lease, {"simulation": True}, science_state="NOT_EVALUATED")

    def test_cli_failure_diagnostics_roundtrip(self):
        task = self.task()
        lease = self.hub.claim(task, self.cae, "claim")
        lease_file = self.root / "lease.json"
        lease_file.write_text(json.dumps(lease), encoding="utf-8")
        cli = ROOT / "agenthub_sp_invopt" / "cli.py"
        base = [sys.executable, "-B", str(cli), "--db", str(self.hub.path)]
        failed = subprocess.run(base + ["fail", "--lease-file", str(lease_file), "--code", "MOCK_FAILURE", "--detail", "diagnostic retained"], capture_output=True, text=True, check=True)
        failure_id = json.loads(failed.stdout)["failure_id"]
        queried = subprocess.run(base + ["diagnostics", "--task", task], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(queried.stdout)[0]["failure_id"], failure_id)

    def test_message_dedup_cannot_change_sender_or_recipient(self):
        task = self.task()
        lease = self.hub.claim(task, self.cae, "claim")
        self.hub.message(task, self.main["agent_id"], "CAE", {"simulation": True}, "same-key")
        with self.assertRaisesRegex(HubError, "MESSAGE_IDEMPOTENCY_CONFLICT"):
            self.hub.message(task, self.cae["agent_id"], "MAIN", {"simulation": True}, "same-key")
        self.hub.finish(lease, {"simulation": True}, science_state="NOT_EVALUATED")

    def test_agenthub_maintenance_identity_has_no_research_authority(self):
        maintainer = self.hub.register("AGENTHUB", "runtime-maintainer")
        self.assertEqual(self.hub.session_identity(maintainer["session_id"])["role"], "AGENTHUB")
        task = self.task()
        with self.assertRaisesRegex(HubError, "CREATE_DENIED"):
            self.hub.create_task(maintainer["agent_id"], "CAE", "forbidden", {}, "maintenance-create")
        with self.assertRaisesRegex(HubError, "CLAIM_DENIED"):
            self.hub.claim(task, maintainer, "maintenance-claim")
        with self.assertRaisesRegex(HubError, "APPROVAL_DENIED"):
            self.hub.approve(task, maintainer["agent_id"], "generate_inp")

    def test_recovery_requires_main_and_explicit_approval(self):
        task = self.task()
        lease = self.hub.claim(task, self.cae, "claim", now=10)
        with self.assertRaisesRegex(HubError, "RECOVERY_REQUIRED"):
            self.hub.claim(task, self.cae, "later", now=lease["lease_until"] + 1)
        with self.assertRaisesRegex(HubError, "RECOVERY_DENIED"):
            self.hub.recover(task, self.cae["agent_id"], worker_stopped_confirmed=True)
        with self.assertRaisesRegex(HubError, "TASK_APPROVAL_REQUIRED"):
            self.hub.recover(task, self.main["agent_id"], worker_stopped_confirmed=True)
        self.hub.approve(task, self.main["agent_id"], "recover_retry")
        self.hub.recover(task, self.main["agent_id"], worker_stopped_confirmed=True)
        self.assertEqual(self.hub.claim(task, self.cae, "after-recovery")["generation"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
