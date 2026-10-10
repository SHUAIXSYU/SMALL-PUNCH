"""Read-only dependency import probe; run with the explicitly selected interpreter.

Prints JSON to stdout. Does not install packages, initialize CUDA, or run training.
Each import runs in a fresh process to distinguish availability from metadata.
"""
import datetime
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys


PACKAGES = {
    "NumPy": ("numpy", "numpy"),
    "SciPy": ("scipy", "scipy"),
    "Pandas": ("pandas", "pandas"),
    "Matplotlib": ("matplotlib", "matplotlib"),
    "PyTorch": ("torch", "torch"),
    "Gymnasium": ("gymnasium", "gymnasium"),
    "Stable-Baselines3": ("stable-baselines3", "stable_baselines3"),
    "scikit-learn": ("scikit-learn", "sklearn"),
}


def main():
    root = Path(__file__).resolve().parents[3]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg",
               MPLCONFIGDIR=str(root / "run/run_001/artifacts/private/matplotlib"))
    result = {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "executable": sys.executable, "python": sys.version,
              "method": "distribution metadata plus isolated import, 45 s timeout/package",
              "packages": {}}
    for label, (distribution, module) in PACKAGES.items():
        item = {}
        try:
            item["distribution_version"] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            item["distribution_version"] = None
        try:
            p = subprocess.run([sys.executable, "-B", "-c",
                                "import " + module + "; print(" + module + ".__version__)"],
                               cwd=root, env=env, capture_output=True, text=True, timeout=45)
            item.update(import_ok=p.returncode == 0, returncode=p.returncode,
                        imported_version=p.stdout.strip(), diagnostic=p.stderr.strip())
        except subprocess.TimeoutExpired:
            item.update(import_ok=False, diagnostic="TIMEOUT after 45 seconds")
        result["packages"][label] = item
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
