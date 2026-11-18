"""Offline tests for reproducibility, frozen bounds and failure treatment."""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

import numpy as np

from pilot import (FAILED_DISTANCE, MIN_BATCH_DISTANCE, MIN_EXISTING_DISTANCE,
                   normalize, physical, propose_bo, propose_de, select_de_population,
                   validate_dataset)

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
DATA=ROOT/"run/run_040/artifacts/private/initial_dataset.json"
FROZEN=ROOT/"run/run_040/artifacts/private/candidate_manifest.json"


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data=json.loads(DATA.read_text(encoding="utf-8"))
        cls.good=data["valid"]
        cls.bad=data["invalid"]

    def test_shared_dataset_and_contract(self):
        x,y,bad=validate_dataset(self.good,self.bad)
        self.assertEqual((x.shape,y.shape,bad.shape),((19,2),(19,),(3,2)))
        self.assertEqual({r["point_id"] for r in self.bad},{"D07","D09","D10"})
        self.assertTrue(all(r["loss"] is None for r in self.bad))
        self.assertEqual({r["numeric_version"] for r in self.good+self.bad},{"run030-standard-m0025-hollomon-v1"})
        self.assertEqual({r["loss_version"] for r in self.good+self.bad},{"run017-exploratory-fd-v1"})

    def test_physical_normalization_round_trip(self):
        for row in self.good+self.bad:
            sigma,n=physical(normalize(row["sigma_y_mpa"],row["n"]))
            self.assertAlmostEqual(sigma,row["sigma_y_mpa"],places=10)
            self.assertAlmostEqual(n,row["n"],places=14)
        with self.assertRaises(ValueError): normalize(149.999,.2)
        with self.assertRaises(ValueError): physical(np.array([.4,1.01]))

    def test_null_not_trainable(self):
        damaged=[dict(r) for r in self.bad]
        damaged[0]["loss"]=0.0
        with self.assertRaises(ValueError): validate_dataset(self.good,damaged)
        damaged[0]["loss"]=None
        damaged[1]["point_id"]="D07"
        with self.assertRaises(ValueError): validate_dataset(self.good,damaged)

    def test_de_partial_generation(self):
        population=select_de_population(self.good)
        self.assertEqual(len(population),8)
        self.assertEqual(population[0]["point_id"],"D01")
        frozen=json.loads(FROZEN.read_text(encoding="utf-8"))
        bo_xy=[np.array([r["x"],r["y"]]) for r in frozen["points"] if r["algorithm"]=="BO"]
        generated=propose_de(self.good,self.bad,other_branch=bo_xy)
        self.assertEqual(generated["generated_trials"],4)
        self.assertEqual(generated["full_generation_trials"],8)
        self.assertEqual(generated["population_ids"],[r["point_id"] for r in population])
        expected=[r for r in frozen["points"] if r["algorithm"]=="DE"]
        for p,q in zip(generated["proposals"],expected):
            self.assertEqual(p["sigma_y_mpa"],q["sigma_y_mpa"])
            self.assertEqual(p["n"],q["n"])
            self.assertFalse(p["depends_on_new_fe_observation"])

    def test_bo_batch_reproducibility_and_candidate_separation(self):
        frozen=json.loads(FROZEN.read_text(encoding="utf-8"))
        expected=[r for r in frozen["points"] if r["algorithm"]=="BO"]
        generated=propose_bo(self.good,self.bad)
        self.assertEqual(len(generated["proposals"]),4)
        self.assertEqual(generated["method"],"batch_bo_greedy_kriging_believer_ei")
        self.assertTrue(all(not r["depends_on_new_fe_observation"] for r in generated["proposals"]))
        for p,q in zip(generated["proposals"],expected):
            self.assertEqual(p["sigma_y_mpa"],q["sigma_y_mpa"])
            self.assertEqual(p["n"],q["n"])
        existing,bad_loss,bad=validate_dataset(self.good,self.bad)
        xy=np.array([[r["x"],r["y"]] for r in frozen["points"]])
        self.assertEqual(xy.shape,(8,2))
        self.assertTrue(np.all((xy>=0)&(xy<=1)))
        self.assertGreaterEqual(float(np.min(np.linalg.norm(xy[:,None,:]-existing[None,:,:],axis=2))),MIN_EXISTING_DISTANCE)
        self.assertGreaterEqual(float(np.min(np.linalg.norm(xy[:,None,:]-bad[None,:,:],axis=2))),FAILED_DISTANCE)
        distances=np.linalg.norm(xy[:,None,:]-xy[None,:,:],axis=2)
        distances[np.diag_indices(8)]=math.inf
        self.assertGreaterEqual(float(distances.min()),MIN_BATCH_DISTANCE)
        self.assertEqual(len({r["job_name"] for r in frozen["points"]}),8)


if __name__=="__main__":
    unittest.main(verbosity=2)
