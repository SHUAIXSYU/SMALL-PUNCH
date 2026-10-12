"""Abaqus 2024 Python only. Read ODB with readOnly=True; never upgrade or save it.

Usage: abq2024.bat python extract_odb_readonly.py --odb <existing> --output <new.json>
Outputs metadata, complete histories, mesh topology, and bounded field diagnostics.
RP identity is deliberately verified downstream against the matching input deck.
"""
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys
import traceback


def simple(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def json_scalar(value):
    # Abaqus may expose numpy scalar values even without importing numpy here.
    if hasattr(value, 'item'):
        return value.item()
    raise TypeError('Unsupported JSON value: ' + type(value).__name__)


def attributes(obj, names):
    data = {}
    for name in names:
        try:
            data[name] = simple(getattr(obj, name))
        except Exception as exc:
            data[name] = {'unavailable': str(exc)}
    return data


def labels(items):
    result = []
    for value in items:
        if hasattr(value, 'label'):
            result.append({'instance': getattr(value, 'instanceName', None), 'label': value.label})
        else:
            result.extend(labels(value))
    return result


def sets(repository, attribute):
    result = {}
    for name, region in repository.items():
        try:
            result[name] = labels(getattr(region, attribute))
        except Exception as exc:
            result[name] = {'error': str(exc)}
    return result


def values(field):
    for value in field.values:
        try:
            data = value.data
        except Exception:
            data = value.dataDouble
        yield value, data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--odb', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source, target = Path(args.odb).resolve(), Path(args.output).resolve()
    if target.exists():
        raise RuntimeError('Refusing to overwrite extraction output: ' + str(target))
    result = {'started_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'python': sys.version,
              'executable': sys.executable, 'source': str(source), 'read_only': True, 'errors': []}
    odb = None
    try:
        locks = [str(p) for p in source.parent.iterdir() if p.stem.lower() == source.stem.lower() and p.suffix.lower() == '.lck']
        if locks:
            raise RuntimeError('Source lock present; no open attempted: ' + repr(locks))
        from odbAccess import openOdb, isUpgradeRequiredForOdb
        if isUpgradeRequiredForOdb(upgradeRequiredOdbPath=str(source)):
            raise RuntimeError('ODB upgrade required; no upgrade performed')
        odb = openOdb(path=str(source), readOnly=True)
        result['opened'] = True
        result['odb'] = attributes(odb, ['name', 'description', 'isReadOnly', 'analysisTitle'])
        result['job_data'] = attributes(odb.jobData, ['name', 'version', 'analysisCode', 'creationTime', 'modificationTime', 'machineName', 'precision', 'productAddOns'])
        if hasattr(odb, 'diagnosticData'):
            result['diagnostic_data'] = attributes(odb.diagnosticData, ['jobStatus', 'numberOfAnalysisErrors', 'numberOfAnalysisWarnings', 'numberOfSteps'])
        root = odb.rootAssembly
        result['assembly_node_sets'] = sets(root.nodeSets, 'nodes')
        result['assembly_element_sets'] = sets(root.elementSets, 'elements')
        result['instances'] = {}
        for name, inst in root.instances.items():
            result['instances'][name] = dict(
                attributes=attributes(inst, ['name','type','embeddedSpace']),
                nodes=[{'label': n.label, 'coordinates': list(n.coordinates)} for n in inst.nodes],
                elements=[{'label': e.label, 'type': e.type, 'connectivity': list(e.connectivity)} for e in inst.elements],
                node_sets=sets(inst.nodeSets, 'nodes'), element_sets=sets(inst.elementSets, 'elements'),
                surfaces=list(inst.surfaces.keys()))
        rp_by_instance = {}
        axis_by_instance = {}
        for name, inst_data in result['instances'].items():
            rp_by_instance[name] = {n['label'] for set_name, members in inst_data['node_sets'].items()
                if ('PUNCH_RP' in set_name.upper() or 'REFPT' in set_name.upper()) and isinstance(members, list) for n in members}
            axis_by_instance[name] = {n['label'] for n in inst_data['nodes'] if abs(n['coordinates'][0]) < 1e-12} if len(inst_data['nodes']) > 1 else set()
        result['steps'] = {}
        for step_name, step in odb.steps.items():
            item = dict(attributes=attributes(step, ['name','description','domain','procedure','timePeriod','totalTime','nlgeom']),
                        frame_count=len(step.frames), history_regions={}, frames=[])
            for region_name, region in step.historyRegions.items():
                item['history_regions'][region_name] = dict(description=region.description, outputs={
                    key: dict(description=h.description, type=str(h.type), data=[list(p) for p in h.data])
                    for key,h in region.historyOutputs.items()})
            for frame in step.frames:
                f = dict(frame_value=frame.frameValue, increment=frame.incrementNumber,
                         description=frame.description, fields={}, rp_fields={}, resultant_rf={}, axis_u1_max=None)
                for key, field in frame.fieldOutputs.items():
                    components = list(field.componentLabels)
                    low, high, count = None, None, 0
                    valid_low, valid_high, excluded = None, None, 0
                    for value, data in values(field):
                        vals = list(data) if hasattr(data, '__len__') else [data]
                        if low is None:
                            low, high = list(vals), list(vals)
                        else:
                            low = [min(a,b) for a,b in zip(low, vals)]
                            high = [max(a,b) for a,b in zip(high, vals)]
                        count += 1
                        if key.startswith('COPEN'):
                            # Preserve raw extrema; exclude huge unavailable/sentinel values only
                            # from a separately named diagnostic, never from original data.
                            if any(not math.isfinite(float(v)) or abs(float(v)) > 1e30 for v in vals):
                                excluded += 1
                            else:
                                valid_low = vals if valid_low is None else [min(a,b) for a,b in zip(valid_low,vals)]
                                valid_high = vals if valid_high is None else [max(a,b) for a,b in zip(valid_high,vals)]
                        instance_name = value.instance.name if value.instance else None
                        if key in ['U','RF','UR','RM','UR3','RM3']:
                            inst_data = result['instances'].get(instance_name, {})
                            rp_labels = rp_by_instance.get(instance_name, set())
                            if value.nodeLabel in rp_labels:
                                f['rp_fields'].setdefault(instance_name + '.' + str(value.nodeLabel), {})[key] = dict(components=components, data=vals)
                            if key == 'RF':
                                total = f['resultant_rf'].setdefault(instance_name, [0.0] * len(vals))
                                f['resultant_rf'][instance_name] = [a+b for a,b in zip(total, vals)]
                            if key == 'U' and inst_data.get('nodes'):
                                axis_labels = axis_by_instance.get(instance_name, set())
                                if value.nodeLabel in axis_labels and len(inst_data['nodes']) > 1:
                                    f['axis_u1_max'] = max(f['axis_u1_max'] or 0, abs(vals[0]))
                    f['fields'][key] = dict(description=field.description, type=str(field.type), components=components,
                                            value_count=count, minimum=low, maximum=high)
                    if key.startswith('COPEN'):
                        f['fields'][key].update(valid_minimum=valid_low, valid_maximum=valid_high,
                                               excluded_huge_or_nonfinite_count=excluded,
                                               filtering='Separate diagnostic excludes abs(value)>1e30 or nonfinite; raw min/max preserved.')
                item['frames'].append(f)
            result['steps'][step_name] = item
        result['status'] = 'PASS'
    except Exception:
        result['status'] = 'BLOCKED'
        result['errors'].append(traceback.format_exc())
    finally:
        if odb is not None:
            odb.close()
        result['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=json_scalar) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'opened': result.get('opened', False),
                      'steps': list(result.get('steps', {})), 'errors': result['errors']}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
