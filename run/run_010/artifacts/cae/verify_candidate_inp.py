"""Read-only verification of the run_008 candidate INP for the CAE handoff."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from inverse.hollomon import generate_hollomon_table

TASK_ID = "a4b4805f-4989-4168-a54a-3bbf435b52a6"
JOB = "SPIO_R008_Q200_N010_Candidate"
SOURCE_REL = "CAE/Models/Sanity/Job-1.inp"
INP_REL = f"run/run_008/artifacts/candidate_inp/{JOB}/{JOB}.inp"
EXPECTED_SOURCE_SHA = "b2aac48af9529db28873c19f047f479c63ed247884f9bdc5fd7bccd5763305cc"
EXPECTED_INP_SHA = "fa2de5d73a28536c1c07cd22072d2a24c1ae988c569127d728931c583457f05a"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plastic_bounds(lines: list[str]) -> tuple[int, int]:
    materials = [i for i, line in enumerate(lines)
                 if re.fullmatch(r"\*Material\s*,\s*name\s*=\s*Q200N01\s*", line.strip(), re.I)]
    if len(materials) != 1:
        raise ValueError(f"Expected one Q200N01 material; found {len(materials)}")
    starts = [i for i in range(materials[0] + 1, len(lines))
              if lines[i].strip().lower() == "*plastic"]
    if len(starts) != 1:
        raise ValueError(f"Expected one *Plastic keyword after Q200N01; found {len(starts)}")
    start = starts[0]
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].lstrip().startswith("*")), len(lines))
    return start, end


def main() -> None:
    source = ROOT / SOURCE_REL
    inp = ROOT / INP_REL
    report_path = Path(__file__).with_name("verification.json")
    if report_path.exists():
        raise SystemExit("Refuse to overwrite existing verification report")
    if not source.is_file() or not inp.is_file():
        raise SystemExit("Source or candidate INP missing")
    if inp.parent.name != JOB or inp.name != JOB + ".inp":
        raise SystemExit("Candidate job path/name mismatch")

    source_sha, inp_sha = sha256(source), sha256(inp)
    source_lines = source.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    inp_lines = inp.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    ss, se = plastic_bounds(source_lines)
    cs, ce = plastic_bounds(inp_lines)
    table = generate_hollomon_table(200.0, 0.1, max_plastic_strain=0.9)
    fragment = table.abaqus_plastic_text()
    if not fragment.endswith("\n"):
        fragment += "\n"
    reconstructed = "".join(source_lines[:ss]) + fragment + "".join(source_lines[se:])
    candidate_text = "".join(inp_lines)
    data_lines = [line.strip() for line in inp_lines[cs + 1:ce]
                  if line.strip() and not line.lstrip().startswith("**")]
    rows = [tuple(float(cell.strip()) for cell in line.split(",")) for line in data_lines]
    elastic_matches = re.findall(r"(?im)^\*Elastic\s*\n\s*([^\n]+)", candidate_text)
    elastic = tuple(float(cell.strip()) for cell in elastic_matches[0].split(",")) if len(elastic_matches) == 1 else None
    checks = {
        "source_sha256_matches_run008": source_sha == EXPECTED_SOURCE_SHA,
        "candidate_sha256_matches_task_and_run008": inp_sha == EXPECTED_INP_SHA,
        "path_and_job_basename_match": inp.parent.name == JOB and inp.name == JOB + ".inp",
        "elastic_matches_E_210GPa_nu_0p3": elastic == (210e9, 0.3),
        "plastic_rows_match_generator_exactly": tuple(rows) == table.rows,
        "plastic_first_row_is_yield_at_zero": rows[0] == (200e6, 0.0),
        "plastic_row_count_35": len(rows) == 35,
        "plastic_endpoint_p_0p9": rows[-1][1] == 0.9,
        "plastic_stress_and_strain_strictly_increase": all(
            b[0] > a[0] and b[1] > a[1] for a, b in zip(rows, rows[1:])),
        "entire_inp_reconstructs_from_source_plus_generator_block": candidate_text == reconstructed,
        "nonplastic_prefix_and_suffix_unchanged":
            candidate_text.startswith("".join(source_lines[:ss]))
            and candidate_text.endswith("".join(source_lines[se:])),
    }
    report = {
        "task_id": TASK_ID,
        "observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "status": "PASS_STATIC_INP_VERIFICATION" if all(checks.values()) else "FAILED_STATIC_INP_VERIFICATION",
        "scope": "Read-only static file/material/structural comparison; no Abaqus datacheck or solver",
        "source_relative_path": SOURCE_REL,
        "source_sha256": source_sha,
        "candidate_relative_path": INP_REL,
        "candidate_sha256": inp_sha,
        "generator_relative_path": "inverse/hollomon.py",
        "generator_sha256": sha256(ROOT / "inverse/hollomon.py"),
        "generator_model_id": table.model_id,
        "parameters": {"E_Pa": 210e9, "nu": 0.3, "sigma_y_MPa": 200.0,
                       "n": 0.1, "max_plastic_strain": 0.9},
        "elastic": elastic,
        "plastic_row_count": len(rows),
        "plastic_first_row": rows[0],
        "plastic_last_row": rows[-1],
        "checks": checks,
        "prior_abaqus_parser_evidence": "run/run_008/artifacts/candidate_inp_parse.json",
        "limitations": ["Historical Job-1 INP may differ from currently edited CAE database",
                        "No fresh Abaqus parser, datacheck, solver, or physical validation",
                        "INP header retains historical Job-1/Model-1 comments; unique job identity is the output path/basename"],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": checks,
                      "report": str(report_path)}, ensure_ascii=False))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
