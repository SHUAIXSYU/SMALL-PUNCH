"""Generate five offline material-only INP variants from the frozen run_017 design.

No Abaqus import, datacheck, queue or solver operation occurs here. Output paths
must be absent; the run_008 source is read as immutable bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from inverse.hollomon import generate_hollomon_table, stress_at_plastic_strain

TASK_ID = "64ade6c7-71f6-40ea-9ecc-b70f459773fb"
BASE_REL = "run/run_008/artifacts/candidate_inp/SPIO_R008_Q200_N010_Candidate/SPIO_R008_Q200_N010_Candidate.inp"
BASE_SHA = "fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a"
DESIGN_REL = "run/run_017/artifacts/parameter_design.json"
DESIGN_SHA = "e2fb810634997499765b04576f82062c088ec60829ff2b702abc3fe815eaac6b"
META_REL = "run/run_017/artifacts/private/experimental_metadata.json"
REQUEST_REL = "run/run_014/artifacts/request.json"
ENQUEUE_REL = "run/run_014/artifacts/enqueue_response.json"
MANIFEST_REL = "run/run_017/artifacts/cae_candidate_manifest.json"
CHECKS_REL = "run/run_017/artifacts/private/cae/static_checks.json"
REPORT_REL = "run/run_017/artifacts/private/cae/qualification_report.md"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def nset(lines: list[str], name: str) -> list[int]:
    marker = f"*nset, nset={name}".lower()
    places = [i for i, s in enumerate(lines) if s.strip().lower() == marker]
    require(len(places) == 1, f"NSET_{name}_NOT_UNIQUE")
    labels: list[int] = []
    for s in lines[places[0] + 1:]:
        if s.lstrip().startswith("*"):
            break
        labels.extend(int(item) for item in s.split(",") if item.strip())
    return labels


def geometry_gate(text: str, meta: dict) -> dict:
    lines = text.splitlines()
    stripped = [s.strip() for s in lines]
    parts = [s for s in stripped if s.lower().startswith("*part,")]
    require(parts == ["*Part, name=part_punch", "*Part, name=part_specimen"], "MODEL_PARTS_DIFFER")
    require(not any(re.match(r"^\*include\b", s, re.I) for s in stripped), "EXTERNAL_INCLUDE_FOUND")
    node_start = stripped.index("*Node")
    nodes = {}
    for s in stripped[node_start + 1:]:
        if s.startswith("*"):
            break
        fields = [v.strip() for v in s.split(",")]
        nodes[int(fields[0])] = (float(fields[1]), float(fields[2]))
    require(len(nodes) == 670, "SPECIMEN_NODE_COUNT_DIFFERS")
    radius = max(r for r, _ in nodes.values())
    thickness = max(z for _, z in nodes.values()) - min(z for _, z in nodes.values())
    require(abs(radius * 2000 - meta["specimen_diameter_mm"]) < 1e-5, "SPECIMEN_DIAMETER_MISMATCH")
    require(abs(thickness * 1000 - meta["specimen_thickness_mm"]) < 1e-6, "SPECIMEN_THICKNESS_MISMATCH")
    arc = stripped.index("*Surface, type=SEGMENTS, name=surf_punch_contact")
    start = [float(v) for v in stripped[arc + 1].split(",")[1:]]
    circle = [float(v) for v in stripped[arc + 2].split(",")[1:]]
    punch_r = math.dist(circle[:2], circle[2:])
    require(math.isclose(math.dist(start, circle[2:]), punch_r, abs_tol=1e-12), "PUNCH_ARC_INCONSISTENT")
    require(abs(2000 * punch_r - meta["punch_diameter_mm"]) < 1e-6, "PUNCH_DIAMETER_MISMATCH")
    inst = stripped.index("*Instance, name=ASM_SPT, part=part_punch")
    punch_translation_z = float(stripped[inst + 1].split(",")[1])
    require(abs(punch_translation_z + circle[1] - thickness) < 1e-9, "PUNCH_TIP_START_MISMATCH")
    clamps = {}
    for name, z_expect in (("set_specimen_clamped_top", thickness), ("set_specimen_clamped_bot", 0.0)):
        labels = nset(lines, name)
        require(len(labels) == 16, f"NSET_{name}_SIZE_DIFFERS")
        radii = [nodes[label][0] for label in labels]
        zs = [nodes[label][1] for label in labels]
        require(max(abs(z - z_expect) for z in zs) < 1e-9, f"NSET_{name}_Z_DIFFERS")
        require(abs(2000 * min(radii) - meta["lower_support_hole_diameter_mm"]) < 1e-5,
                f"NSET_{name}_INNER_SPAN_DIFFERS")
        require(abs(max(radii) - radius) < 1e-9, f"NSET_{name}_OUTER_RADIUS_DIFFERS")
        require(all(f"ASM_SPT-1.{name}, {d}, {d}" in stripped for d in (1, 2)),
                f"NSET_{name}_BOUNDARY_DIFFERS")
        clamps[name] = {"nodes": len(labels), "r_min_m": min(radii), "r_max_m": max(radii),
                        "z_m": z_expect, "u1_fixed": True, "u2_fixed": True}
    require("ASM_SPT-1.surf_specimen_top, ASM_SPT.surf_punch_contact" in stripped,
            "PUNCH_CONTACT_MISSING")
    friction = stripped.index("*Friction, slip tolerance=0.005")
    require(abs(float(stripped[friction + 1].rstrip(",")) - 0.1) < 1e-12, "FRICTION_DIFFERS")
    require("*Surface Behavior, pressure-overclosure=HARD" in stripped, "CONTACT_NORMAL_DIFFERS")
    require("*Step, name=Step_Punch_Displacement, nlgeom=YES, inc=999999" in stripped,
            "STEP_DIFFERS")
    require("*Static" in stripped, "STATIC_STEP_MISSING")
    require("ASM_SPT.set_punch_rp, 2, 2, -0.0012" in stripped, "PUNCH_DIRECTION_OR_SPAN_DIFFERS")
    require("RF2, U2" in stripped, "PUNCH_OUTPUT_DIFFERS")
    require(stripped.count("*Material, name=Q200N01") == 1, "LEGACY_MATERIAL_NOT_UNIQUE")
    require(stripped.count("*Elastic") == 1 and stripped.count("*Plastic") == 1,
            "MATERIAL_KEYWORDS_NOT_UNIQUE")
    elastic = stripped.index("*Elastic")
    young, nu = (float(v) for v in stripped[elastic + 1].split(","))
    require(young == 210e9 and nu == 0.3, "ELASTIC_BASELINE_DIFFERS")
    return {"specimen_diameter_mm": 2000 * radius, "specimen_thickness_mm": 1000 * thickness,
            "punch_diameter_mm": 2000 * punch_r, "lower_free_span_mm": 2000 * min(nodes[label][0] for label in nset(lines,"set_specimen_clamped_bot")),
            "punch_tip_at_specimen_top": True, "punch_u2_end_m": -0.0012,
            "clamps": clamps, "contact_friction": 0.1, "elastic_E_pa": young,
            "elastic_nu": nu, "lower_die_explicit": False, "include_count": 0,
            "qualification": "MATCHED_DECLARED_DIMENSIONS; IDEALISED_CLAMPING_BASELINE_ONLY"}


def plastic_boundary(lines: list[str]) -> tuple[int, int]:
    starts = [i for i, s in enumerate(lines) if s.startswith("** CANDIDATE ONLY:")]
    plastics = [i for i, s in enumerate(lines) if s.strip().lower() == "*plastic"]
    require(len(starts) == len(plastics) == 1 and starts[0] < plastics[0], "PLASTIC_BOUNDARY_UNEXPECTED")
    end = next((i for i in range(plastics[0] + 1, len(lines)) if lines[i].lstrip().startswith("*")), None)
    require(end is not None and lines[end].strip() == "**", "PLASTIC_END_UNEXPECTED")
    return starts[0], end


def table_check(table, sigma_y_mpa: float, n: float) -> dict:
    rows = table.rows
    require(len(rows) >= 2, "TABLE_TOO_SHORT")
    require(rows[0][1] == 0 and math.isclose(rows[0][0], sigma_y_mpa * 1e6, rel_tol=1e-15),
            "TABLE_FIRST_POINT")
    require(rows[-1][1] == 0.9, "TABLE_COVERAGE")
    require(all(a[0] < b[0] and a[1] < b[1] for a, b in zip(rows, rows[1:])),
            "TABLE_NONMONOTONE")
    require(table.conservative_relative_error_bound <= 0.001000000000001,
            "GENERATOR_RELATIVE_BOUND_EXCEEDED")
    max_sampled = 0.0
    for (s0, p0), (s1, p1) in zip(rows, rows[1:]):
        for fraction in (0.25, 0.5, 0.75):
            p = p0 + (p1 - p0) * fraction
            chord = s0 + (s1 - s0) * fraction
            analytic = stress_at_plastic_strain(p, sigma_y_mpa, n)
            max_sampled = max(max_sampled, abs(chord - analytic) / analytic)
    require(max_sampled <= 0.001000000000001, "SAMPLED_INTERPOLATION_ERROR")
    return {"rows": len(rows), "first_stress_pa": rows[0][0], "first_plastic_strain": rows[0][1],
            "last_plastic_strain": rows[-1][1],
            "max_sampled_relative_interpolation_error": max_sampled,
            "conservative_relative_error_bound": table.conservative_relative_error_bound,
            "max_normalized_error_bound": table.max_normalized_error_bound,
            "strictly_increasing_stress_and_strain": True}


def main() -> None:
    source = (ROOT / BASE_REL).read_bytes()
    design_bytes = (ROOT / DESIGN_REL).read_bytes()
    require(digest(source) == BASE_SHA and digest(design_bytes) == DESIGN_SHA,
            "FROZEN_SOURCE_OR_DESIGN_HASH_MISMATCH")
    design = json.loads(design_bytes)
    meta = read_json(META_REL)
    request = read_json(REQUEST_REL)
    enqueue = read_json(ENQUEUE_REL)
    require(Path(request["inp_path"]).resolve() == (ROOT / BASE_REL).resolve()
            and request["metadata"]["inp_sha256"] == BASE_SHA, "RUN014_REQUEST_IDENTITY_MISMATCH")
    require(enqueue["status"] == "ENQUEUED" and str((ROOT / BASE_REL).resolve()) in enqueue["command_preview"],
            "RUN014_ENQUEUE_IDENTITY_MISMATCH")
    require(meta["force_unit"] == "N" and meta["displacement_unit"] == "mm"
            and meta["displacement_sensor"] == "actual punch displacement", "EXPERIMENT_UNITS_UNCONFIRMED")
    require("idealised clamping baseline" in meta["model_permission"], "BASELINE_PERMISSION_MISSING")
    fixed = design["fixed"]
    require(fixed == {"E_pa": 210000000000.0, "nu": 0.3, "max_plastic_strain": 0.9,
                      "model_id": "candidate-true-total-hollomon-v1",
                      "material_interpolation_relative_tolerance": 0.001}, "FROZEN_MATERIAL_CONTRACT_DIFFERS")
    require(len(design["points"]) == 5, "DESIGN_NOT_FIVE_POINTS")
    text = source.decode("utf-8")
    geometry = geometry_gate(text, meta)
    lines = text.splitlines(keepends=True)
    start, end = plastic_boundary(lines)
    prefix = "".join(lines[:start]).encode("utf-8")
    suffix = "".join(lines[end:]).encode("utf-8")
    nonmaterial_sha = digest(prefix + suffix)
    output_paths: list[Path] = [ROOT / MANIFEST_REL, ROOT / CHECKS_REL, ROOT / REPORT_REL]
    for point in design["points"]:
        output_paths.extend((ROOT / point["inp_path"], ROOT / point["parameters_path"],
                             ROOT / point["working_dir"]))
    require(len(set(output_paths)) == len(output_paths), "OUTPUT_PATHS_NOT_UNIQUE")
    require(all(not p.exists() for p in output_paths), "OUTPUT_EXISTS_REFUSE_OVERWRITE")
    require(all((ROOT / p["working_dir"]).is_relative_to(ROOT / "run/run_017/artifacts/solver")
                for p in design["points"]), "WORKING_DIR_OUTSIDE_RUN017")
    prepared = []
    point_rows = []
    seen_jobs, seen_pairs, seen_inps = set(), set(), set()
    for point in design["points"]:
        name = point["job_name"]
        require(re.fullmatch(r"SPIO_R017_P0[1-5]_[A-Z]+", name) is not None,
                "JOB_NAME_INVALID")
        require(point["inp_path"].startswith(f"run/run_017/artifacts/candidates/{name}/")
                and point["inp_path"].endswith(f"/{name}.inp"), "INP_PATH_INVALID")
        require(point["parameters_path"] == f"run/run_017/artifacts/candidates/{name}/parameters.json",
                "PARAMETERS_PATH_INVALID")
        require(point["working_dir"] == f"run/run_017/artifacts/solver/{name}", "WORK_DIR_INVALID")
        require(point["expected_odb"] == f"{point['working_dir']}/{name}.odb", "ODB_PATH_INVALID")
        sigma, n = point["sigma_y_mpa"], point["n"]
        require(math.isfinite(sigma) and 150 <= sigma <= 1000 and math.isfinite(n)
                and 0.02 <= n <= 0.5 and 0 < n < 1, "PARAMETER_OUTSIDE_FROZEN_DOMAIN")
        require(abs(math.log(sigma / 150) / math.log(1000 / 150) - point["x"]) < 1e-13
                and abs((n - 0.02) / 0.48 - point["y"]) < 1e-13, "DESIGN_COORDINATE_MISMATCH")
        require(name not in seen_jobs and (sigma, n) not in seen_pairs, "DUPLICATE_JOB_OR_PARAMETERS")
        seen_jobs.add(name); seen_pairs.add((sigma, n))
        table = generate_hollomon_table(sigma, n, max_plastic_strain=0.9,
                                        relative_tolerance=0.001)
        quality = table_check(table, sigma, n)
        comments = (f"** RUN_017 POINT {point['point_id']} JOB {name}; input only, no solver authorization\n"
                    f"** sigma_y_MPa={sigma:.17g}; n={n:.17g}; design_sha256={DESIGN_SHA}\n")
        block = (comments + table.abaqus_plastic_text()).encode("utf-8")
        data = prefix + block + suffix
        require(digest(data[:len(prefix)] + data[-len(suffix):]) == nonmaterial_sha,
                "NONMATERIAL_BYTES_CHANGED")
        require(data.count(b"*Plastic\n") == 1, "OUTPUT_PLASTIC_COUNT")
        require(data.count(b"*Elastic\n") == 1, "OUTPUT_ELASTIC_COUNT")
        parsed_rows = []
        for line in table.abaqus_plastic_text().split("*Plastic\n", 1)[1].splitlines():
            values = [float(v) for v in line.split(",")]
            parsed_rows.append((values[0], values[1]))
        require(len(parsed_rows) == len(table.rows) and all(
                math.isclose(a[0], b[0], rel_tol=1e-15) and math.isclose(a[1], b[1], rel_tol=1e-15, abs_tol=1e-18)
                for a, b in zip(parsed_rows, table.rows)), "TABLE_SERIALIZATION_LOSS")
        inp_sha = digest(data)
        require(inp_sha not in seen_inps, "DUPLICATE_INP_HASH")
        seen_inps.add(inp_sha)
        params = {"schema": "sp_invopt.cae.parameters.v1", "task_id": TASK_ID,
                  "point_id": point["point_id"], "job_name": name, "sigma_y_mpa": sigma,
                  "n": n, "E_pa": fixed["E_pa"], "nu": fixed["nu"],
                  "material_model": fixed["model_id"], "stress_unit": "Pa",
                  "plastic_strain": "equivalent plastic strain, dimensionless",
                  "max_plastic_strain": 0.9, "relative_tolerance": 0.001,
                  "baseline_inp_sha256": BASE_SHA, "design_sha256": DESIGN_SHA,
                  "inp_sha256": inp_sha, "material_table_quality": quality,
                  "physical_validation": "NOT_EVALUATED"}
        prepared.append((point, data, json.dumps(params, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"))
        point_rows.append({"point_id": point["point_id"], "role": point["role"],
                           "job_name": name, "parameters": {"sigma_y_mpa": sigma, "n": n,
                           "E_pa": fixed["E_pa"], "nu": fixed["nu"],
                           "max_plastic_strain": 0.9, "relative_tolerance": 0.001},
                           "parameters_path": point["parameters_path"],
                           "inp_path": point["inp_path"], "sha256": inp_sha,
                           "working_dir": point["working_dir"],
                           "expected_outputs": {"odb": point["expected_odb"],
                           "dat": f"{point['working_dir']}/{name}.dat",
                           "msg": f"{point['working_dir']}/{name}.msg",
                           "sta": f"{point['working_dir']}/{name}.sta",
                           "log": f"{point['working_dir']}/{name}.log"},
                           "expected_outputs_status": "NOT_CREATED",
                           "material_rows": quality["rows"],
                           "max_sampled_relative_interpolation_error": quality["max_sampled_relative_interpolation_error"],
                           "generator_relative_error_bound": quality["conservative_relative_error_bound"],
                           "nonmaterial_sha256": nonmaterial_sha})
    manifest = {"schema": "sp_invopt.cae.candidate_manifest.v1", "task_id": TASK_ID,
                "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                "source": {"baseline_inp": BASE_REL, "baseline_sha256": BASE_SHA,
                           "design": DESIGN_REL, "design_sha256": DESIGN_SHA,
                           "experimental_metadata": META_REL,
                           "experimental_metadata_sha256": digest((ROOT / META_REL).read_bytes()),
                           "hollomon_generator": "inverse/hollomon.py",
                           "hollomon_sha256": digest((ROOT / "inverse/hollomon.py").read_bytes())},
                "material_contract": fixed, "model_qualification": geometry["qualification"],
                "legacy_abaqus_material_name": "Q200N01",
                "legacy_material_name_note": "Kept unchanged so only the original Plastic block/comments vary; actual parameters are in each point JSON.",
                "nonmaterial_sha256": nonmaterial_sha,
                "nonmaterial_definition": "SHA-256 of exact baseline bytes outside candidate comments and Plastic block; identical for all generated INPs",
                "points": point_rows, "new_fe_authorized": 0, "solver_or_queue_action": False,
                "future_gate": "Check each future ODB maximum PEEQ <= 0.9; no extrapolation guarantee now."}
    checks = {"schema": "sp_invopt.cae.static_checks.v1", "task_id": TASK_ID,
              "observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
              "baseline_input_identity": "PASS", "design_hash": "PASS",
              "parameter_domain_and_uniqueness": "PASS", "model_geometry_dimensions": geometry,
              "external_includes": "NONE", "candidate_count": 5,
              "plastic_first_point_monotonicity_coverage_interpolation": "PASS",
              "nonmaterial_bytes_preserved": "PASS", "unique_jobs_paths_hashes": "PASS",
              "work_dirs_empty_before_creation": "PASS_ABSENT",
              "abaqus_execution": "NOT_PERFORMED", "preflight_dry_run": "MAIN_RESPONSIBILITY",
              "future_peeq_adequacy": "UNKNOWN_PENDING_FUTURE_ODB",
              "fixture_equivalence": "IDEALISED_CLAMPING_BASELINE_ONLY",
              "experimental_displacement_mapping": "CORRECTION_DETAILS_UNKNOWN"}
    report = f"""# run_017 CAE five-point qualification

- Task: `{TASK_ID}`; status **offline inputs prepared**; scientific state **NOT_EVALUATED**.
- Actual run_014 input matches run_008 baseline `{BASE_SHA}`; design SHA-256 `{DESIGN_SHA}`.
- Declared specimen 10 × 0.5 mm, punch 2.5 mm and lower aperture 4 mm match the candidate's nominal geometry. Both outer annuli from radius 2 to 5 mm are fixed in U1/U2. This is the user-authorized **idealised clamping baseline**, not a demonstration of full fixture contact equivalence.
- Punch tip starts at specimen top and moves in negative U2; output requests RP RF2/U2. The experiment reports corrected actual punch displacement in mm and force in N. Correction details remain unknown; no secondary correction was applied.
- Only candidate comments and the `*Plastic` block changed. The legacy Abaqus material name `Q200N01` was retained as a stable reference; each point's parameters JSON is the authoritative identity. Elastic E=210 GPa and ν=0.3, mesh, geometry, BC, contact, steps and output requests remain byte-identical.
- Five unique INPs use `inverse/hollomon.py` with true-total-strain candidate interpretation, pmax=0.9 and relative interpolation tolerance 0.001. Each table starts at plastic strain 0, strictly increases and covers 0.9. Independent quarter/mid/three-quarter chord checks plus the generator's conservative bound passed; full metrics are in `static_checks.json` and the manifest.
- No `*Include` dependency, prior output in designated work directories, Abaqus command, datacheck, Solver or queue mutation. Work directories were created empty for future use. MAIN owns public preflight/dry-run.
- **Future gate:** each future ODB must demonstrate maximum PEEQ within 0.9; this preparation cannot establish future coverage or FE convergence. Fixture details and the experiment's displacement-correction algorithm remain limitations.
"""
    # No file or work directory is created until every point passes the in-memory gates.
    for point, inp_bytes, params_bytes in prepared:
        write_new(ROOT / point["inp_path"], inp_bytes)
        write_new(ROOT / point["parameters_path"], params_bytes)
        (ROOT / point["working_dir"]).mkdir(parents=True, exist_ok=False)
    write_new(ROOT / MANIFEST_REL, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    write_new(ROOT / CHECKS_REL, json.dumps(checks, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    write_new(ROOT / REPORT_REL, report.encode("utf-8"))
    require(digest((ROOT / BASE_REL).read_bytes()) == BASE_SHA, "SOURCE_CHANGED_DURING_GENERATION")
    for point in point_rows:
        require(digest((ROOT / point["inp_path"]).read_bytes()) == point["sha256"],
                "OUTPUT_HASH_VERIFICATION_FAILED")
        require(not any((ROOT / point["working_dir"]).iterdir()), "WORK_DIR_NOT_EMPTY")
    print(json.dumps({"task_id": TASK_ID, "manifest": str(ROOT / MANIFEST_REL),
                      "points": len(point_rows), "input_hashes": [p["sha256"] for p in point_rows],
                      "nonmaterial_sha256": nonmaterial_sha, "static_checks": "PASS"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
