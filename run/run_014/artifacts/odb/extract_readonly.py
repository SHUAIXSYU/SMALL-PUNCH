"""Abaqus 2024 Python: read one verified ODB without saving/upgrading it."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import traceback


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def plain(value):
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def attrs(obj, names):
    result = {}
    for name in names:
        try:
            result[name] = plain(getattr(obj, name))
        except Exception as exc:
            result[name] = {"unavailable": str(exc)}
    return result


def series(output):
    return [[float(t), float(v)] for t, v in output.data]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--odb", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    source = Path(args.odb).resolve()
    target = Path(args.output).resolve()
    if target.exists():
        raise RuntimeError("Refusing to overwrite extraction: " + str(target))
    if source.with_suffix(".lck").exists():
        raise RuntimeError("ODB lock exists")
    before = digest(source)
    if before != args.expected_sha256:
        raise RuntimeError("ODB source hash mismatch before open")
    from odbAccess import openOdb, isUpgradeRequiredForOdb
    if isUpgradeRequiredForOdb(upgradeRequiredOdbPath=str(source)):
        raise RuntimeError("ODB upgrade required; refusing to modify source")
    odb = None
    result = {"started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "interpreter": sys.executable, "python_version": sys.version,
              "source": str(source), "source_sha256_before": before,
              "read_only_requested": True, "status": "RUNNING"}
    try:
        odb = openOdb(path=str(source), readOnly=True)
        result["odb"] = attrs(odb, ["name", "isReadOnly", "analysisTitle", "description"])
        if result["odb"]["isReadOnly"] is not True:
            raise RuntimeError("ODB did not report read-only mode")
        result["job_data"] = attrs(odb.jobData, ["name", "version", "analysisCode", "creationTime", "modificationTime", "precision"])
        if hasattr(odb, "diagnosticData"):
            result["diagnostic_data"] = attrs(odb.diagnosticData, ["jobStatus", "numberOfAnalysisErrors", "numberOfAnalysisWarnings", "numberOfSteps"])
        result["steps"] = {}
        for step_name, step in odb.steps.items():
            item = {"attributes": attrs(step, ["name", "procedure", "timePeriod", "totalTime", "nlgeom"]),
                    "frame_count": len(step.frames), "history_regions": {}, "frame_diagnostics": []}
            for region_name, region in step.historyRegions.items():
                selected = {}
                for key, output in region.historyOutputs.items():
                    if (region_name == "Node ASM_SPT.1" and key in ("U2", "RF2")) or key.startswith("ALL") or key == "ETOTAL":
                        selected[key] = {"description": output.description, "data": series(output)}
                if selected:
                    item["history_regions"][region_name] = {"description": region.description, "outputs": selected}
            for frame in step.frames:
                record = {"time": float(frame.frameValue), "increment": frame.incrementNumber,
                          "description": frame.description, "peeq_count": None, "peeq_max": None,
                          "rp_field": {}}
                field = frame.fieldOutputs["PEEQ"] if "PEEQ" in frame.fieldOutputs else None
                if field is not None:
                    values = [float(v.data) for v in field.values]
                    record["peeq_count"] = len(values)
                    record["peeq_max"] = max(values) if values else None
                for key in ("U", "RF"):
                    field = frame.fieldOutputs[key] if key in frame.fieldOutputs else None
                    if field is not None:
                        for value in field.values:
                            if value.instance is not None and value.instance.name == "ASM_SPT" and value.nodeLabel == 1:
                                record["rp_field"][key] = [float(v) for v in value.data]
                item["frame_diagnostics"].append(record)
            result["steps"][step_name] = item
        result["status"] = "PASS"
    except Exception:
        result["status"] = "FAILED"
        result["error"] = traceback.format_exc()
    finally:
        if odb is not None:
            odb.close()
        result["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        result["source_sha256_after"] = digest(source)
        if result["source_sha256_after"] != before:
            result["status"] = "FAILED"
            result["error"] = (result.get("error", "") + "\nODB source hash changed during read")
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "steps": list(result.get("steps", {})),
                      "job_data": result.get("job_data"), "diagnostic_data": result.get("diagnostic_data"),
                      "error": result.get("error")}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
