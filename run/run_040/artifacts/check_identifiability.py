"""Descriptive SPT-only compensation and boundary diagnostics from actual FE points."""
from __future__ import annotations

import itertools
import json
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
SOURCE=ROOT/"run/run_039/artifacts/private/main/main_review.json"
OUT=ROOT/"run/run_040/artifacts/private/identifiability.json"


def main():
    prior=json.loads(SOURCE.read_text(encoding="utf-8"))
    rows=prior["rows"]
    low=[r for r in rows if r["loss"] is not None and r["loss"]<=.01]
    assert len(low)==5
    xy=np.array([[r["x"],r["y"]] for r in low])
    all_corr=float(np.corrcoef(xy.T)[0,1])
    jackknife=[]
    for i,r in enumerate(low):
        mask=np.arange(5)!=i
        jackknife.append({"left_out":r["point_id"],"correlation":float(np.corrcoef(xy[mask].T)[0,1])})
    a=next(r for r in low if r["point_id"]=="D01")
    b=next(r for r in low if r["point_id"]=="I08")
    pair=next(p for p in prior["low_loss_pairwise_fe_curve_similarity"] if {p["a"],p["b"]}=={"D01","I08"})
    values={"version":"run040-spt-identifiability-descriptive-v1",
            "at":datetime.now().astimezone().isoformat(),
            "source":"run/run_039/artifacts/private/main/main_review.json",
            "low_loss_selection":"actual frozen Loss <= 0.01; descriptive only, five observed points",
            "low_loss_ids":[r["point_id"] for r in low],"low_loss_normalized_correlation":all_corr,
            "four_of_five_leave_one_out_correlations":jackknife,
            "D01_vs_I08":{"sigma_y_difference_mpa":b["sigma_y_mpa"]-a["sigma_y_mpa"],
                          "n_difference":b["n"]-a["n"],
                          "D01_distance_above_lower_bound_mpa":a["sigma_y_mpa"]-150,
                          "loss_difference":b["loss"]-a["loss"],
                          "same_grid_fe_curve_rmse_n":pair["force_rmse_n"]},
            "conclusion":"Compensation direction supported by sparse evaluated points, continuous valley and uniqueness unknown; D01 near sigma_y lower bound. No boundary expansion.",
            "sealed_tensile_access":False}
    with OUT.open("x",encoding="utf-8") as stream:
        json.dump(values,stream,ensure_ascii=False,indent=2);stream.write("\n")
    print(json.dumps({"correlation":all_corr,"jackknife_range":[min(v["correlation"] for v in jackknife),
               max(v["correlation"] for v in jackknife)],"D01_I08":values["D01_vs_I08"]},ensure_ascii=False))


if __name__=="__main__":
    main()
