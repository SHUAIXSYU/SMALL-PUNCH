"""Measure only offline proposal time; verify byte-frozen candidate values."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from pilot import propose_bo, propose_de

ROOT=Path(r"E:\Projects\SMALL-PUNCH")
ART=ROOT/"run/run_040/artifacts"
DATA=json.loads((ART/"private/initial_dataset.json").read_text(encoding="utf-8"))
FROZEN=json.loads((ART/"private/candidate_manifest.json").read_text(encoding="utf-8"))


def main():
    t0=time.perf_counter()
    bo=propose_bo(DATA["valid"],DATA["invalid"])
    t1=time.perf_counter()
    de=propose_de(DATA["valid"],DATA["invalid"],
                  other_branch=[np.array([p["x"],p["y"]]) for p in bo["proposals"]])
    t2=time.perf_counter()
    for branch,proposals in (("BO",bo["proposals"]),("DE",de["proposals"])):
        expected=[p for p in FROZEN["points"] if p["algorithm"]==branch]
        assert all(a["sigma_y_mpa"]==b["sigma_y_mpa"] and a["n"]==b["n"]
                   for a,b in zip(proposals,expected))
    result={"at":datetime.now().astimezone().isoformat(),"BO_proposal_wall_s":t1-t0,
            "DE_proposal_wall_s":t2-t1,"solver_calls":0,"queue_writes":0,
            "scope":"one local repeat of offline proposal generation; not FE cost or a statistical runtime benchmark"}
    with (ART/"private/algorithm_runtime.json").open("x",encoding="utf-8") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2);stream.write("\n")
    print(json.dumps(result))


if __name__=="__main__":
    main()
