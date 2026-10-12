"""Read-only interpreter/package audit; run with the explicitly selected Python."""
import datetime as dt
import hashlib
import importlib.metadata as md
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "run/run_004"
EXPECTED = r"D:\XianLab\envs\conda\torch-gpu\python.exe"
TZ = dt.timezone(dt.timedelta(hours=8))


def now():
    return dt.datetime.now(TZ).isoformat()


def save(path, value):
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(pending.read_text(encoding="utf-8"))
    pending.replace(path)


def command(args):
    started = now()
    try:
        result = subprocess.run(args, cwd=ROOT, env=ENV, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=60)
        return dict(command=args, started_at=started, ended_at=now(),
                    returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
    except subprocess.TimeoutExpired as exc:
        def decode(value):
            return value.decode("utf-8", "replace") if isinstance(value, bytes) else value
        return dict(command=args, started_at=started, ended_at=now(), returncode=None,
                    error=repr(exc), stdout=decode(exc.stdout), stderr=decode(exc.stderr))


if __name__ == "__main__":
    if os.path.normcase(sys.executable) != os.path.normcase(EXPECTED):
        raise RuntimeError("Unexpected interpreter: " + sys.executable)
    ENV = os.environ.copy()
    ENV.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", MPLBACKEND="Agg")
    for key, folder in [("MPLCONFIGDIR", "mplconfig"), ("TEMP", "temp"), ("TMP", "temp")]:
        local = RUN / "artifacts/private" / folder
        local.mkdir(exist_ok=True)
        ENV[key] = str(local)
    baseline = json.loads((RUN / "checkpoints/initial_state.json").read_text(encoding="utf-8-sig"))
    record = dict(schema_version="1.0", run_id="run_004", stage="Stage 1",
                  objective="Record and verify the selected research Python without solving, optimization or training.",
                  status="RUNNING", start_time=baseline["first_clock_observed_at"], end_time=None,
                  time_notes="Start is the first observed clock after initial reads; probe timestamps are actual +08:00 observations.",
                  python_interpreter=sys.executable, git_head=baseline["head"], git_branch=baseline["branch"],
                  inputs=[], outputs=[], validation=[], errors=[])
    save(RUN / "run.json", record)
    packages = [("numpy", "numpy"), ("scipy", "scipy"), ("pandas", "pandas"),
                ("matplotlib", "matplotlib"), ("scikit-learn", "sklearn"), ("torch", "torch"),
                ("gymnasium", "gymnasium"), ("stable-baselines3", "stable_baselines3")]
    report = dict(checked_at=now(), executable=sys.executable, python=sys.version,
                  executable_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
                  packages={}, optional_bo_metadata={}, commands=[],
                  scope="Package imports, SciPy DE API import, installed metadata and pip check only; no numerical, CUDA, solver, optimization or training validation.")
    for distribution, module in packages:
        try:
            version = md.version(distribution)
        except md.PackageNotFoundError:
            version = None
        code = "import importlib,json; m=importlib.import_module(" + repr(module) + "); print(json.dumps({'version':getattr(m,'__version__',None)}))"
        outcome = command([EXPECTED, "-B", "-c", code])
        report["commands"].append(outcome)
        report["packages"][distribution] = dict(version=version, import_ok=outcome["returncode"] == 0)
        print(distribution, version, "PASS" if outcome["returncode"] == 0 else "FAILED", flush=True)
        save(RUN / "artifacts/environment.json", report)
    for distribution in ["botorch", "gpytorch", "scikit-optimize", "optuna", "bayesian-optimization"]:
        try:
            report["optional_bo_metadata"][distribution] = md.version(distribution)
        except md.PackageNotFoundError:
            report["optional_bo_metadata"][distribution] = None
    de = command([EXPECTED, "-B", "-c", "from scipy.optimize import differential_evolution; print('DE API import OK; optimizer not executed')"])
    report["commands"].append(de)
    report["scipy_de_api_import_ok"] = de["returncode"] == 0
    pip_check = command([EXPECTED, "-B", "-m", "pip", "--disable-pip-version-check", "check"])
    report["commands"].append(pip_check)
    report["pip_check_ok"] = pip_check["returncode"] == 0
    report["finished_at"] = now()
    report["status"] = "PASS" if all(p["import_ok"] for p in report["packages"].values()) and report["scipy_de_api_import_ok"] and report["pip_check_ok"] else "WARNING"
    save(RUN / "artifacts/environment.json", report)
    inventory = sorted([dict(name=d.metadata.get("Name"), version=d.version) for d in md.distributions()], key=lambda d: (d["name"] or "").lower())
    save(RUN / "artifacts/package_inventory.json", dict(observed_at=now(), packages=inventory))
    print(json.dumps({"status": report["status"], "pip_check": pip_check, "optional_bo_metadata": report["optional_bo_metadata"]}, ensure_ascii=False), flush=True)
