"""Lightweight run_001 audit; standard library only, no solver or source mutation.

Run from any cwd with the approved external Python. JSON is printed to stdout.
Private hashes can only be checked on the local checkout containing the sources.
"""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "AGENTS.md", "README.md", ".gitignore", "docs/Research_Overview.md",
    "docs/Research_Architecture.md", "docs/Constitutive_Model.md",
    "docs/Agent_File_Communication_Protocol.md", "docs/Data_Management.md",
    "docs/CAE_Model_Audit.md", "status/PROJECT_STATUS.md", "run/README.md",
    "run/run_001/run.json", "run/run_001/summary.md",
    "run/run_001/artifacts/manifest.json", "run/run_001/checkpoints/initial_state.json",
]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    check("required_files", all((ROOT / p).is_file() for p in REQUIRED), REQUIRED)
    dirs = ["CAE/Models", "CAE/Scripts", "experiments", "inverse", "tests",
            "run/run_001/artifacts", "run/run_001/checkpoints", "references_private"]
    check("required_directories", all((ROOT / p).is_dir() for p in dirs), dirs)
    run = json.loads((ROOT / "run/run_001/run.json").read_text(encoding="utf-8"))
    keys = ["schema_version", "run_id", "stage", "objective", "status", "start_time",
            "end_time", "python_interpreter", "git_head", "inputs", "outputs", "validation", "errors"]
    check("run_fields", all(k in run for k in keys) and run["run_id"] == "run_001"
          and run["status"] in {"PASS", "WARNING", "BLOCKED", "FAILED"}, keys)
    times = [datetime.datetime.fromisoformat(run[k]) for k in ("start_time", "end_time")]
    check("time_order", all(t.tzinfo is not None for t in times) and times[0] <= times[1],
          "Both actual observed timestamps include timezone")
    check("git_head_unchanged", git("rev-parse", "HEAD").stdout.strip() == run["git_head"], run["git_head"])
    check("index_unchanged", git("diff", "--cached", "--exit-code").returncode == 0,
          "No staged changes")
    initial = json.loads((ROOT / "run/run_001/checkpoints/initial_state.json").read_text(encoding="utf-8"))
    prefix = (ROOT / "README.md").read_bytes()[:initial["initial_files"]["README.md"]["bytes"]]
    check("original_readme_preserved", hashlib.sha256(prefix).hexdigest() ==
          initial["initial_files"]["README.md"]["sha256"], "Original byte prefix retained; additions only")
    private = ROOT / "run/run_001/artifacts/private"
    before = json.loads((private / "migration_before.json").read_text(encoding="utf-8-sig"))
    expected = {f["relative_path"]: f for f in before["files"]}
    source = ROOT / "references_private"
    actual = {p.relative_to(source).as_posix(): p for p in source.rglob("*") if p.is_file()}
    check("source_filenames", set(expected) == set(actual), {"expected": len(expected), "actual": len(actual)})
    check("source_sha256", set(expected) == set(actual) and all(
        actual[p].stat().st_size == item["bytes"] and sha(actual[p]) == item["sha256"]
        for p, item in expected.items()), "All original files checked, no raw hashes disclosed")
    actual_dirs = sorted(p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_dir())
    check("source_directories", actual_dirs == sorted(before["directories"]), "Original relative directory structure")
    check("legacy_directory_absent", not (ROOT / "Materials").exists(), "Materials/ renamed")
    probes = ["references_private/test.dat", "materials/test.dat", "Materials/test.dat",
              "run/run_001/artifacts/private/test.json", "CAE/Jobs/run_002/job/test.inp",
              "CAE/Models/test.odb", "CAE/Models/test.ODB", "CAE/Models/test.sim", "CAE/Models/test.lck"]
    check("ignore_rules", all(git("check-ignore", "-q", "--", p).returncode == 0 for p in probes), probes)
    check("source_not_tracked", not any(p.lower().startswith(("materials/", "references_private/"))
          for p in git("ls-files").stdout.splitlines()), "No private sources in Git index")
    manifest = json.loads((ROOT / "run/run_001/artifacts/manifest.json").read_text(encoding="utf-8"))
    paths = [o["path"] for o in run["outputs"]] + [o["path"] for o in manifest["artifacts"]]
    path_ok = all(not Path(p).is_absolute() and (ROOT / p).resolve().is_relative_to(ROOT)
                  and (ROOT / p).exists() for p in paths)
    check("artifact_paths", path_ok, "All declared artifacts exist and resolve inside repository")
    md_errors = []
    markdown_paths = [ROOT / "README.md", ROOT / "AGENTS.md"]
    markdown_paths += list((ROOT / "docs").glob("*.md")) + list((ROOT / "status").glob("*.md"))
    markdown_paths += [ROOT / "run/README.md", ROOT / "run/run_001/summary.md"]
    for p in markdown_paths:
        content = p.read_text(encoding="utf-8")
        if "\ufffd" in content or content.count("```") % 2:
            md_errors.append(p.relative_to(ROOT).as_posix() + ": encoding/fence")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            if re.match(r"https?://", target) or target.startswith("#"):
                continue
            if not (p.parent / target.split("#")[0]).exists():
                md_errors.append(p.relative_to(ROOT).as_posix() + ": broken link " + target)
    check("markdown_local_checks", not md_errors, md_errors or "UTF-8, fences and local links only; no remote-link test")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    check("readme_privacy", not re.search(r"[A-Za-z]:[\\/]", readme)
          and not any(name in readme for name in expected), "No absolute local paths or original filenames")
    check("whitespace_diff", git("diff", "--check").returncode == 0, "Tracked diff whitespace")
    result = {"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL", "checks": checks,
              "scope": "Local filesystem, original-file hashes, Git, run metadata, ignore rules and Markdown only"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
