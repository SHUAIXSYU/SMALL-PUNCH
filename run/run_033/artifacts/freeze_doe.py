"""Freeze 14 SPT-only DOE coordinates before any candidate INP generation."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[3]
A = ROOT / "run/run_033/artifacts"
DESIGN = A / "doe_design.json"
LOG_DENOM = math.log(1000.0 / 150.0)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def xy(sigma_y_mpa, n):
    return (math.log(sigma_y_mpa / 150.0) / LOG_DENOM, (n - 0.02) / 0.48)


def nearest(points, other):
    return float(np.linalg.norm(points[:, None, :] - other[None, :, :], axis=2).min())


def minimum_pair_distance(points):
    return min(float(np.linalg.norm(points[i] - points[j]))
               for i in range(len(points)) for j in range(i + 1, len(points)))


def main():
    assert not DESIGN.exists(), "DOE already frozen; do not regenerate"
    assert read(ROOT / "run/run_033/artifacts/private/i02_execution_audit.json")["status"] == "I02_EXECUTION_IDENTITY_PASS_WITH_WARNINGS"
    batch_path = ROOT / "run/run_030/artifacts/prepared_batch.json"
    batch = read(batch_path)
    assert sha(batch_path) == read(ROOT / "run/run_030/checkpoints/completion.json")["prepared_batch_sha256"]
    assert batch["numeric_version"] == "run030-standard-m0025-hollomon-v1"
    assert batch["loss_version"] == "run017-exploratory-fd-v1"
    low_path = ROOT / "run/run_022/artifacts/private/analysis/loss_results.json"
    low_data = read(low_path)
    assert low_data["contract"] == batch["loss_version"]
    low = next(x for x in low_data["rows"] if x["point_id"] == "L04")
    assert low["sigma_y_mpa"] == 200.0 and low["n"] == 0.124
    assert math.isclose(low["loss"], 0.031024866128661885, rel_tol=1e-12)
    assert low["mode"] == "PROVISIONAL"

    # Prior FE inputs are used only to avoid duplicate or crowded coordinates.
    # No sealed tensile data and no new I02 ODB score enters the design.
    prior_physical = [(p["sigma_y_mpa"], p["n"]) for p in batch["points"]]
    prior_physical += [(200.0, 0.1), (387.2983346207417, 0.26),
                       (181.9007788573887, 0.1), (219.9001029641563, 0.1),
                       (200.0, 0.076), (200.0, 0.124)]
    prior = np.array(list(dict.fromkeys(xy(*p) for p in prior_physical)), dtype=float)
    assert prior.shape[1] == 2

    # First Latin hypercube seed satisfying fixed, predeclared spacing rules.
    chosen_seed = None
    global_points = None
    for seed in range(3301, 4301):
        candidate = qmc.LatinHypercube(d=2, scramble=True, seed=seed).random(n=7)
        if nearest(candidate, prior) >= 0.08 and minimum_pair_distance(candidate) >= 0.16:
            chosen_seed = seed
            global_points = candidate
            break
    assert global_points is not None, "No global design satisfies frozen spacing rules"
    # The local box is centered on the prior SPT low-Loss vicinity with broad
    # margins; it is exploratory and is not a tensile-derived material prior.
    local_box = ((0.02, 0.45), (0.02, 0.44))
    sobol = qmc.Sobol(d=2, scramble=True, seed=3302).random_base2(m=13)
    candidates = np.column_stack((local_box[0][0] + sobol[:, 0] * (local_box[0][1] - local_box[0][0]),
                                  local_box[1][0] + sobol[:, 1] * (local_box[1][1] - local_box[1][0])))
    occupied = np.vstack((prior, global_points))
    local_points = []
    local_nearest = []
    for _ in range(7):
        distance = np.linalg.norm(candidates[:, None, :] - occupied[None, :, :], axis=2).min(axis=1)
        index = int(np.argmax(distance))  # first in Sobol order resolves ties
        chosen = candidates[index]
        local_points.append(chosen)
        local_nearest.append(float(distance[index]))
        occupied = np.vstack((occupied, chosen))
        candidates = np.delete(candidates, index, axis=0)
    local_points = np.array(local_points)
    assert min(local_nearest) >= 0.055, "Local DOE too crowded; stop before generation"
    all_new = np.vstack((global_points, local_points))
    assert nearest(all_new, prior) >= 0.055
    assert minimum_pair_distance(all_new) >= 0.055
    assert np.all((all_new > 0) & (all_new < 1))

    global_entries = []
    local_entries = []
    for i, p in enumerate(global_points, 1):
        x, y = map(float, p)
        sigma = 150.0 * math.exp(x * LOG_DENOM)
        n = 0.02 + 0.48 * y
        job = f"SPIO_R033_D{i:02d}_G"
        global_entries.append({"point_id": f"D{i:02d}", "region": "GLOBAL",
                               "x": x, "y": y, "sigma_y_mpa": sigma, "n": n,
                               "job_name": job,
                               "inp_path": f"run/run_033/artifacts/candidates/{job}/{job}.inp",
                               "parameters_path": f"run/run_033/artifacts/candidates/{job}/parameters.json",
                               "working_dir": f"run/run_033/artifacts/solver/{job}",
                               "expected_odb": f"run/run_033/artifacts/solver/{job}/{job}.odb"})
    for i, p in enumerate(local_points, 8):
        x, y = map(float, p)
        sigma = 150.0 * math.exp(x * LOG_DENOM)
        n = 0.02 + 0.48 * y
        job = f"SPIO_R033_D{i:02d}_L"
        local_entries.append({"point_id": f"D{i:02d}", "region": "LOCAL",
                              "x": x, "y": y, "sigma_y_mpa": sigma, "n": n,
                              "job_name": job,
                              "inp_path": f"run/run_033/artifacts/candidates/{job}/{job}.inp",
                              "parameters_path": f"run/run_033/artifacts/candidates/{job}/parameters.json",
                              "working_dir": f"run/run_033/artifacts/solver/{job}",
                              "expected_odb": f"run/run_033/artifacts/solver/{job}/{job}.odb"})
    new_points = global_entries + local_entries
    assert len({p["job_name"] for p in new_points}) == 14
    existing_names = {p["job_name"] for p in batch["points"]}
    assert not existing_names.intersection(p["job_name"] for p in new_points)
    for p in new_points:
        assert not (ROOT / p["inp_path"]).exists()
        assert not (ROOT / p["parameters_path"]).exists()
        assert not (ROOT / p["working_dir"]).exists()

    # Batch order is fixed now; no per-Job result changes it later.
    batch_order = [p["point_id"] for p in batch["points"][2:]]
    batch_order += [item for pair in zip(global_entries, local_entries)
                    for item in (pair[0]["point_id"], pair[1]["point_id"])]
    assert len(batch_order) == len(set(batch_order)) == 20
    doc = {"version": "run033-twenty-doe-design-v1",
           "frozen_at": datetime.now().astimezone().isoformat(),
           "authorization": "User explicitly approved exactly 20 new Jobs and one GUI-started serial batch",
           "research_scope": "SPT-only exploratory DOE; no BO/DE/RL",
           "numeric_version": batch["numeric_version"], "loss_version": batch["loss_version"],
           "run030_batch_sha256": sha(batch_path),
           "run022_prior_loss_file_sha256": sha(low_path),
           "low_loss_basis": {"point": "run022 L04", "sigma_y_mpa": 200.0,
                              "n": 0.124, "provisional_loss": low["loss"],
                              "note": "Observed SPT-only vicinity; not true material parameters"},
           "bounds": {"sigma_y_mpa": [150.0, 1000.0], "n": [0.02, 0.50],
                      "status": "EXPLORATORY_ENGINEERING_BOUNDS"},
           "normalization": {"x": "ln(sigma_y_mpa/150)/ln(1000/150)",
                             "y": "(n-0.02)/0.48"},
           "global_method": {"algorithm": "first_seed_satisfying_7_stratum_scipy_LatinHypercube",
                             "seed_search_inclusive": [3301, 4300],
                             "chosen_seed": chosen_seed, "scramble": True,
                             "min_distance_to_prior": 0.08,
                             "min_pair_distance": 0.16,
                             "actual_nearest_prior": nearest(global_points, prior),
                             "actual_min_pair": minimum_pair_distance(global_points)},
           "local_method": {"algorithm": "greedy_farthest_first_8192_scrambled_Sobol_candidates",
                            "seed": 3302, "local_box_xy": local_box,
                            "candidate_order_tie_break": "first_Sobol_index",
                            "min_allowed_distance": 0.055,
                            "actual_sequential_nearest": local_nearest,
                            "basis": "run022 low-Loss vicinity with broad margins; no I02 score used"},
           "minimum_new_pair_distance": minimum_pair_distance(all_new),
           "minimum_new_to_prior_distance": nearest(all_new, prior),
           "scipy_version": __import__("scipy").__version__,
           "numpy_version": np.__version__,
           "existing_frozen": [{"point_id": p["point_id"], "job_name": p["job_name"],
                                "inp_path": p["inp_path"], "inp_sha256": p["inp_sha256"],
                                "sigma_y_mpa": p["sigma_y_mpa"], "n": p["n"]}
                               for p in batch["points"][2:]],
           "new_points": new_points, "batch_order": batch_order,
           "sealed_tensile_data_used": False,
           "selection_does_not_depend_on_new_batch_results": True}
    with DESIGN.open("x", encoding="utf-8") as stream:
        json.dump(doc, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "DOE_FROZEN", "sha256": sha(DESIGN),
                      "global_seed": chosen_seed,
                      "global_nearest": doc["global_method"]["actual_nearest_prior"],
                      "local_min": min(local_nearest),
                      "batch_order": batch_order}, ensure_ascii=False))


if __name__ == "__main__":
    main()
