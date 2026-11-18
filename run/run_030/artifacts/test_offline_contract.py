"""Independent, non-Solver checks of frozen initial design and source identity."""
import hashlib
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
A = ROOT / "run/run_030/artifacts"
sys.dont_write_bytecode = True


def read(name):
    return json.loads((A / name).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FrozenPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = read("parameter_design.json")
        cls.model = read("model_contract.json")
        cls.loss = read("loss_contract_binding.json")
        cls.budget = read("budget_protocol.json")

    def test_eight_unique_balanced_points(self):
        points = self.design["points"]
        self.assertEqual(len(points), 8)
        self.assertEqual([p["region"] for p in points], ["GLOBAL", "LOCAL"] * 4)
        self.assertEqual(len({(p["x"], p["y"]) for p in points}), 8)
        self.assertEqual(len({p["job_name"] for p in points}), 8)
        self.assertEqual(len({p["inp_path"] for p in points}), 8)
        self.assertEqual(len({p["working_dir"] for p in points}), 8)

    def test_physical_parameters_round_trip(self):
        for p in self.design["points"]:
            self.assertTrue(150 <= p["sigma_y_mpa"] <= 1000)
            self.assertTrue(0.02 <= p["n"] <= 0.5)
            self.assertAlmostEqual(math.log(p["sigma_y_mpa"] / 150) / math.log(1000 / 150), p["x"], places=14)
            self.assertAlmostEqual((p["n"] - 0.02) / 0.48, p["y"], places=14)

    def test_stratified_global_and_targeted_local(self):
        g = [p for p in self.design["points"] if p["region"] == "GLOBAL"]
        l = [p for p in self.design["points"] if p["region"] == "LOCAL"]
        self.assertEqual([p["x"] for p in g], [0.125, 0.375, 0.625, 0.875])
        self.assertEqual([p["y"] for p in g], [0.875, 0.375, 0.625, 0.125])
        self.assertTrue(all(0.12 <= p["x"] <= 0.30 and 0.16 <= p["y"] <= 0.32 for p in l))

    def test_source_and_numerical_contract(self):
        source = ROOT / self.model["source_inp"]
        self.assertEqual(sha(source), self.model["source_inp_sha256"])
        text = source.read_text(encoding="utf-8")
        self.assertEqual(text.count("*Static\n0.001, 1., 1e-12, 0.0025"), 1)
        self.assertEqual(text.count("inc=999999"), 1)
        self.assertEqual(self.model["static_step"]["maximum_increment"], 0.0025)
        self.assertEqual(self.model["resources"], {"cpus": 14, "gpus": 0, "datacheck": True, "full_analysis": True})

    def test_frozen_loss_identity(self):
        for field, expected in (("loss_identity_path", "loss_identity_sha256"),
                                ("config_path", "config_sha256"),
                                ("target_path", "target_sha256"),
                                ("implementation_path", "implementation_sha256")):
            self.assertEqual(sha(ROOT / self.loss[field]), self.loss[expected])
        self.assertEqual(self.loss["version"], "run017-exploratory-fd-v1")
        self.assertEqual(self.loss["points"], 241)
        self.assertEqual(self.loss["F_ref_n"], 1428.9)
        self.assertEqual(self.loss["window_m"], [0, 0.0012])

    def test_budget_and_authority(self):
        self.assertEqual(self.budget["stage_a"]["count"], 8)
        self.assertEqual(self.budget["stage_b"]["new_fe_cap"], 4)
        self.assertEqual(self.budget["stage_c"]["new_fe_cap"], 4)
        self.assertEqual(self.budget["total_unique_new_fe_cap"], 16)
        self.assertEqual(self.budget["authorized_now"], 0)
        self.assertEqual(self.budget["automatic_retries"], 0)
        self.assertEqual(self.design["authorized_enqueues"], 0)
        self.assertEqual(self.design["authorized_solver_jobs"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
