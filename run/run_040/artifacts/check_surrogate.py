"""Offline leave-one-out diagnostic for the frozen first-gate GP kernel."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np

from pilot import _fit_gp, validate_dataset

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
DATA=ROOT/"run/run_040/artifacts/private/initial_dataset.json"
OUT=ROOT/"run/run_040/artifacts/private/surrogate_check.json"


def main():
    data=json.loads(DATA.read_text(encoding="utf-8"))
    valid=data["valid"]; bad=data["invalid"]
    x,loss,_=validate_dataset(valid,bad)
    y=np.log1p(loss)
    full,warnings=_fit_gp(x,y)
    predictions=[]
    for i,row in enumerate(valid):
        mask=np.arange(len(valid))!=i
        loo,_=_fit_gp(x[mask],y[mask],kernel=full.kernel_,optimize=False)
        mean,std=loo.predict(x[i:i+1],return_std=True)
        predictions.append({"point_id":row["point_id"],"true_log1p_loss":float(y[i]),
                            "pred_log1p_loss":float(mean[0]),"pred_std":float(std[0]),
                            "absolute_error_log1p":float(abs(mean[0]-y[i])),
                            "covered_95pct_approx":bool(abs(mean[0]-y[i])<=1.96*std[0])})
    errors=np.array([p["absolute_error_log1p"] for p in predictions])
    payload={"version":"run040-gp-loo-diagnostic-v1","at":datetime.now().astimezone().isoformat(),
             "kernel_fitted_on_all_19":str(full.kernel_),"fit_warnings":warnings,
             "method":"leave one point out; freeze full-data hyperparameters for diagnostic; no Abaqus calls",
             "mean_abs_error_log1p":float(np.mean(errors)),"median_abs_error_log1p":float(np.median(errors)),
             "max_abs_error_log1p":float(np.max(errors)),
             "approx_95pct_coverage":sum(p["covered_95pct_approx"] for p in predictions)/len(predictions),
             "results":predictions,
             "interpretation_limit":"19 sparse points, fixed-kernel LOO is not calibrated predictive validation or material uncertainty"}
    with OUT.open("x",encoding="utf-8") as stream:
        json.dump(payload,stream,ensure_ascii=False,indent=2);stream.write("\n")
    print(json.dumps({k:payload[k] for k in ("kernel_fitted_on_all_19","fit_warnings","mean_abs_error_log1p","median_abs_error_log1p","max_abs_error_log1p","approx_95pct_coverage")},ensure_ascii=False))


if __name__=="__main__":
    main()
