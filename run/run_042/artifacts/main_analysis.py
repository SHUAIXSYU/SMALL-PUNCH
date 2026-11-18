"""MAIN independent scoring and descriptive BO/DE analysis; no FE proposals/calls."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
RUN=ROOT/"run/run_042"
OUT=RUN/"artifacts/private/main"
ODB=RUN/"artifacts/private/odb"
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub
from inverse.hollomon import stress_from_total_strain


def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1048576),b""):h.update(chunk)
    return h.hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def rows(p):
    with Path(p).open(encoding="utf-8-sig",newline="") as stream:return list(csv.DictReader(stream))
def csv_write(p,data,keys):
    with Path(p).open("w",encoding="utf-8",newline="") as stream:
        w=csv.DictWriter(stream,fieldnames=keys);w.writeheader()
        for r in data:w.writerow({k:r.get(k) for k in keys})


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    ids=read(RUN/"artifacts/task_ids.json")
    hub=Hub(ROOT/"agenthub_sp_invopt/runtime/sp_invopt.sqlite3")
    assert hub.task(ids["odb_task_id"])["execution_state"]=="COMPLETED" and hub.verify_chain()
    manifest=read(ODB/"manifest.json")
    for v in manifest["files"]:
        assert sha(ROOT/v["path"])==v["sha256"]
    binding=read(ROOT/"run/run_030/artifacts/loss_contract_binding.json")
    for key,hkey in (("target_path","target_sha256"),("implementation_path","implementation_sha256"),("config_path","config_sha256")):
        assert sha(ROOT/binding[key])==binding[hkey]
    target=rows(ROOT/binding["target_path"])[:241]
    u=np.array([float(r["displacement_m"]) for r in target]);fexp=np.array([float(r["force_n"]) for r in target]);ref=1428.9
    assert len(u)==241 and u[0]==0 and abs(u[-1]-.0012)<1e-12
    frozen=read(ROOT/"run/run_040/artifacts/private/candidate_manifest.json")
    contract=read(ROOT/frozen["contract_path"])
    assert sha(ROOT/frozen["contract_path"])==frozen["contract_sha256"]
    baseline=read(ROOT/contract["shared_initial_dataset_path"])
    assert sha(ROOT/contract["shared_initial_dataset_path"])==contract["shared_initial_dataset_sha256"]
    assert len(baseline["valid"])==19 and all(r["loss"] is None for r in baseline["invalid"])
    initial_best=min(baseline["valid"],key=lambda r:r["loss"])
    assert initial_best["point_id"]=="D01"
    base_loss=initial_best["loss"]
    audit=read(RUN/"artifacts/private/execution_audit.json")
    by_id={r["candidate_id"]:r for r in audit["records"]}
    output=[];curves={};new_curves={}
    for p in frozen["points"]:
        cid=p["candidate_id"];record=by_id[cid]
        result_path=ODB/cid/"result.json"
        result=read(result_path);score=read(ODB/cid/"loss_score.json")
        assert result.get("candidate_id",result.get("point_id"))==cid
        assert result["queue_id"]==record["queue_id"] and result["job_name"]==p["job_name"]
        assert result["inp_sha256"]==record["inp_sha256"]
        assert result["odb_sha256"]==record["files"]["odb"]["sha256"]
        assert score["version"]==binding["version"]
        for k in ("target_sha256","implementation_sha256","config_sha256"):
            assert score[k]==binding[k]
        value=score["loss_or_null"];rmse=None
        if value is not None:
            curve=rows(ODB/cid/"force_displacement.csv")
            ux=np.array([float(r["displacement_m"]) for r in curve]);fy=np.array([float(r["force_n"]) for r in curve])
            assert np.all(np.isfinite(ux)) and np.all(np.isfinite(fy)) and np.all(np.diff(ux)>0)
            assert ux[0]<=u[0] and ux[-1]>=u[-1]
            interp=np.interp(u,ux,fy)
            independent=math.fsum(((float(a)-float(b))/ref)**2 for a,b in zip(interp,fexp))/241
            rmse=math.sqrt(math.fsum((float(a)-float(b))**2 for a,b in zip(interp,fexp))/241)
            assert abs(independent-value)<1e-12 and abs(rmse-score["rmse_n_or_null"])<1e-8
            new_curves[cid]=interp;curves[cid]=interp
        else:
            assert score["status"]=="LOSS_NULL_NUMERICAL_BLOCKER" or result.get("numerical_blocking_issues")
        warning=result["warning_events_by_accepted_or_rejected"]
        diagnostics=read(ODB/cid/"diagnostics.json")
        force_steps=rows(ODB/cid/"force_steps.csv")
        negative=[r for r in force_steps if float(r["delta_force_n"])<0]
        output.append({"candidate_id":cid,"algorithm":p["algorithm"],"job_name":p["job_name"],"queue_id":record["queue_id"],
                       "sigma_y_mpa":p["sigma_y_mpa"],"n":p["n"],"x":p["x"],"y":p["y"],
                       "loss":value,"rmse_n":rmse,"nrmse":None if rmse is None else rmse/ref,
                       "software_status":record["queue_status"],"started_attempts":record["started_attempts"],
                       "actual_runtime_s":record["actual_runtime_s"],"max_saved_peeq":result["max_saved_peeq"],
                       "cutback":result["cutback_increments"],"rejected_attempts":result["rejected_attempts"],
                       "accepted_warning_classes":sorted({w["class"] for w in warning["accepted"]}),
                       "rejected_warning_classes":sorted({w["class"] for w in warning["rejected"]}),
                       "accepted_warning_counts":dict(Counter(w["class"] for w in warning["accepted"])),
                       "rejected_warning_counts":dict(Counter(w["class"] for w in warning["rejected"])),
                       "contact_review":result.get("contact_transition_review",{}),
                       "contact_focus_1p10_1p16mm":diagnostics["focus_1p10_to_1p16mm"],
                       "energy_diagnostics":diagnostics["energy"],
                       "negative_force_steps":{"count":len(negative),"sum_n":sum(float(r["delta_force_n"]) for r in negative),
                                               "largest_drop_n":min([float(r["delta_force_n"]) for r in negative],default=0),
                                               "first_start_mm":float(negative[0]["start_mm"]) if negative else None,
                                               "last_end_mm":float(negative[-1]["end_mm"]) if negative else None},
                       "blocking_issues":result.get("numerical_blocking_issues",score.get("numerical_blocking_issues",[])),
                       "quality":"WARNING_REVIEWED_PROVISIONAL" if value is not None else "UNSCOREABLE_NUMERICAL_BLOCKER",
                       "result_path":result_path.relative_to(ROOT).as_posix(),"result_sha256":sha(result_path),
                       "source_odb_sha256":result["odb_sha256"]})
    # Frozen initial curves are referenced and independently checked, never rescored using new conventions.
    for b in baseline["valid"]:
        assert sha(ROOT/b["result_path"])==b["result_sha256"] and sha(ROOT/b["fd_path"])==b["fd_sha256"]
        rr=rows(ROOT/b["fd_path"]);uu=np.array([float(r["displacement_m"]) for r in rr]);ff=np.array([float(r["force_n"]) for r in rr])
        assert np.all(np.diff(uu)>0) and uu[0]<=u[0] and uu[-1]>=u[-1]
        curves[b["point_id"]]=np.interp(u,uu,ff)
        assert abs(float(np.mean(((curves[b["point_id"]]-fexp)/ref)**2))-b["loss"])<1e-12
    branches={};budget_rows=[]
    for branch in ("BO","DE"):
        group=[r for r in output if r["algorithm"]==branch]
        valid=[r for r in group if r["loss"] is not None]
        best_new=min(valid,key=lambda r:r["loss"]) if valid else None
        current=base_loss;attempts=0;valid_count=0;wall=0
        budget_rows.append({"algorithm":branch,"attempted_budget":0,"valid_new":0,"best_so_far_loss":current,"cumulative_wall_s":0,"statistic":"fixed-proposal completion order; no intra-batch adaptation"})
        for r in group:
            attempts+=r["started_attempts"];wall+=r["actual_runtime_s"] or 0
            if r["loss"] is not None:current=min(current,r["loss"]);valid_count+=1
            budget_rows.append({"algorithm":branch,"candidate_id":r["candidate_id"],"attempted_budget":attempts,
                                "valid_new":valid_count,"best_so_far_loss":current,"cumulative_wall_s":wall,
                                "statistic":"fixed-proposal completion order; no intra-batch adaptation"})
        branches[branch]={"attempted":attempts,"valid_count":len(valid),"unscoreable_count":len(group)-len(valid),
                          "software_failure_count":sum(not by_id[r["candidate_id"]]["software_completed"] for r in group),
                          "best_new":best_new,"best_so_far_loss":current,"absolute_improvement_over_D01":base_loss-current,
                          "relative_improvement_over_D01":(base_loss-current)/base_loss,
                          "actual_wall_s":wall,"allocated_14cpu_hours":14*wall/3600}
    combined=[{**r,"candidate_id":r["point_id"],"algorithm":"INITIAL","quality":r["numerical_quality"]} for r in baseline["valid"]]
    combined.extend(r for r in output if r["loss"] is not None)
    ranked=sorted(combined,key=lambda r:r["loss"]);best=ranked[0]
    low=[r for r in ranked if r["loss"]<=.01]
    pairwise=[]
    for i,a in enumerate(low):
        for b in low[i+1:]:
            pairwise.append({"a":a["candidate_id"],"b":b["candidate_id"],
                             "normalized_parameter_distance":float(np.linalg.norm([a["x"]-b["x"],a["y"]-b["y"]])),
                             "mutual_fd_rmse_n":float(np.sqrt(np.mean((curves[a["candidate_id"]]-curves[b["candidate_id"]])**2)))})
    # Post-result diagnostics reuse exactly the original GP specification, per branch.
    impl=ROOT/frozen["algorithm_implementation_path"]
    assert sha(impl)==frozen["algorithm_implementation_sha256"]
    spec=importlib.util.spec_from_file_location("run040_frozen_pilot",impl)
    pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
    gp_diag={}
    for branch in ("BO","DE"):
        own=[r for r in output if r["algorithm"]==branch and r["loss"] is not None]
        xx=np.array([[r["x"],r["y"]] for r in baseline["valid"]+own])
        yy=np.log1p([r["loss"] for r in baseline["valid"]+own])
        gp,warnings=pilot._fit_gp(xx,yy)
        gp_diag[branch]={"training_count":len(xx),"kernel":str(gp.kernel_),"warnings":warnings,
                         "scope":"branch-own post-result diagnostic only; original selection unchanged; no proposals generated"}
    de_selection=[]
    base_by={r["point_id"]:r for r in baseline["valid"]}
    for p in frozen["points"]:
        if p["algorithm"]!="DE":continue
        trial=next(r for r in output if r["candidate_id"]==p["candidate_id"])
        target_id=p["proposal"]["target_id"];parent=base_by[target_id]
        de_selection.append({"trial":p["candidate_id"],"target":target_id,"parent_loss":parent["loss"],
                             "trial_loss":trial["loss"],"would_replace_parent":trial["loss"] is not None and trial["loss"]<parent["loss"],
                             "scope":"analysis only; no new DE candidate or evolution executed"})
    result={"at":datetime.now().astimezone().isoformat(),"status":"MAIN_REVIEW_EXPLORATORY_WARNING",
            "initial_best":initial_best,"initial_valid_count":19,"initial_null_ids":[r["point_id"] for r in baseline["invalid"]],
            "software_completed":audit["software_completed"],"started_attempts":audit["started_attempts"],
            "new_scoreable":len(new_curves),"branches":branches,"rows":output,"combined_scoreable_count":len(combined),
            "best_evaluated":best,"low_loss_threshold":.01,"low_loss_ids":[r["candidate_id"] for r in low],
            "low_loss_pairwise":pairwise,"branch_gp_diagnostics":gp_diag,"de_parent_comparisons":de_selection,
            "numeric_version":"run030-standard-m0025-hollomon-v1","loss_version":binding["version"],
            "manifest_verified_files":len(manifest["files"]),"odb_manifest_sha256":sha(ODB/"manifest.json"),
            "science_limit":"Single-seed batch BO and partial DE; no unique constitutive identification; sealed tensile not accessed"}
    save(OUT/"main_analysis.json",result)
    csv_write(OUT/"eight_results.csv",output,["candidate_id","algorithm","sigma_y_mpa","n","loss","rmse_n","nrmse","max_saved_peeq","cutback","rejected_attempts","actual_runtime_s","software_status","quality","queue_id"])
    csv_write(OUT/"loss_budget.csv",budget_rows,["algorithm","candidate_id","attempted_budget","valid_new","best_so_far_loss","cumulative_wall_s","statistic"])
    csv_write(OUT/"combined_valid.csv",combined,["candidate_id","algorithm","sigma_y_mpa","n","x","y","loss","quality"])
    fig,ax=plt.subplots(1,2,figsize=(12,4.7),layout="constrained")
    for branch in ("BO","DE"):
        r=[z for z in budget_rows if z["algorithm"]==branch]
        ax[0].step([z["attempted_budget"] for z in r],[z["best_so_far_loss"] for z in r],where="post",label=branch,
                   ls="--" if branch=="BO" else ":",linewidth=2)
        ax[0].scatter([z["attempted_budget"] for z in r],[z["best_so_far_loss"] for z in r],s=35,
                      marker="o" if branch=="BO" else "x",facecolors="none" if branch=="BO" else None)
        ax[1].bar(branch,branches[branch]["actual_wall_s"],label=f"{branch}: {branches[branch]['valid_count']}/4 scoreable")
    ax[0].set(xlabel="New started FE attempts (null included)",ylabel="Best frozen Loss including common baseline",title="Fixed batch order statistics; no intra-batch adaptation")
    ax[0].ticklabel_format(style="sci",axis="y",scilimits=(0,0));ax[0].legend()
    ax[0].text(.04,.08,"BO = DE = shared initial D01 at every budget",transform=ax[0].transAxes,fontsize=9)
    ax[1].set(ylabel="Actual elapsed Job seconds",title="Branch FE cost");ax[1].legend()
    fig.savefig(OUT/"loss_budget_and_cost.png",dpi=170);plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(10,4.5),layout="constrained")
    for branch in ("BO","DE"):
        ax[0].bar(branch,branches[branch]["valid_count"],label=f"{branch}: {branches[branch]['valid_count']}/4")
        best_new=branches[branch]["best_new"]
        if best_new:ax[1].bar(branch,best_new["loss"])
    ax[0].set(ylim=(0,4.5),ylabel="Scoreable new FE evaluations",title="All four started attempts count per branch");ax[0].legend()
    ax[1].axhline(base_loss,color="black",ls="--",label="Shared initial D01")
    ax[1].set(yscale="log",ylabel="Best new frozen Loss",title="Single-seed pilot; no general algorithm ranking");ax[1].legend()
    fig.savefig(OUT/"validity_and_best_new_loss.png",dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,6),layout="constrained")
    for label,marker in (("INITIAL","o"),("BO","s"),("DE","^")):
        rr=[r for r in combined if r["algorithm"]==label]
        if rr:ax.scatter([r["sigma_y_mpa"] for r in rr],[r["n"] for r in rr],c=[math.log10(r["loss"]) for r in rr],vmin=-4,vmax=1.2,cmap="viridis",marker=marker,s=70,edgecolor="black",label=label)
    for r in output:
        if r["loss"] is None:ax.scatter(r["sigma_y_mpa"],r["n"],marker="x",color="red",s=85)
        ax.annotate(r["candidate_id"],(r["sigma_y_mpa"],r["n"]),xytext=(4,4),textcoords="offset points",fontsize=7)
    ax.set(xscale="log",xlabel="sigma_y (MPa)",ylabel="n",title="Actual valid FE Loss; red x = new null score");ax.legend()
    fig.colorbar(matplotlib.cm.ScalarMappable(norm=matplotlib.colors.Normalize(-4,1.2),cmap="viridis"),ax=ax,label="log10(frozen Loss)")
    fig.savefig(OUT/"parameter_loss_scatter.png",dpi=170);plt.close(fig)
    displayed=[]
    for key in ["D01","I08"]+[b["best_new"]["candidate_id"] for b in branches.values() if b["best_new"]]:
        if key not in displayed:displayed.append(key)
    fig,ax=plt.subplots(figsize=(9,5),layout="constrained")
    ax.plot(u*1000,fexp,color="black",linewidth=2,label="SPT target")
    for key in displayed:ax.plot(u*1000,curves[key],label=key)
    ax.set(xlabel="Punch displacement (mm)",ylabel="Force (N)",title="Common frozen grid, no zero shift or smoothing");ax.legend()
    fig.savefig(OUT/"best_fd_comparison.png",dpi=170);plt.close(fig)
    # Analytic predictions from the frozen true-total law; never read a tensile experiment.
    chosen=low[:7]
    eps=np.linspace(0,.2,401)
    predicted=[]
    fig,ax=plt.subplots(figsize=(9,5),layout="constrained")
    for r in chosen:
        stress=np.array([stress_from_total_strain(float(e),r["sigma_y_mpa"],r["n"])/1e6 for e in eps])
        ax.plot(eps,stress,label=f"{r['candidate_id']}: sy={r['sigma_y_mpa']:.1f}, n={r['n']:.4f}")
        predicted.extend({"candidate_id":r["candidate_id"],"true_total_strain":float(e),"predicted_true_stress_mpa":float(s)} for e,s in zip(eps,stress))
    ax.set(xlabel="True total strain",ylabel="Predicted true stress (MPa)",title="SPT-informed candidate constitutive predictions; no tensile validation");ax.legend(fontsize=8)
    fig.savefig(OUT/"predicted_constitutive_curves.png",dpi=170);plt.close(fig)
    csv_write(OUT/"predicted_constitutive_curves.csv",predicted,["candidate_id","true_total_strain","predicted_true_stress_mpa"])
    save(OUT/"predicted_constitutive_provenance.json",{
        "generator_path":"inverse/hollomon.py","generator_sha256":sha(ROOT/"inverse/hollomon.py"),
        "law":"E*epsilon below epsilon_y; sigma_y*(epsilon/epsilon_y)^n above, epsilon_y=sigma_y/E",
        "strain":"true total strain","stress":"predicted true stress MPa","strain_range":[0,.2],
        "candidates":[{k:r[k] for k in ("candidate_id","sigma_y_mpa","n","loss")} for r in chosen],
        "scope":"SPT-derived predictions only; no tensile experiment or post-necking conversion used; not independently validated"})
    print(json.dumps({"software_completed":result["software_completed"],"scoreable":len(new_curves),"rows":[{k:r[k] for k in ("candidate_id","loss","rmse_n","quality")} for r in output],
                      "branches":{k:{z:v[z] for z in ("valid_count","best_so_far_loss","absolute_improvement_over_D01","actual_wall_s")} for k,v in branches.items()},"best":best["candidate_id"],"gp_diagnostics":gp_diag},ensure_ascii=False))


if __name__=="__main__":main()
