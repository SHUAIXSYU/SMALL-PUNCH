"""MAIN's independent, SPT-only review of the run_034 ODB handoff.

Reads frozen inputs and the completed ODB task. It never calls the solver,
opens an ODB, changes a source curve, or treats a missing score as zero.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_034"
OUT = RUN / "artifacts/private/main"
ODB = RUN / "artifacts/private/odb"
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(path: Path):
    return path.relative_to(ROOT).as_posix()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    binding = load(ROOT / "run/run_030/artifacts/loss_contract_binding.json")
    for key, hash_key in (("loss_identity_path", "loss_identity_sha256"),
                          ("config_path", "config_sha256"),
                          ("target_path", "target_sha256"),
                          ("implementation_path", "implementation_sha256")):
        assert sha(ROOT / binding[key]) == binding[hash_key]
    prepared = load(ROOT / "run/run_033/artifacts/prepared_batch.json")
    by_id = {p["point_id"]: p for p in prepared["points"]}
    order = prepared["batch_order"]
    assert len(order) == 20 and len(by_id) == 20
    manifest = load(ODB / "manifest.json")
    assert len(manifest["files"]) == manifest["file_count"]
    for item in manifest["files"]:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    summary = load(ODB / "batch_summary.json")
    assert summary["read_only_extraction_pass_count"] == 19
    hub = Hub(ROOT / "agenthub_sp_invopt/runtime/sp_invopt.sqlite3")
    task_id = load(RUN / "artifacts/task_ids.json")["odb_task_id"]
    task = hub.task(task_id)
    assert task is not None and task["execution_state"] == "COMPLETED"
    assert hub.verify_chain()
    target = rows(ROOT / binding["target_path"])[:241]
    assert len(target) == 241
    u = np.array([float(r["displacement_m"]) for r in target])
    fexp = np.array([float(r["force_n"]) for r in target])
    assert u[0] == 0 and abs(u[-1] - .0012) < 1e-12
    ref = float(binding["F_ref_n"])
    review = []
    curves = {}
    for pid in order:
        frozen = by_id[pid]
        result_path = ODB / pid / "result.json"
        if pid == "D09":
            assert not result_path.exists()
            review.append({"point_id": pid, "job_name": frozen["job_name"],
                           "region": frozen["region"], "sigma_y_mpa": frozen["sigma_y_mpa"],
                           "n": frozen["n"], "x": frozen["x"], "y": frozen["y"],
                           "execution": "UNKNOWN_INTERRUPTED", "score_status": "NULL_UNCONFIRMED_EXECUTION",
                           "loss": None, "rmse_n": None, "nrmse": None,
                           "runtime_s": None, "cutback": None, "max_saved_peeq": None,
                           "reason": "Datacheck only; full terminal state unconfirmed and .lck present"})
            continue
        r = load(result_path)
        assert r["point_id"] == pid and r["job_name"] == frozen["job_name"]
        assert r["inp_sha256"] == frozen["inp_sha256"]
        assert r["project_id"] == prepared["project_id"]
        assert r["full_status"]["queue_status"] == "COMPLETED"
        assert r["full_status"]["odb_job_status"] == "JOB_STATUS_COMPLETED_SUCCESSFULLY"
        assert r["max_saved_peeq"] < r["material_table_max_plastic_strain"] == .9
        score = load(ODB / pid / "loss_score.json")
        assert score["version"] == binding["version"]
        for k in ("config_sha256", "target_sha256", "implementation_sha256"):
            assert score[k] == binding[k]
        value = score["loss_or_null"]
        if value is not None:
            aligned = rows(ODB / pid / "aligned_241.csv")
            assert len(aligned) == 241
            ua = np.array([float(q["displacement_m"]) for q in aligned])
            assert np.max(np.abs(ua - u)) < 1e-15
            fa = np.array([float(q["fe_interpolated_force_n"]) for q in aligned])
            ta = np.array([float(q["target_force_n"]) for q in aligned])
            assert np.max(np.abs(ta - fexp)) < 1e-9
            independent = math.fsum(float(((a-b)/ref)**2) for a, b in zip(fa, fexp)) / 241
            assert abs(independent - value) < 1e-12
            rmse = math.sqrt(math.fsum(float((a-b)**2) for a, b in zip(fa, fexp)) / 241)
            assert abs(rmse - score["rmse_n_or_null"]) < 1e-8
            curves[pid] = fa
        else:
            assert score["status"] == "LOSS_NULL_NUMERICAL_BLOCKER"
            assert pid in {"D07", "D10"}
            rmse = None
        review.append({"point_id": pid, "job_name": r["job_name"],
                       "queue_id": r["queue_id"], "region": frozen["region"],
                       "sigma_y_mpa": frozen["sigma_y_mpa"], "n": frozen["n"],
                       "x": frozen["x"], "y": frozen["y"],
                       "execution": "COMPLETED_WITH_WARNINGS",
                       "score_status": score["status"], "loss": value,
                       "rmse_n": rmse, "nrmse": None if rmse is None else rmse/ref,
                       "runtime_s": r["actual_runtime_s"],
                       "cutback": r["cutback_increments"],
                       "rejected_attempts": r["rejected_attempts"],
                       "max_saved_peeq": r["max_saved_peeq"],
                       "accepted_warning_classes": sorted({e["class"] for e in r["warning_events_by_accepted_or_rejected"]["accepted"]}),
                       "rejected_warning_classes": sorted({e["class"] for e in r["warning_events_by_accepted_or_rejected"]["rejected"]}),
                       "numerical_blocking_issues": load(ODB / pid / "numeric_review.json")["blocking_issues"],
                       "result_sha256": sha(result_path), "curve_sha256": sha(ODB / pid / "force_displacement.csv")})
    assert len(review) == 20 and len(curves) == 17
    scored = sorted((r for r in review if r["loss"] is not None), key=lambda x:x["loss"])
    best = scored[0]
    low = [r for r in scored if r["loss"] <= .01]
    times = [r["runtime_s"] for r in review if r["runtime_s"] is not None]
    cutbacks = [r["cutback"] for r in review if r["cutback"] is not None]
    peeqs = [r["max_saved_peeq"] for r in review if r["max_saved_peeq"] is not None]
    groups = {}
    for region in ("GLOBAL", "LOCAL"):
        group = [r for r in scored if r["region"] == region]
        groups[region] = {"scored_count": len(group), "median_loss": float(np.median([r["loss"] for r in group])),
                          "min_loss": min(r["loss"] for r in group)}
    low_xy = np.array([[r["x"], r["y"]] for r in low])
    low_corr = float(np.corrcoef(low_xy.T)[0,1]) if len(low) >= 3 else None
    risk = {"D09": "UNKNOWN_INTERRUPTED; do not read/score/clean/retry",
            "D10": "accepted-attempt LARGE_STRAIN_INCREMENT warning; frozen protocol blocks scoring",
            "D07": "one -0.00030517578125 N final accepted-frame force step at 1.199681–1.2 mm; ODB gate conservatively null; tiny amplitude does not establish its cause; review before use"}
    totals = {"attempted": 20, "public_software_completed": 19, "read_only_odb_extracted": 19,
              "frozen_provisional_scores": 17, "loss_null": 3,
              "runtime_s_completed_sum": sum(times),
              "runtime_s_completed_median": float(np.median(times)),
              "allocated_cpu_hours_14cpus": 14*sum(times)/3600,
              "cutback_min_max": [min(cutbacks), max(cutbacks)],
              "max_saved_peeq_min_max": [min(peeqs), max(peeqs)]}
    finding = {"observed_at": datetime.now().astimezone().isoformat(),
               "status": "MAIN_REVIEW_WARNING_THREE_UNSCORED",
               "project_id": prepared["project_id"], "numeric_version": prepared["numeric_version"],
               "loss_version": binding["version"], "loss_binding_sha256": sha(ROOT / "run/run_030/artifacts/loss_contract_binding.json"),
               "odb_task_id": task_id, "odb_task_execution_state": task["execution_state"],
               "odb_manifest_sha256": sha(ODB / "manifest.json"),
               "odb_manifest_verified_file_count": manifest["file_count"],
               "independent_loss_recalculated_count": len(curves),
               "totals": totals, "best_evaluated": best,
               "low_loss_descriptive_threshold": .01,
               "low_loss_count": len(low), "low_loss_points": [r["point_id"] for r in low],
               "low_loss_sigma_range_mpa": [min(r["sigma_y_mpa"] for r in low), max(r["sigma_y_mpa"] for r in low)],
               "low_loss_n_range": [min(r["n"] for r in low), max(r["n"] for r in low)],
               "low_loss_normalized_xy_pearson": low_corr,
               "region_summary": groups, "risk": risk,
               "science": "PROVISIONAL_SPT_ONLY; no global optimum, parameter uniqueness, formal inversion, fixture equivalence, or hidden tensile validation",
               "bo_de_admission": "PAUSE_NEW_FE_PENDING_D09_RUNNER_STATE_AND_D10_NUMERICAL_REVIEW; 17 provisional samples support offline surrogate diagnostics only; separate authorization required for new FE",
               "rows": review}
    save(OUT / "main_review.json", finding)
    with (OUT / "review_table.csv").open("w", encoding="utf-8", newline="") as stream:
        columns = ["point_id", "region", "sigma_y_mpa", "n", "x", "y", "execution", "score_status", "loss", "rmse_n", "nrmse", "runtime_s", "cutback", "max_saved_peeq"]
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for r in review:
            writer.writerow({k:r.get(k) for k in columns})
    mm = u*1000
    fig, ax = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for pid, fe in curves.items():
        ax[0].plot(mm, fe, linewidth=.7, alpha=.65)
    ax[0].plot(mm, fexp, color="black", linewidth=2, label="SPT target")
    ax[0].set(xlabel="Punch displacement (mm)", ylabel="Force (N)", title="17 scored FE curves on fixed 241-point grid")
    ax[0].legend()
    for r in low:
        ax[1].plot(mm, curves[r["point_id"]], label=f'{r["point_id"]} L={r["loss"]:.4g}', linewidth=1)
    ax[1].plot(mm, fexp, color="black", linewidth=2, label="SPT target")
    ax[1].set(xlabel="Punch displacement (mm)", ylabel="Force (N)", title="Descriptive low-loss subset (L <= 0.01)")
    ax[1].legend(fontsize=7)
    fig.savefig(OUT / "fd_overlay.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
    for region, marker in (("GLOBAL", "o"), ("LOCAL", "s")):
        subset = [r for r in scored if r["region"] == region]
        ax.scatter([r["x"] for r in subset], [r["y"] for r in subset],
                   c=[math.log10(r["loss"]) for r in subset], cmap="viridis", vmin=-4, vmax=2,
                   s=75, marker=marker, edgecolors="black", label=f"{region} scored")
    for r in review:
        if r["loss"] is None:
            ax.scatter(r["x"], r["y"], marker="x", s=85, color="red")
        ax.annotate(r["point_id"], (r["x"], r["y"]), xytext=(4,4), textcoords="offset points", fontsize=7)
    colour = matplotlib.cm.ScalarMappable(norm=matplotlib.colors.Normalize(vmin=-4, vmax=2), cmap="viridis")
    fig.colorbar(colour, ax=ax, label="log10(Provisional Loss)")
    ax.set(xlim=(-.03,1.03), ylim=(-.03,1.03), xlabel="x = ln(sigma_y/150)/ln(1000/150)",
           ylabel="y = (n-0.02)/0.48", title="Evaluated DOE points; colour = log10(Loss)")
    ax.legend(fontsize=8)
    fig.savefig(OUT / "parameter_loss_scatter.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 4), constrained_layout=True)
    ax.bar([r["point_id"] for r in scored], [r["loss"] for r in scored])
    ax.set(yscale="log", xlabel="Scored point, ranked", ylabel="Provisional frozen Loss", title="17 evaluated points (null excluded)")
    ax.tick_params(axis="x", rotation=60)
    fig.savefig(OUT / "loss_rank.png", dpi=160)
    plt.close(fig)
    print(json.dumps({"status": finding["status"], "best": {k:best[k] for k in ("point_id","sigma_y_mpa","n","loss")},
                      "totals": totals, "low": [r["point_id"] for r in low], "low_corr": low_corr}, ensure_ascii=False))


if __name__ == "__main__":
    main()
