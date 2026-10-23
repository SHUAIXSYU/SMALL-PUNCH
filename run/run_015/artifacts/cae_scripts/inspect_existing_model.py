"""Read-only static geometry and loading extraction from the existing INP/JNL."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
INP_REL = "run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp"
JNL_REL = "CAE/Models/Sanity/SP_InvOpt_Sanity_model.jnl"
SOURCE_INP_REL = "CAE/Models/Sanity/Job-1.inp"
OUT = ROOT / "run/run_015/artifacts/private/cae/model_geometry_raw.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def section(lines: list[str], keyword: str) -> list[tuple[int, list[str]]]:
    found = []
    for index, line in enumerate(lines):
        if line.strip().lower().startswith(keyword.lower()):
            data = []
            for following in lines[index + 1:]:
                if following.lstrip().startswith("*"):
                    break
                if following.strip():
                    data.append(following.strip())
            found.append((index + 1, data))
    return found


def nset(lines: list[str], name: str) -> tuple[int, list[int]]:
    key = f"*Nset, nset={name}"
    matches = section(lines, key)
    if len(matches) != 1:
        raise ValueError(f"Expected one {key}; found {len(matches)}")
    line_number, data = matches[0]
    values = [int(cell) for row in data for cell in row.split(",") if cell.strip()]
    return line_number, values


def main() -> None:
    if OUT.exists():
        raise SystemExit("Refuse to overwrite existing model geometry evidence")
    inp_path = ROOT / INP_REL
    jnl_path = ROOT / JNL_REL
    source_path = ROOT / SOURCE_INP_REL
    lines = inp_path.read_text(encoding="utf-8-sig").splitlines()
    jnl = jnl_path.read_text(encoding="mbcs").splitlines()
    parts = [(i + 1, line.strip()) for i, line in enumerate(lines)
             if line.strip().lower().startswith("*part,")]
    assert len(parts) == 2 and "part_punch" in parts[0][1] and "part_specimen" in parts[1][1]
    node_start = next(i for i, line in enumerate(lines) if line.strip() == "*Node")
    node_end = next(i for i in range(node_start + 1, len(lines)) if lines[i].lstrip().startswith("*"))
    nodes = {}
    for row in lines[node_start + 1:node_end]:
        if not row.strip():
            continue
        cells = [c.strip() for c in row.split(",")]
        nodes[int(cells[0])] = (float(cells[1]), float(cells[2]))
    elements = section(lines, "*Element, type=CAX4")
    assert len(elements) == 1
    element_count = len(elements[0][1])
    sets = {}
    for name in ("set_specimen_clamped_top", "set_specimen_clamped_bot"):
        line_number, labels = nset(lines, name)
        points = [nodes[label] for label in labels]
        sets[name] = {"line": line_number, "node_count": len(labels),
                      "r_min": min(p[0] for p in points), "r_max": max(p[0] for p in points),
                      "z_min": min(p[1] for p in points), "z_max": max(p[1] for p in points)}
    surface = section(lines, "*Surface, type=SEGMENTS, name=surf_punch_contact")
    assert len(surface) == 1 and len(surface[0][1]) == 2
    start = [float(x) for x in surface[0][1][0].split(",")[1:]]
    circle = [float(x) for x in surface[0][1][1].split(",")[1:]]
    end = circle[:2]
    center = circle[2:]
    radius_from_start = math.dist(start, center)
    radius_from_end = math.dist(end, center)
    assert abs(radius_from_start - radius_from_end) < 1e-12
    instance_line = next(i for i, line in enumerate(lines)
                         if line.strip().lower() == "*instance, name=asm_spt, part=part_punch")
    translation = [float(x) for x in lines[instance_line + 1].split(",")]
    assert len(translation) == 3
    static = section(lines, "*Static")
    assert len(static) == 1
    static_values = [float(x) for x in static[0][1][0].split(",")]
    friction = section(lines, "*Friction, slip tolerance=")
    assert len(friction) == 1
    mu = float(friction[0][1][0].rstrip(","))
    bc_blocks = section(lines, "*Boundary")
    boundary = [{"line": line, "rows": data} for line, data in bc_blocks]
    report = {
        "observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "sources": [{"path": INP_REL, "sha256": sha256(inp_path)},
                    {"path": JNL_REL, "sha256": sha256(jnl_path)},
                    {"path": SOURCE_INP_REL, "sha256": sha256(source_path)}],
        "part_keywords": parts,
        "specimen": {"node_keyword_line": node_start + 1, "node_count": len(nodes),
                     "element_keyword_line": elements[0][0], "cax4_element_count": element_count,
                     "r_min": min(x for x, _ in nodes.values()),
                     "r_max": max(x for x, _ in nodes.values()),
                     "z_min": min(z for _, z in nodes.values()),
                     "z_max": max(z for _, z in nodes.values()),
                     "clamp_boundary_node_sets": sets},
        "punch": {"surface_line": surface[0][0], "arc_start_local": start,
                  "arc_end_local": end, "arc_center_local": center,
                  "arc_radius_from_start": radius_from_start,
                  "arc_radius_from_end": radius_from_end,
                  "instance_translation": translation,
                  "lowest_point_global_z": end[1] + translation[1]},
        "contact": {"friction_keyword_line": friction[0][0], "mu": mu,
                    "friction_slip_tolerance": 0.005,
                    "normal_behavior": "HARD",
                    "contact_pair": "ASM_SPT-1.surf_specimen_top, ASM_SPT.surf_punch_contact"},
        "step": {"static_keyword_line": static[0][0],
                 "static_values_initial_period_min_max": static_values,
                 "boundary_blocks": boundary},
        "jnl_crosscheck": {"specimen_rectangle_line": 22,
                           "final_punch_radius_line": 153,
                           "final_punch_center_line": 157,
                           "assembly_translation_line": 707,
                           "punch_rotation_bc_final_line": 1124,
                           "jnl_line_count": len(jnl)},
        "units_encoded_in_inp": None,
        "scope": "Static text and coordinate extraction only; does not read or save CAE binary, run Abaqus, or establish experiment correspondence",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUT), "node_count": len(nodes),
                      "element_count": element_count, "specimen": report["specimen"],
                      "punch": report["punch"], "step": {"static": static_values, "bc": boundary}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
