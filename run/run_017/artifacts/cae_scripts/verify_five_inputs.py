"""Independent static re-read of five run_017 INPs; no Abaqus execution."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from inverse.hollomon import stress_at_plastic_strain

MANIFEST = ROOT / "run/run_017/artifacts/cae_candidate_manifest.json"
OUT = ROOT / "run/run_017/artifacts/private/cae/verification.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def disassemble(raw: bytes) -> tuple[bytes, list[tuple[float, float]], bytes]:
    lines = raw.splitlines(keepends=True)
    run_starts = [i for i, s in enumerate(lines) if s.startswith(b"** RUN_017 POINT ")]
    candidate_starts = [i for i, s in enumerate(lines) if s.startswith(b"** CANDIDATE ONLY:")]
    if len(candidate_starts) != 1 or len(run_starts) > 1:
        raise ValueError("Candidate material comment boundary not unique")
    starts = run_starts if run_starts else candidate_starts
    if run_starts and not run_starts[0] < candidate_starts[0]:
        raise ValueError("Candidate comment order changed")
    plastic = [i for i, s in enumerate(lines) if s.strip().lower() == b"*plastic"]
    if len(plastic) != 1 or plastic[0] <= starts[0]:
        raise ValueError("Plastic keyword boundary not unique")
    end = next((i for i in range(plastic[0] + 1, len(lines)) if lines[i].lstrip().startswith(b"*")), None)
    if end is None or lines[end].strip() != b"**":
        raise ValueError("Plastic block end changed")
    rows = []
    for line in lines[plastic[0] + 1:end]:
        a, b = (float(v) for v in line.split(b","))
        rows.append((a, b))
    return b"".join(lines[:starts[0]]), rows, b"".join(lines[end:])


def main() -> None:
    if OUT.exists():
        raise SystemExit("Refuse to overwrite verification")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base = (ROOT / manifest["source"]["baseline_inp"]).read_bytes()
    if sha(base) != manifest["source"]["baseline_sha256"]:
        raise ValueError("Baseline changed")
    baseline_prefix, _, baseline_suffix = disassemble(base)
    nonmaterial = sha(baseline_prefix + baseline_suffix)
    if nonmaterial != manifest["nonmaterial_sha256"]:
        raise ValueError("Baseline nonmaterial hash mismatch")
    if len(manifest["points"]) != 5:
        raise ValueError("Unexpected candidate count")
    jobs, hashes, paths, checks = set(), set(), set(), []
    for item in manifest["points"]:
        inp_path = ROOT / item["inp_path"]
        raw = inp_path.read_bytes()
        if sha(raw) != item["sha256"] or sha(raw) in hashes:
            raise ValueError("INP hash mismatch or duplicate")
        hashes.add(sha(raw))
        prefix, rows, suffix = disassemble(raw)
        if prefix != baseline_prefix or suffix != baseline_suffix or sha(prefix + suffix) != nonmaterial:
            raise ValueError("Nonmaterial bytes changed")
        if b"*Include" in raw or b"*INCLUDE" in raw:
            raise ValueError("External include detected")
        point = json.loads((ROOT / item["parameters_path"]).read_text(encoding="utf-8"))
        if point["inp_sha256"] != item["sha256"] or point["job_name"] != item["job_name"]:
            raise ValueError("Parameters sidecar mismatch")
        if point["sigma_y_mpa"] != item["parameters"]["sigma_y_mpa"] or point["n"] != item["parameters"]["n"]:
            raise ValueError("Frozen parameters mismatch")
        if len(rows) != item["material_rows"] or rows[0][1] != 0 or rows[-1][1] != 0.9:
            raise ValueError("Material table endpoint or count mismatch")
        if not math.isclose(rows[0][0], point["sigma_y_mpa"] * 1e6, rel_tol=1e-15):
            raise ValueError("First stress mismatch")
        if not all(a[0] < b[0] and a[1] < b[1] for a, b in zip(rows, rows[1:])):
            raise ValueError("Material table not strictly monotonic")
        max_error = 0.0
        for (s0, p0), (s1, p1) in zip(rows, rows[1:]):
            for fraction in (0.25, 0.5, 0.75):
                p = p0 + (p1 - p0) * fraction
                chord = s0 + (s1 - s0) * fraction
                analytic = stress_at_plastic_strain(p, point["sigma_y_mpa"], point["n"])
                max_error = max(max_error, abs(chord - analytic) / analytic)
        if max_error > 0.001000000000001:
            raise ValueError("Interpolation error exceeds tolerance")
        work_dir = ROOT / item["working_dir"]
        if not work_dir.is_dir() or any(work_dir.iterdir()):
            raise ValueError("Work directory missing or not empty")
        if item["job_name"] in jobs or item["inp_path"] in paths:
            raise ValueError("Duplicate job name or path")
        jobs.add(item["job_name"]); paths.add(item["inp_path"])
        checks.append({"point_id": item["point_id"], "job_name": item["job_name"],
                       "inp_sha256": sha(raw), "nonmaterial_sha256": nonmaterial,
                       "rows": len(rows), "max_sampled_relative_error": max_error,
                       "work_dir_empty": True})
    result = {"schema": "sp_invopt.cae.verification.v1",
              "observed_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
              "task_id": manifest["task_id"], "status": "PASS_STATIC_SCOPE_ONLY",
              "source_sha256": sha(base), "design_sha256": manifest["source"]["design_sha256"],
              "candidate_count": len(checks), "points": checks,
              "nonmaterial_bytes_identical": True,
              "no_external_dependencies": True,
              "work_directories_empty": True,
              "abaqus_or_preflight_executed": False,
              "future_peeq_adequacy": "UNKNOWN"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "candidate_count": len(checks),
                      "max_sampled_relative_error": max(p["max_sampled_relative_error"] for p in checks),
                      "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
