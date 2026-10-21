"""Abaqus Python only: scan stored PEEQ integration-point values, no solver."""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import sys
import traceback


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--odb', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source, output = Path(args.odb).resolve(), Path(args.output).resolve()
    if output.exists():
        raise FileExistsError('Refusing to overwrite extraction output')
    result = dict(started_at=datetime.now().astimezone().isoformat(),
                  source=str(source), executable=sys.executable, python=sys.version,
                  read_only=True, field='PEEQ', status='RUNNING', errors=[])
    odb = None
    try:
        if any(p.suffix.lower() == '.lck' and p.stem.lower() == source.stem.lower()
               for p in source.parent.iterdir()):
            raise RuntimeError('ODB lock present; no read attempted')
        from odbAccess import openOdb, isUpgradeRequiredForOdb
        if isUpgradeRequiredForOdb(upgradeRequiredOdbPath=str(source)):
            raise RuntimeError('ODB requires upgrade; not allowed')
        odb = openOdb(path=str(source), readOnly=True)
        if not odb.isReadOnly:
            raise RuntimeError('ODB did not open read-only')
        result['job_version'] = str(odb.jobData.version)
        result['frames'] = []
        result['instances'] = {}
        result['missing_frames'] = []
        total = 0
        maximum, minimum, peak = None, None, None
        for step_name, step in odb.steps.items():
            for frame_index, frame in enumerate(step.frames):
                if 'PEEQ' not in frame.fieldOutputs:
                    result['missing_frames'].append([step_name, frame_index])
                    continue
                field = frame.fieldOutputs['PEEQ']
                values = []
                frame_peak = None
                positions = set()
                for value in field.values:
                    position = str(value.position)
                    positions.add(position)
                    if position != 'INTEGRATION_POINT':
                        raise RuntimeError('PEEQ requires stored integration point values, got '+position)
                    try:
                        p = float(value.data)
                    except Exception:
                        p = float(value.dataDouble)
                    if not math.isfinite(p) or p < 0:
                        raise ValueError('Nonfinite or negative PEEQ: '+repr(p))
                    location = dict(step=step_name, frame_index=frame_index,
                                    frame_value=float(frame.frameValue),
                                    increment=int(frame.incrementNumber),
                                    instance=value.instance.name,
                                    element=int(value.elementLabel),
                                    integration_point=int(value.integrationPoint))
                    values.append(p)
                    stats = result['instances'].setdefault(value.instance.name,
                                                          dict(count=0, minimum=p, maximum=p))
                    stats['count'] += 1
                    stats['minimum'] = min(stats['minimum'], p)
                    stats['maximum'] = max(stats['maximum'], p)
                    if frame_peak is None or p > frame_peak['PEEQ']:
                        frame_peak = dict(location, PEEQ=p)
                    if maximum is None or p > maximum:
                        maximum, peak = p, location
                    minimum = p if minimum is None else min(minimum, p)
                if not values:
                    raise RuntimeError('Empty PEEQ field')
                total += len(values)
                ordered = sorted(values)
                quantiles = {}
                for q in [0, .5, .9, .95, .99, 1]:
                    index = q*(len(ordered)-1)
                    low, high = int(math.floor(index)), int(math.ceil(index))
                    quantiles[str(q)] = ordered[low]+(ordered[high]-ordered[low])*(index-low)
                result['frames'].append(dict(step=step_name, frame_index=frame_index,
                                             frame_value=float(frame.frameValue),
                                             count=len(values), positions=sorted(positions),
                                             minimum=min(values), maximum=max(values),
                                             quantiles=quantiles, peak=frame_peak))
        if not total:
            raise RuntimeError('No stored PEEQ data; cannot infer coverage from PE or LE components')
        result.update(status='PASS' if not result['missing_frames'] else 'WARNING',
                      minimum=minimum, maximum=maximum, peak=peak, value_count=total,
                      scope='All available saved frames; not unsaved increments or future parameter cases')
    except Exception:
        result['status'] = 'BLOCKED'
        result['errors'].append(traceback.format_exc())
    finally:
        if odb is not None:
            odb.close()
        result['finished_at'] = datetime.now().astimezone().isoformat()
        with output.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k:result.get(k) for k in ['status','value_count','minimum','maximum','peak','errors']}))
    return 0 if result['status'] in ['PASS','WARNING'] else 1


if __name__ == '__main__':
    sys.exit(main())
