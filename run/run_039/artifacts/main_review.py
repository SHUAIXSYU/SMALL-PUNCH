"""Independent MAIN review of the frozen SPT DOE; never starts Abaqus."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(r"E:\Projects\SMALL-PUNCH")))
from agenthub_sp_invopt.hub import Hub

ROOT = Path(r"E:\Projects\SMALL-PUNCH")
RUN = ROOT / "run/run_039"
OUT = RUN / "artifacts/private/main"
OLD = ROOT / "run/run_034/artifacts/private/odb"
NEW = RUN / "artifacts/private/odb"
I01 = ROOT / "run/run_032/artifacts/private/odb"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    binding_path = ROOT / "run/run_030/artifacts/loss_contract_binding.json"
    binding = read(binding_path)
    for key, hash_key in (("loss_identity_path", "loss_identity_sha256"),
                          ("config_path", "config_sha256"), ("target_path", "target_sha256"),
                          ("implementation_path", "implementation_sha256")):
        assert digest(ROOT / binding[key]) == binding[hash_key]
    assert binding["version"] == "run017-exploratory-fd-v1"
    target = rows(ROOT / binding["target_path"])[:241]
    u = np.array([float(r["displacement_m"]) for r in target])
    fexp = np.array([float(r["force_n"]) for r in target])
    assert len(u) == 241 and u[0] == 0 and abs(u[-1] - .0012) < 1e-12
    assert np.all(np.diff(u) > 0)
    ref = float(binding["F_ref_n"])
    assert ref == 1428.9
    batch20 = read(ROOT / "run/run_033/artifacts/prepared_batch.json")
    batch8 = read(ROOT / "run/run_030/artifacts/prepared_batch.json")
    assert batch20["numeric_version"] == batch8["numeric_version"] == "run030-standard-m0025-hollomon-v1"
    assert batch20["loss_version"] == batch8["loss_version"] == binding["version"]
    p20 = {r["point_id"]: r for r in batch20["points"]}
    p8 = {r["point_id"]: r for r in batch8["points"]}
    assert len(p20) == 20 and len(set(batch20["batch_order"])) == 20
    old_revalidated = read(NEW / "existing_19_revalidation.json")
    assert len(old_revalidated["records"]) == 19
    assert all(r["reusable"] for r in old_revalidated["records"])
    assert read(NEW / "i01_revalidation.json")["reusable"]
    existing = {r["point_id"]: r for r in old_revalidated["records"]}
    assert set(existing) == set(p20) - {"D09"}
    audit = read(RUN / "artifacts/private/execution_audit.json")
    assert audit["original_software_completed"] == 19 and audit["original_interrupted"] == 1
    assert audit["replacement_software_completed"] == 1
    odb_task_id = read(RUN/"artifacts/task_ids.json")["odb_task_id"]
    hub = Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3")
    assert hub.task(odb_task_id)["execution_state"] == "COMPLETED"
    assert hub.verify_chain()
    manifest = read(NEW/"manifest.json")
    assert len(manifest["files"]) == manifest["file_count"] == 45
    for item in manifest["files"]:
        path = ROOT/item["path"]
        assert path.stat().st_size == item["bytes"] and digest(path) == item["sha256"]

    review = []
    curves = {}
    independently_scored = 0
    for pid in ["I01", "I02"] + batch20["batch_order"]:
        frozen = p8[pid] if pid in {"I01", "I02"} else p20[pid]
        source = I01 if pid == "I01" else NEW / "I02" if pid == "I02" else NEW / "D09" if pid == "D09" else OLD / pid
        result = read(source / "result.json")
        score = read(source / "loss_score.json")
        assert result["point_id"] == pid
        assert result["inp_sha256"] == frozen["inp_sha256"]
        assert result["project_id"] == batch20["project_id"]
        assert result["full_status"]["odb_job_status"] == "JOB_STATUS_COMPLETED_SUCCESSFULLY"
        assert result["max_saved_peeq"] < result["material_table_max_plastic_strain"] == .9
        assert score["version"] == binding["version"]
        for key in ("config_sha256", "target_sha256", "implementation_sha256"):
            if key in score:
                assert score[key] == binding[key]
        assert digest(ROOT / frozen["inp_path"]) == frozen["inp_sha256"]
        if pid in existing:
            assert existing[pid]["result_path"] == (source / "result.json").relative_to(ROOT).as_posix()
        if pid == "D09":
            assert result["job_name"] == "SPIO_R038_D09_RETRY2"
            assert result["queue_id"] == "q_434c5f15c837413f8628b5b5188088aa"
            assert score["loss_or_null"] is None
        else:
            assert result["job_name"] == frozen["job_name"]
        if pid == "I02":
            assert result["queue_id"] == "q_a40ddbf45cec472cb3541e28e6184fad"
        loss = score["loss_or_null"]
        rmse = None
        if loss is not None:
            aligned = rows(source / "aligned_241.csv")
            assert len(aligned) == 241
            ua = np.array([float(r["displacement_m"]) for r in aligned])
            ta = np.array([float(r["target_force_n"]) for r in aligned])
            fe = np.array([float(r["fe_interpolated_force_n"]) for r in aligned])
            assert np.max(np.abs(ua-u)) < 1e-15 and np.max(np.abs(ta-fexp)) < 1e-9
            assert np.all(np.isfinite(fe))
            loss_check = math.fsum(((float(a)-float(b))/ref)**2 for a,b in zip(fe,fexp))/241
            rmse = math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(fe,fexp))/241)
            assert abs(loss_check-loss) < 1e-12
            assert abs(rmse-score["rmse_n_or_null"]) < 1e-8
            curves[pid] = fe
            independently_scored += 1
        else:
            assert pid in {"D07", "D09", "D10"}
            assert score["status"] == "LOSS_NULL_NUMERICAL_BLOCKER"
        blockers = read(source / "numeric_review.json")["blocking_issues"]
        assert (loss is None) == bool(blockers)
        review.append({"point_id":pid, "job_name":result["job_name"], "original_job_name":frozen["job_name"],
                       "queue_id":result["queue_id"], "source_attempt":"run038_replacement" if pid=="D09" else "original",
                       "region":frozen["region"], "sigma_y_mpa":frozen["sigma_y_mpa"], "n":frozen["n"],
                       "x":frozen["x"], "y":frozen["y"],
                       "software_status":"COMPLETED_WITH_WARNINGS", "numerical_quality":"BLOCKED" if blockers else "WARNING_REVIEWED_PROVISIONAL",
                       "loss":loss, "rmse_n":rmse, "nrmse":None if rmse is None else rmse/ref,
                       "runtime_s":result["actual_runtime_s"], "cutback":result["cutback_increments"],
                       "rejected_attempts":result["rejected_attempts"], "max_saved_peeq":result["max_saved_peeq"],
                       "accepted_warning_classes":sorted({e["class"] for e in result["warning_events_by_accepted_or_rejected"]["accepted"]}),
                       "blocking_issues":blockers, "inp_sha256":result["inp_sha256"], "odb_sha256":result["odb_sha256"],
                       "result_path":(source/"result.json").relative_to(ROOT).as_posix(),
                       "result_sha256":digest(source/"result.json")})
    assert len(review) == 22 and independently_scored == 19
    scored = sorted([r for r in review if r["loss"] is not None], key=lambda r:r["loss"])
    low = [r for r in scored if r["loss"] <= .01]
    xy = np.array([[r["x"],r["y"]] for r in low])
    corr = float(np.corrcoef(xy.T)[0,1]) if len(low) >= 3 else None
    if len(low) >= 3:
        reg = np.polyfit(xy[:,0],xy[:,1],1)
        slope = float(reg[0])
    else:
        slope = None
    groups = {}
    for region in ("GLOBAL","LOCAL"):
        group = [r for r in scored if r["region"] == region]
        groups[region] = {"scored":len(group), "median_loss":statistics.median(r["loss"] for r in group),
                          "best_loss":min(r["loss"] for r in group)}
    curve_similarity = []
    for i,a in enumerate(low):
        for b in low[i+1:]:
            d = curves[a["point_id"]]-curves[b["point_id"]]
            curve_similarity.append({"a":a["point_id"],"b":b["point_id"],
                                     "force_rmse_n":float(np.sqrt(np.mean(d*d))),
                                     "parameter_distance_xy":float(np.linalg.norm([a["x"]-b["x"],a["y"]-b["y"]]))})
    curve_similarity.sort(key=lambda r:r["force_rmse_n"])
    bins = [(0,.0004),(.0004,.0008),(.0008,.0012)]
    interval_distinction = []
    for lo,hi in bins:
        mask = (u>=lo-1e-12) & (u<=hi+1e-12)
        vals = [curves[r["point_id"]][mask] for r in low]
        interval_distinction.append({"u_mm":[lo*1000,hi*1000],
                                     "low_loss_curve_spread_rms_n":float(np.sqrt(np.mean(np.var(vals,axis=0)))) if len(vals)>1 else None})
    runtime = [r["runtime_s"] for r in review]
    totals = {"original_batch_job_count":20,"original_software_completed":19,"original_interrupted":1,
              "replacement_D09_software_completed":1,"distinct_parameter_points":22,
              "software_completed_distinct_parameter_points":22,"numerically_scored":19,"numerical_blockers":3,
              "original_batch_scored":17,"runtime_sum_22_completed_s":sum(runtime),
              "runtime_median_s":statistics.median(runtime),"allocated_cpu_hours_14":14*sum(runtime)/3600,
              "cutback_range":[min(r["cutback"] for r in review),max(r["cutback"] for r in review)],
              "saved_peeq_range":[min(r["max_saved_peeq"] for r in review),max(r["max_saved_peeq"] for r in review)]}
    finding = {"observed_at":datetime.now().astimezone().isoformat(),"status":"WARNING_19_OF_22_NUMERICALLY_SCOREABLE",
               "project_id":batch20["project_id"],"numeric_version":batch20["numeric_version"],
               "loss_version":binding["version"],"loss_binding_sha256":digest(binding_path),
               "target_sha256":binding["target_sha256"],"independent_loss_recalculated":independently_scored,
               "totals":totals,"top_five":scored[:5],"best_evaluated":scored[0],
               "low_loss_descriptive_threshold":.01,"low_loss_point_ids":[r["point_id"] for r in low],
               "low_loss_count":len(low),"low_loss_normalized_xy_pearson":corr,"low_loss_regression_y_on_x_slope":slope,
               "low_loss_pairwise_fe_curve_similarity":curve_similarity,"displacement_interval_diagnostics":interval_distinction,
               "region_summary":groups,
               "original_D09":"UNKNOWN_INTERRUPTED; legacy ODB not opened or scored; separate run038 replacement completed but blocked numerical score",
               "blocked_point_ids":[r["point_id"] for r in review if r["loss"] is None],
               "prior_run022_sensitivity":{"cosine":.990176,"condition_number":15.1276,"scope":"different, coarser increment contract; context only"},
               "science":"SPT exploratory provisional only; sparse samples do not establish global optimum, uniqueness or tensile validation",
               "bo_de_admission":"WARNING_CONDITIONAL_EXPLORATION",
               "rows":review}
    save(OUT/"main_review.json",finding)
    with (OUT/"original_20_execution_audit.csv").open("w",encoding="utf-8",newline="") as stream:
        keys=["point_id","original_job_name","original_queue_id","original_status","original_started_at",
              "original_ended_at","original_duration_s","frozen_inp_sha256","numerical_score_from_original"]
        w=csv.DictWriter(stream,fieldnames=keys); w.writeheader()
        reviewed={r["point_id"]:r for r in review}
        assert len(audit["original_batch"])==20
        for old in audit["original_batch"]:
            row={k:old.get(k) for k in keys}
            row["numerical_score_from_original"]=(reviewed[old["point_id"]]["loss"]
                                                   if old["point_id"]!="D09" else None)
            w.writerow(row)
    with (OUT/"evaluated_22_points.csv").open("w",encoding="utf-8",newline="") as stream:
        keys=["point_id","region","sigma_y_mpa","n","x","y","job_name","queue_id","source_attempt",
              "software_status","numerical_quality","loss","rmse_n","nrmse","runtime_s","cutback","rejected_attempts","max_saved_peeq"]
        w=csv.DictWriter(stream,fieldnames=keys); w.writeheader()
        for r in review: w.writerow({k:r.get(k) for k in keys})
    mm=u*1000
    fig,ax=plt.subplots(figsize=(8,6),layout="constrained")
    for region,marker in (("GLOBAL","o"),("LOCAL","s")):
        g=[r for r in scored if r["region"]==region]
        ax.scatter([r["x"] for r in g],[r["y"] for r in g],c=[math.log10(r["loss"]) for r in g],
                   vmin=-4,vmax=1,cmap="viridis",marker=marker,s=80,edgecolor="black",label=f"{region} scored")
    for r in review:
        if r["loss"] is None: ax.scatter(r["x"],r["y"],color="red",marker="x",s=80)
        ax.annotate(r["point_id"],(r["x"],r["y"]),xytext=(3,3),textcoords="offset points",fontsize=7)
    m=matplotlib.cm.ScalarMappable(norm=matplotlib.colors.Normalize(-4,1),cmap="viridis")
    fig.colorbar(m,ax=ax,label="log10(frozen Loss)")
    ax.set(xlabel="x = ln(sigma_y/150)/ln(1000/150)",ylabel="y = (n-0.02)/0.48",
           xlim=(-.03,1.03),ylim=(-.03,1.03),title="Actual FE evaluations; red x = numerical score blocked")
    ax.legend(); fig.savefig(OUT/"parameter_loss_scatter.png",dpi=170); plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,6),layout="constrained")
    for r in low:
        ax.scatter(r["sigma_y_mpa"],r["n"],c=[math.log10(r["loss"])],vmin=-4,vmax=-2,
                   cmap="viridis",s=100,edgecolor="black")
        ax.annotate(r["point_id"],(r["sigma_y_mpa"],r["n"]),xytext=(4,4),textcoords="offset points")
    ax.set(xlabel="sigma_y (MPa)",ylabel="n",title="Measured FE points with frozen Loss <= 0.01")
    fig.savefig(OUT/"low_loss_zoom.png",dpi=170); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5),layout="constrained")
    for r in scored[:5]: ax.plot(mm,curves[r["point_id"]],label=f'{r["point_id"]}: {r["loss"]:.4g}')
    ax.plot(mm,fexp,color="black",linewidth=2,label="SPT target")
    ax.set(xlabel="Punch displacement (mm)",ylabel="Force (N)",title="Top five valid FE evaluations on frozen grid")
    ax.legend(); fig.savefig(OUT/"top_five_fd.png",dpi=170); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,5),layout="constrained")
    vals=[[r["loss"] for r in scored if r["region"]==z] for z in ("GLOBAL","LOCAL")]
    ax.boxplot(vals,tick_labels=["GLOBAL","LOCAL"])
    ax.set(yscale="log",ylabel="Frozen Loss",title="Observed full-domain and local DOE samples")
    fig.savefig(OUT/"global_local_loss.png",dpi=170); plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(12,5),layout="constrained")
    for panel,key,label in ((ax[0],"runtime_s","Elapsed (s)"),(ax[1],"cutback","Cutback count")):
        panel.scatter([r[key] for r in scored],[r["loss"] for r in scored],s=65)
        panel.set(xlabel=label,ylabel="Frozen Loss",yscale="log")
    fig.savefig(OUT/"loss_vs_runtime_cutback.png",dpi=170); plt.close(fig)
    print(json.dumps({"status":finding["status"],"totals":totals,"top_five":[{k:r[k] for k in ("point_id","sigma_y_mpa","n","loss","rmse_n","numerical_quality")} for r in scored[:5]],"low_corr":corr},ensure_ascii=False))


if __name__ == "__main__":
    main()
