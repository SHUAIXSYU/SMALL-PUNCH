"""Offline, deterministic BO/DE pilot proposals; no Abaqus or queue interface."""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm, qmc
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

SIGMA_BOUNDS_MPA = (150.0, 1000.0)
N_BOUNDS = (0.02, 0.50)
SEED = 20261025
MIN_EXISTING_DISTANCE = 0.035
MIN_BATCH_DISTANCE = 0.07
FAILED_DISTANCE = 0.04
EI_XI_LOG1P = 0.005
DE_F = 0.7
DE_CR = 0.9
DE_POPULATION = 8


def normalize(sigma_y_mpa: float, n: float) -> np.ndarray:
    if not (SIGMA_BOUNDS_MPA[0] <= sigma_y_mpa <= SIGMA_BOUNDS_MPA[1]
            and N_BOUNDS[0] <= n <= N_BOUNDS[1]):
        raise ValueError("PARAMETER_OUTSIDE_FROZEN_BOUNDS")
    return np.array([math.log(sigma_y_mpa / SIGMA_BOUNDS_MPA[0]) /
                     math.log(SIGMA_BOUNDS_MPA[1] / SIGMA_BOUNDS_MPA[0]),
                     (n - N_BOUNDS[0]) / (N_BOUNDS[1] - N_BOUNDS[0])], dtype=float)


def physical(xy: np.ndarray) -> tuple[float, float]:
    xy = np.asarray(xy, dtype=float)
    if xy.shape != (2,) or not np.all(np.isfinite(xy)) or np.any(xy < 0) or np.any(xy > 1):
        raise ValueError("NORMALIZED_PARAMETER_OUTSIDE_UNIT_SQUARE")
    return (SIGMA_BOUNDS_MPA[0] * math.exp(float(xy[0]) * math.log(SIGMA_BOUNDS_MPA[1] / SIGMA_BOUNDS_MPA[0])),
            N_BOUNDS[0] + float(xy[1]) * (N_BOUNDS[1] - N_BOUNDS[0]))


def validate_dataset(valid: list[dict], invalid: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if len(valid) != 19 or len(invalid) != 3:
        raise ValueError("EXPECTED_19_VALID_AND_3_INVALID")
    ids = [r["point_id"] for r in valid + invalid]
    if len(set(ids)) != 22 or set(r["point_id"] for r in invalid) != {"D07", "D09", "D10"}:
        raise ValueError("DATASET_IDENTITY_CONFLICT")
    x = np.array([normalize(float(r["sigma_y_mpa"]), float(r["n"])) for r in valid])
    y = np.array([float(r["loss"]) for r in valid])
    bad = np.array([normalize(float(r["sigma_y_mpa"]), float(r["n"])) for r in invalid])
    if not np.all(np.isfinite(y)) or np.any(y < 0):
        raise ValueError("INVALID_LOSS")
    if any(r["loss"] is not None for r in invalid):
        raise ValueError("INVALID_POINTS_MUST_RETAIN_NULL")
    if np.unique(np.round(x, 12), axis=0).shape[0] != 19:
        raise ValueError("DUPLICATE_VALID_X")
    return x, y, bad


def valid_candidate(xy: np.ndarray, existing: np.ndarray, bad: np.ndarray,
                    selected: list[np.ndarray]) -> bool:
    if np.any(xy < 0) or np.any(xy > 1):
        return False
    if np.min(np.linalg.norm(existing - xy, axis=1)) < MIN_EXISTING_DISTANCE:
        return False
    if np.min(np.linalg.norm(bad - xy, axis=1)) < FAILED_DISTANCE:
        return False
    if selected and min(float(np.linalg.norm(p - xy)) for p in selected) < MIN_BATCH_DISTANCE:
        return False
    return True


def _fit_gp(x: np.ndarray, transformed_loss: np.ndarray, *, kernel=None, optimize=True):
    if kernel is None:
        kernel = (ConstantKernel(1.0, (1e-3, 1e3)) *
                  Matern(length_scale=[0.25, 0.25], length_scale_bounds=(0.03, 2.0), nu=2.5) +
                  WhiteKernel(noise_level=1e-6, noise_level_bounds=(1e-8, 1e-3)))
    gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True, alpha=1e-8,
                                  n_restarts_optimizer=4 if optimize else 0,
                                  optimizer="fmin_l_bfgs_b" if optimize else None,
                                  random_state=SEED)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        gp.fit(x, transformed_loss)
    return gp, [str(w.message) for w in caught]


def expected_improvement(gp, points: np.ndarray, best: float) -> np.ndarray:
    mean, std = gp.predict(points, return_std=True)
    std = np.maximum(std, 1e-12)
    gain = best - mean - EI_XI_LOG1P
    z = gain / std
    return gain * norm.cdf(z) + std * norm.pdf(z)


def propose_bo(valid: list[dict], invalid: list[dict], count=4) -> dict:
    """Greedy kriging-believer batch EI; four points share no real new observation."""
    if count != 4:
        raise ValueError("FROZEN_FIRST_GATE_REQUIRES_FOUR")
    existing, loss, bad = validate_dataset(valid, invalid)
    y = np.log1p(loss)
    gp, fit_warnings = _fit_gp(existing, y)
    fitted_kernel = gp.kernel_
    # Fixed Sobol candidate pool makes discrete acquisition reproducible.
    pool = qmc.Sobol(d=2, scramble=True, seed=SEED).random_base2(m=14)
    chosen = []
    proposals = []
    fantasy_x = existing.copy()
    fantasy_y = y.copy()
    model = gp
    for rank in range(1, count + 1):
        mask = np.array([valid_candidate(p, existing, bad, chosen) for p in pool])
        candidates = pool[mask]
        if not len(candidates):
            raise RuntimeError("NO_FEASIBLE_BATCH_CANDIDATE")
        ei = expected_improvement(model, candidates, float(np.min(y)))
        idx = int(np.argmax(ei))
        p = candidates[idx]
        predicted_log_loss, predicted_sd = model.predict(p.reshape(1, 2), return_std=True)
        chosen.append(p)
        sigma, n = physical(p)
        proposals.append({"rank": rank, "x": float(p[0]), "y": float(p[1]),
                          "sigma_y_mpa": sigma, "n": n,
                          "acquisition_ei": float(ei[idx]),
                          "fantasy_log1p_loss": float(predicted_log_loss[0]),
                          "posterior_std_log1p": float(predicted_sd[0]),
                          "depends_on_new_fe_observation": False})
        fantasy_x = np.vstack([fantasy_x, p])
        fantasy_y = np.append(fantasy_y, predicted_log_loss[0])
        model, _ = _fit_gp(fantasy_x, fantasy_y, kernel=fitted_kernel, optimize=False)
    return {"method":"batch_bo_greedy_kriging_believer_ei", "seed":SEED,
            "initial_kernel":str(fitted_kernel), "fit_warnings":fit_warnings,
            "target_transform":"log1p(Loss)","acquisition":"EI(xi=0.005) in log1p loss space",
            "sobol_pool_size":len(pool), "batch_fantasy":"posterior mean; no real new FE outcomes",
            "proposals":proposals}


def select_de_population(valid: list[dict]) -> list[dict]:
    """Best point plus deterministic farthest-first coverage of existing evaluations."""
    candidates = sorted(valid, key=lambda r:(r["loss"],r["point_id"]))
    selected = [candidates[0]]
    while len(selected) < DE_POPULATION:
        remaining = [r for r in candidates if r["point_id"] not in {s["point_id"] for s in selected}]
        next_row = max(remaining, key=lambda r:(
            min(float(np.linalg.norm(normalize(r["sigma_y_mpa"],r["n"])-
                                     normalize(s["sigma_y_mpa"],s["n"]))) for s in selected),
            -r["loss"],r["point_id"]))
        selected.append(next_row)
    return selected


def _reflect_unit(v: np.ndarray) -> np.ndarray:
    # Reflection avoids point piles caused by clipping at a physical bound.
    return np.abs((v + 1.0) % 2.0 - 1.0)


def propose_de(valid: list[dict], invalid: list[dict], count=4,
               other_branch: list[np.ndarray] | None = None) -> dict:
    """Four simultaneous trials of one frozen eight-member DE/rand/1/bin generation."""
    if count != 4:
        raise ValueError("FROZEN_FIRST_GATE_REQUIRES_FOUR")
    existing, _, bad = validate_dataset(valid, invalid)
    population = select_de_population(valid)
    pop = np.array([normalize(r["sigma_y_mpa"],r["n"]) for r in population])
    rng = np.random.default_rng(SEED + 1)
    selected = list(other_branch or [])
    proposals = []
    for target_idx in range(count):
        choices = [i for i in range(DE_POPULATION) if i != target_idx]
        for attempt in range(10000):
            a,b,c = rng.choice(choices, 3, replace=False)
            mutant = _reflect_unit(pop[a] + DE_F * (pop[b] - pop[c]))
            mask = rng.random(2) < DE_CR
            mask[int(rng.integers(0,2))] = True
            trial = np.where(mask, mutant, pop[target_idx])
            if valid_candidate(trial, existing, bad, selected):
                break
        else:
            raise RuntimeError("NO_FEASIBLE_DE_TRIAL")
        selected.append(trial)
        sigma,n = physical(trial)
        proposals.append({"rank":target_idx+1,"target_id":population[target_idx]["point_id"],
                          "donor_ids":[population[i]["point_id"] for i in (a,b,c)],
                          "crossover_mask":mask.tolist(), "generation":1,
                          "x":float(trial[0]),"y":float(trial[1]),"sigma_y_mpa":sigma,"n":n,
                          "depends_on_new_fe_observation":False})
    return {"method":"DE/rand/1/bin_partial_generation", "seed":SEED+1,
            "population_size":DE_POPULATION,"F":DE_F,"CR":DE_CR,
            "boundary":"reflect to [0,1]", "population_ids":[r["point_id"] for r in population],
            "generated_trials":4,"full_generation_trials":8,
            "selection":"all four trials evaluated together; parent replacement only after actual FE",
            "proposals":proposals}
