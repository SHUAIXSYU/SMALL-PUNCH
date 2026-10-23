"""Read only the explicit SPT model and run_014 identity inputs for run_016."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK_ID = "5e024e04-4f41-4fd8-a199-15b632ce6e79"
INP_REL = "run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp"
JNL_REL = "CAE/Models/Sanity/SP_InvOpt_Sanity_model.jnl"
DECL_REL = "run/run_016/artifacts/private/collaborator_declaration.json"
REQUEST_REL = "run/run_014/artifacts/request.json"
ENQUEUE_REL = "run/run_014/artifacts/enqueue_response.json"
OUT = ROOT / "run/run_016/artifacts/private/cae/model_facts.json"
EXPECTED_INP_SHA = "fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def block(lines: list[str], keyword: str, first: bool = False) -> tuple[int, list[str]]:
    matches = [i for i, line in enumerate(lines) if line.strip().lower() == keyword.lower()]
    if not matches or (not first and len(matches) != 1):
        raise ValueError(f"Expected exactly one {keyword}; found {len(matches)}")
    index = matches[0]
    rows = []
    for line in lines[index + 1:]:
        if line.lstrip().startswith("*"):
            break
        if line.strip():
            rows.append(line.strip())
    return index + 1, rows


def nset(lines: list[str], name: str) -> dict:
    line, rows = block(lines, f"*Nset, nset={name}")
    return {"line": line, "labels": [int(x) for row in rows for x in row.split(",") if x.strip()]}


def main() -> None:
    if OUT.exists():
        raise SystemExit("Refuse to overwrite prior facts")
    paths = [INP_REL, JNL_REL, DECL_REL, REQUEST_REL, ENQUEUE_REL]
    hashes = {rel: sha256(ROOT / rel) for rel in paths}
    if hashes[INP_REL] != EXPECTED_INP_SHA:
        raise ValueError("Run_008 candidate hash differs from run_014 request")
    lines = (ROOT / INP_REL).read_text(encoding="utf-8-sig").splitlines()
    declaration = json.loads((ROOT / DECL_REL).read_text(encoding="utf-8"))
    request = json.loads((ROOT / REQUEST_REL).read_text(encoding="utf-8"))
    enqueued = json.loads((ROOT / ENQUEUE_REL).read_text(encoding="utf-8"))
    if Path(request["inp_path"]).resolve() != (ROOT / INP_REL).resolve():
        raise ValueError("run_014 request points at a different INP")
    if request["metadata"]["inp_sha256"] != EXPECTED_INP_SHA:
        raise ValueError("run_014 request hash differs")
    if str((ROOT / INP_REL).resolve()) not in enqueued["command_preview"]:
        raise ValueError("run_014 enqueue command preview points at another INP")
    if enqueued["status"] != "ENQUEUED":
        raise ValueError("run_014 enqueue was not accepted")

    node_line, node_rows = block(lines, "*Node", first=True)
    # The first *Node in the input is the specimen Part; the punch instance has a second one.
    nodes = {}
    for row in node_rows:
        values = [x.strip() for x in row.split(",")]
        nodes[int(values[0])] = (float(values[1]), float(values[2]))
    if len(nodes) != 670:
        raise ValueError("Unexpected specimen node count")
    clamps = {}
    for name in ("set_specimen_clamped_top", "set_specimen_clamped_bot"):
        found = nset(lines, name)
        points = [nodes[label] for label in found["labels"]]
        clamps[name] = {"line": found["line"], "count": len(points),
                        "r_min_m": min(p[0] for p in points), "r_max_m": max(p[0] for p in points),
                        "z_min_m": min(p[1] for p in points), "z_max_m": max(p[1] for p in points)}
    punch_line, punch_rows = block(lines, "*Surface, type=SEGMENTS, name=surf_punch_contact")
    if len(punch_rows) != 2 or not punch_rows[0].upper().startswith("START") or not punch_rows[1].upper().startswith("CIRCL"):
        raise ValueError("Unexpected analytic punch segment")
    start = [float(x) for x in punch_rows[0].split(",")[1:]]
    circle = [float(x) for x in punch_rows[1].split(",")[1:]]
    end, center = circle[:2], circle[2:]
    radius = math.dist(end, center)
    if abs(radius - math.dist(start, center)) > 1e-12:
        raise ValueError("Punch arc radius inconsistent")
    if not math.isclose(radius, 0.00125, abs_tol=1e-12):
        raise ValueError("Punch radius changed")
    instances = [(i + 1, line.strip()) for i, line in enumerate(lines)
                 if line.strip().lower().startswith("*instance,")]
    parts = [(i + 1, line.strip()) for i, line in enumerate(lines)
             if line.strip().lower().startswith("*part,")]
    static_line, static_rows = block(lines, "*Static")
    friction_line = next(i + 1 for i, line in enumerate(lines)
                         if line.strip().lower().startswith("*friction,"))
    mu = float(lines[friction_line].strip().rstrip(","))
    punch_bc_line = next(i + 1 for i, line in enumerate(lines)
                         if line.strip() == "ASM_SPT.set_punch_rp, 2, 2, -0.0012")
    contact_line = next(i + 1 for i, line in enumerate(lines)
                        if line.strip() == "ASM_SPT-1.surf_specimen_top, ASM_SPT.surf_punch_contact")
    report = {
        "task_id": TASK_ID,
        "observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "source_sha256": hashes,
        "run014_input_identity": {"request_path": request["inp_path"],
                                  "request_sha256": request["metadata"]["inp_sha256"],
                                  "enqueue_job_id": enqueued["job_id"],
                                  "enqueue_status": enqueued["status"],
                                  "command_preview_contains_candidate_path": True},
        "model": {
            "parts": parts,
            "instances": instances,
            "specimen_node_line": node_line,
            "specimen_node_count": len(nodes),
            "specimen_radius_m": max(p[0] for p in nodes.values()),
            "specimen_thickness_m": max(p[1] for p in nodes.values()) - min(p[1] for p in nodes.values()),
            "clamp_node_sets": clamps,
            "punch_surface_line": punch_line,
            "punch_arc_radius_m": radius,
            "punch_arc_diameter_m": 2 * radius,
            "punch_local_start": start,
            "punch_local_end": end,
            "punch_local_center": center,
            "friction_line": friction_line,
            "friction_coefficient": mu,
            "static_line": static_line,
            "static_rows": static_rows,
            "punch_bc_u2_line": punch_bc_line,
            "contact_pair_data_line": contact_line,
            "explicit_lower_die_part": False,
        },
        "collaborator_declaration": {"specimen_thickness_mm": declaration["specimen_thickness_mm"],
                                     "specimen_diameter_mm": declaration["specimen_diameter_mm"],
                                     "lower_support_hole_diameter_mm": declaration["lower_support_hole_diameter_mm"],
                                     "punch_diameter_mm": None,
                                     "displacement": declaration["displacement"],
                                     "correction": declaration["correction"],
                                     "referenced_standard": declaration["other_settings_reference"]},
        "scope": "Read-only SPT inputs; no heldout validation content, no CAE save, no Abaqus execution",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "candidate_sha256": hashes[INP_REL],
                      "specimen_radius_m": report["model"]["specimen_radius_m"],
                      "specimen_thickness_m": report["model"]["specimen_thickness_m"],
                      "punch_diameter_m": report["model"]["punch_arc_diameter_m"],
                      "clamp_sets": clamps}, ensure_ascii=False))


if __name__ == "__main__":
    main()
