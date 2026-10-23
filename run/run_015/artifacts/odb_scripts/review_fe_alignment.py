"""Review FE measurement definition and draw an explicitly unaligned diagnostic."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fe-csv", required=True)
    p.add_argument("--fe-diagnostics", required=True)
    p.add_argument("--candidate-csv", required=True)
    p.add_argument("--xlsx-audit", required=True)
    p.add_argument("--private-output", required=True)
    args = p.parse_args()
    fe_path = Path(args.fe_csv).resolve()
    candidate_path = Path(args.candidate_csv).resolve()
    out = Path(args.private_output).resolve()
    fe = rows(fe_path)
    experimental = rows(candidate_path)
    audit = json.loads(Path(args.xlsx_audit).read_text(encoding="utf-8"))
    fe_diagnostics = json.loads(Path(args.fe_diagnostics).read_text(encoding="utf-8"))
    assert len(fe) == fe_diagnostics["sample_count"]
    assert len(experimental) == audit["point_count"]
    x_fe = [float(r["displacement_model_length"]) for r in fe]
    f_fe = [float(r["force_model_force"]) for r in fe]
    x_exp = [float(r["displacement_m"]) for r in experimental]
    f_exp = [float(r["force_n"]) for r in experimental]
    result = {
        "observed_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        "fe_source": str(fe_path), "fe_sha256": sha(fe_path), "fe_points": len(fe),
        "fe_measurement": "Punch reference point ASM_SPT.1; d=-U2, F=-RF2, downward compression positive; no 2*pi factor, no baseline shift",
        "fe_unit_interpretation": "N-m-Pa explicitly declared by user for run_015; historical run_014 report had marked physical units unverified",
        "fe_displacement_end_m": x_fe[-1], "fe_force_end_n": f_fe[-1],
        "experimental_candidate_source": str(candidate_path), "experimental_candidate_sha256": sha(candidate_path),
        "experimental_points": len(experimental),
        "experimental_measurement": "XLSX columns labeled displacement (mm) and load (N); sensor/zero/compliance origin not stated",
        "experimental_displacement_end_m": x_exp[-1], "experimental_load_end_n": f_exp[-1],
        "known_alignment_facts": ["Both curves can be represented on axes labeled m and N under the current user FE unit declaration.",
                                  "Candidate XLSX displacement was converted from explicitly labeled mm by factor 0.001; load N unchanged."],
        "unresolved_alignment": ["Experimental displacement sensor location and its relation to Punch RP U2",
                                 "Experimental displacement zeroing and machine/fixture compliance correction",
                                 "Experimental load sign/calibration and punch-force relation",
                                 "Specimen geometry, punch/support/fixture and loading protocol comparability",
                                 "Experiment sample/replicate identity and whether XLSX is original measurement or derived export",
                                 "Origin OPJU versus XLSX data authority and any preprocessing provenance"],
        "status": "UNALIGNED_DIAGNOSTIC_ONLY",
        "formal_loss": None,
        "interpolation_or_crop_applied": False,
        "smoothing_zero_shift_outlier_removal_averaging_applied": False,
    }
    (out / "fe_measurement_review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x_fe, f_fe, label="FE Punch RP (user-declared N–m–Pa)")
    ax.plot(x_exp, f_exp, label="XLSX candidate (units only; unaligned)")
    ax.set_xlabel("Displacement (m; reference locations not reconciled)")
    ax.set_ylabel("Force / load (N; measurement relation unverified)")
    ax.set_title("Unaligned diagnostic only — no experimental Loss")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "unaligned_diagnostic.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"status": result["status"], "fe_points": len(fe), "xlsx_points": len(experimental), "formal_loss": None}, ensure_ascii=False))

if __name__ == "__main__":
    main()
