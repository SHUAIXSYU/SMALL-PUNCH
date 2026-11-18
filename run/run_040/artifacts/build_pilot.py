"""Freeze 19-point SPT-only data and offline BO/DE first-gate candidates."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import numpy as np

from pilot import (DE_CR, DE_F, DE_POPULATION, EI_XI_LOG1P, FAILED_DISTANCE,
                   MIN_BATCH_DISTANCE, MIN_EXISTING_DISTANCE, SEED, normalize,
                   propose_bo, propose_de, validate_dataset)

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
RUN=ROOT/"run/run_040"
ART=RUN/"artifacts"
PRIVATE=ART/"private"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):
            h.update(block)
    return h.hexdigest()


def save_new(path,data):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2)
        stream.write("\n")


def relative(path):
    return path.relative_to(ROOT).as_posix()


def stamp():
    return datetime.now().astimezone().isoformat()


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()


def main():
    assert sys.executable.lower()==r"d:\xianlab\envs\torch-gpu\python.exe"
    assert not (PRIVATE/"candidate_manifest.json").exists()
    previous=read(ROOT/"run/run_039/artifacts/private/main/main_review.json")
    previous_run=read(ROOT/"run/run_039/run.json")
    expected={v["path"]:v["sha256"] for v in previous_run["outputs"]}
    prior_path=ROOT/"run/run_039/artifacts/private/main/main_review.json"
    assert expected[relative(prior_path)]==digest(prior_path)
    assert previous["numeric_version"]=="run030-standard-m0025-hollomon-v1"
    assert previous["loss_version"]=="run017-exploratory-fd-v1"
    assert previous["independent_loss_recalculated"]==19
    model=ROOT/"run/run_030/artifacts/model_contract.json"
    binding=ROOT/"run/run_030/artifacts/loss_contract_binding.json"
    model_j=read(model); binding_j=read(binding)
    assert model_j["version"]==previous["numeric_version"]
    assert binding_j["version"]==previous["loss_version"]
    assert digest(ROOT/binding_j["target_path"])==binding_j["target_sha256"]
    assert digest(ROOT/binding_j["implementation_path"])==binding_j["implementation_sha256"]
    assert digest(binding)==previous["loss_binding_sha256"]
    good=[]; bad=[]
    for row in previous["rows"]:
        result_path=ROOT/row["result_path"]
        assert digest(result_path)==row["result_sha256"]
        result=read(result_path)
        assert result["inp_sha256"]==row["inp_sha256"]
        assert result["odb_sha256"]==row["odb_sha256"]
        assert result["queue_id"]==row["queue_id"]
        assert result["max_saved_peeq"]<.9
        curve=ROOT/result["positive_fd_csv"]
        assert curve.is_file()
        rec={"point_id":row["point_id"],"sigma_y_mpa":row["sigma_y_mpa"],"n":row["n"],
             "x":row["x"],"y":row["y"],"loss":row["loss"],"numerical_quality":row["numerical_quality"],
             "blocking_issues":row["blocking_issues"],"runtime_s":row["runtime_s"],
             "cutback":row["cutback"],"rejected_attempts":row["rejected_attempts"],
             "source_attempt":row["source_attempt"],"job_name":row["job_name"],"queue_id":row["queue_id"],
             "inp_sha256":row["inp_sha256"],"odb_sha256":row["odb_sha256"],
             "result_path":row["result_path"],"result_sha256":row["result_sha256"],
             "fd_path":relative(curve),"fd_sha256":digest(curve),
             "numeric_version":previous["numeric_version"],"loss_version":previous["loss_version"]}
        x=normalize(row["sigma_y_mpa"],row["n"])
        assert abs(x[0]-row["x"])<1e-12 and abs(x[1]-row["y"])<1e-12
        (good if row["loss"] is not None else bad).append(rec)
    validate_dataset(good,bad)
    assert sum(r["runtime_s"] for r in good+bad)==previous["totals"]["runtime_sum_22_completed_s"]
    initial={"version":"run040-shared-initial-19-v1","created_at":stamp(),
             "numeric_version":previous["numeric_version"],"model_contract_sha256":digest(model),
             "loss_version":previous["loss_version"],"loss_binding_sha256":digest(binding),
             "experimental_target_sha256":binding_j["target_sha256"],
             "source_main_review_path":relative(prior_path),"source_main_review_sha256":digest(prior_path),
             "valid_count":19,"invalid_count":3,"valid":good,"invalid":bad,
             "known_failure_rule":"Null scores are never imputed or trained as objective values; avoid radius 0.04 in normalized coordinates",
             "shared_historical_cost":{"software_completed_s":previous["totals"]["runtime_sum_22_completed_s"],
                                       "all_observed_attempts":24,"distinct_valid_evaluations":19,
                                       "invalid_parameter_points":3},
             "sealed_tensile_access":"PROHIBITED; historic information exposure retained"}
    if (PRIVATE/"initial_dataset.json").exists():
        saved=read(PRIVATE/"initial_dataset.json")
        assert {k:v for k,v in saved.items() if k!="created_at"}=={k:v for k,v in initial.items() if k!="created_at"}
    else:
        save_new(PRIVATE/"initial_dataset.json",initial)
    bo=propose_bo(good,bad)
    de=propose_de(good,bad,other_branch=[np.array([p["x"],p["y"]]) for p in bo["proposals"]])
    assert len(bo["proposals"])==len(de["proposals"])==4
    points=[]
    for branch,proposals in (("BO",bo["proposals"]),("DE",de["proposals"])):
        for item in proposals:
            idx=item["rank"]
            name=f"SPIO_R040_{branch}{idx:02d}"
            points.append({"candidate_id":f"{branch}{idx:02d}","algorithm":branch,
                           "job_name":name,"sigma_y_mpa":item["sigma_y_mpa"],"n":item["n"],
                           "x":item["x"],"y":item["y"],"proposal":item,
                           "inp_path":f"run/run_040/artifacts/candidates/{name}/{name}.inp",
                           "parameters_path":f"run/run_040/artifacts/candidates/{name}/parameters.json",
                           "working_dir":f"run/run_040/artifacts/solver/{name}",
                           "expected_odb":f"run/run_040/artifacts/solver/{name}/{name}.odb",
                           "numeric_version":previous["numeric_version"],"loss_version":previous["loss_version"],
                           "fe_status":"NOT_AUTHORIZED_NOT_QUEUED"})
    all_xy=np.array([[p["x"],p["y"]] for p in points])
    assert np.min(np.linalg.norm(all_xy[:,None,:]-all_xy[None,:,:]+np.eye(8)[:,:,None]*10,axis=2))>=MIN_BATCH_DISTANCE
    assert len(set(p["job_name"] for p in points))==8
    for p in points:
        assert not (ROOT/p["inp_path"]).exists()
        assert not (ROOT/p["working_dir"]).exists()
    contract={"version":"run040-bo-de-pilot-v1","created_at":stamp(),
              "shared_initial_dataset_path":"run/run_040/artifacts/private/initial_dataset.json",
              "shared_initial_dataset_sha256":digest(PRIVATE/"initial_dataset.json"),
              "numeric_version":previous["numeric_version"],"loss_version":previous["loss_version"],
              "bounds":{"sigma_y_mpa":[150,1000],"n":[.02,.5]},
              "normalization":"x=ln(sigma_y/150)/ln(1000/150); y=(n-0.02)/0.48",
              "seed":SEED,"first_gate_budget":{"BO":4,"DE":4,"new_fe_total":8},
              "overall_potential_budget":{"BO":8,"DE":8,"new_fe_total":16,"second_gate_requires_new_review_and_authorization":True},
              "BO":{"type":"offline batch BO, greedy kriging believer with posterior-mean fantasies",
                    "surrogate":"GaussianProcessRegressor on log1p(Loss), ARD Matern-5/2 + bounded WhiteKernel",
                    "normalization":"standardized GP target; inputs frozen x,y",
                    "hyperparameter_bounds":{"constant":[1e-3,1e3],"lengthscale_each":[.03,2],"noise":[1e-8,1e-3]},
                    "acquisition":"Expected Improvement; xi=0.005 on log1p(Loss)",
                    "candidate_pool":"2^14 scrambled Sobol points", "fantasies":"posterior mean; no real new FE observations",
                    "batch_size":4,"fit_warnings":bo["fit_warnings"],"fitted_kernel":bo["initial_kernel"]},
              "DE":{"variant":"rand/1/bin","population_size":DE_POPULATION,"F":DE_F,"CR":DE_CR,
                    "seed":SEED+1,"initial_population":"best valid point plus deterministic farthest-first seven from same 19; all 19 visible as historical archive",
                    "boundary":"reflect unit-square coordinates", "first_gate":"4 of 8 trial vectors, partial generation; no parent replacement until real FE",
                    "population_ids":de["population_ids"]},
              "shared_exclusions":{"min_distance_from_existing_valid":MIN_EXISTING_DISTANCE,
                                   "min_distance_from_known_invalid":FAILED_DISTANCE,
                                   "min_distance_between_any_first_gate_candidates":MIN_BATCH_DISTANCE,
                                   "invalid_ids":[r["point_id"] for r in bad],"invalid_loss":None},
              "fairness":{"common_initial_valid":19,"common_known_invalid":3,
                          "each_branch_can_see":"same frozen initial set plus own new results only",
                          "metrics":["best_so_far_loss","valid_fe_count","attempt_count","failure_rate","wall_clock",
                                     "parameter_spread","low_loss_equivalent_solutions","uncertainty","numerical_quality"],
                          "claim_limit":"single seed and four first-gate evaluations per branch cannot establish statistical superiority"},
              "future_acceptance":{"datacheck_and_full":"both terminal successful with provenance",
                                   "fd_window":"covers fixed 0–1.2 mm, 241 points, no extrapolation",
                                   "peeq":"max saved frame below actual material table coverage; rejected attempts separately reviewed",
                                   "warning":"accepted large strain, significant accepted force drop, distortion/contact anomalies require MAIN review; blocking result has null Loss",
                                   "attempts":"failed/unknown attempt consumes one new FE budget; no automatic retry or replacement"},
              "stop_gate":"Pause after first 4+4; pause earlier for identity uncertainty, incomplete output, blocking numerical warning or systemic failure",
              "solver_permission":"NONE; no queue or solver in this Run"}
    save_new(ART/"algorithm_contract.json",contract)
    candidate={"version":"run040-first-gate-eight-candidates-v1","created_at":stamp(),
               "contract_path":relative(ART/"algorithm_contract.json"),"contract_sha256":digest(ART/"algorithm_contract.json"),
               "initial_dataset_sha256":digest(PRIVATE/"initial_dataset.json"),
               "algorithm_implementation_path":"run/run_040/artifacts/pilot.py",
               "algorithm_implementation_sha256":digest(ART/"pilot.py"),
               "bo_model":{"fitted_kernel":bo["initial_kernel"],"fit_warnings":bo["fit_warnings"]},
               "de_population_ids":de["population_ids"],"points":points,
               "status":"PARAMETERS_FROZEN_INP_PENDING_CAE"}
    save_new(PRIVATE/"candidate_manifest.json",candidate)
    git_info={"branch":git("branch","--show-current"),"head":git("rev-parse","HEAD"),
              "remote":git("remote","-v"),"working_tree":git("status","--short")}
    start={"at":stamp(),"git":git_info,"python":sys.executable,
           "initial_dataset_sha256":digest(PRIVATE/"initial_dataset.json"),
           "algorithm_contract_sha256":digest(ART/"algorithm_contract.json"),
           "candidate_manifest_sha256":digest(PRIVATE/"candidate_manifest.json")}
    save_new(RUN/"checkpoints/start.json",start)
    run={"schema_version":"1.0","run_id":"run_040","stage":"BO/DE optimisation pilot preparation",
         "objective":"Freeze 19-point shared data, offline batch BO and partial-generation DE, prepare 8 preview-only candidates",
         "status":"RUNNING","start_time":start["at"],"end_time":None,
         "git_branch":git_info["branch"],"git_head":git_info["head"],"git":git_info,
         "python_interpreter":sys.executable,
         "inputs":[{"path":relative(prior_path),"role":"frozen 22-point MAIN review","sha256":digest(prior_path)},
                   {"path":relative(model),"role":"numeric/model contract","sha256":digest(model)},
                   {"path":relative(binding),"role":"SPT loss binding","sha256":digest(binding)}],
         "outputs":[{"path":relative(PRIVATE/"initial_dataset.json"),"role":"private shared evaluations","sha256":start["initial_dataset_sha256"]},
                    {"path":relative(ART/"algorithm_contract.json"),"role":"algorithm and fairness protocol","sha256":start["algorithm_contract_sha256"]},
                    {"path":relative(PRIVATE/"candidate_manifest.json"),"role":"private frozen eight candidate parameters","sha256":start["candidate_manifest_sha256"]}],
         "validation":[{"check":"input_19_valid_3_null","status":"PASS","evidence":"all source hashes and contract identities verified"},
                       {"check":"CAE_and_preview","status":"PENDING","evidence":"parameters frozen, task to be dispatched"}],
         "errors":[]}
    save_new(RUN/"run.json",run)
    (RUN/"summary.md").write_text("# run_040 — BO/DE 先导离线准备\n\nRUNNING：19点共享数据与8个候选参数已冻结；等待真实CAE准备和工程预览。\n",encoding="utf-8")
    print(json.dumps({"status":"CANDIDATES_FROZEN","candidate_manifest_sha256":start["candidate_manifest_sha256"],
                      "bo_kernel":bo["initial_kernel"],"bo_fit_warnings":bo["fit_warnings"],
                      "points":[{"id":p["candidate_id"],"sigma_y_mpa":p["sigma_y_mpa"],"n":p["n"]} for p in points]},ensure_ascii=False))


if __name__=="__main__":
    main()
