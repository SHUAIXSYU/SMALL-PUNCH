"""Hash explicit run047 evidence files; no private-directory traversal."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'run/run_047/artifacts/private/evidence_manifest.json'
paths=[
 'run/run_047/checkpoints/pre_unblind_prediction.json',
 'run/run_047/artifacts/verify_freeze.py',
 'run/run_047/artifacts/pre_unblind_checkpoint.py',
 'run/run_047/artifacts/probe_origin.ps1',
 'run/run_047/artifacts/conditional_coordinate_analysis.py',
 'run/run_047/artifacts/private/freeze_integrity.json',
 'run/run_047/artifacts/private/freeze_integrity_report.md',
 'run/run_047/artifacts/private/source_copy/508 RAW TENSILE TEST.opju',
 'run/run_047/artifacts/private/extract_origin.py',
 'run/run_047/artifacts/private/origin_extract.json',
 'run/run_047/artifacts/private/tensile_data_inventory.md',
 'run/run_047/artifacts/private/tensile_provenance_and_comparability.md',
 'run/run_047/artifacts/private/validation_metrics.json',
 'run/run_047/artifacts/private/tensile_validation_results.csv',
 'run/run_047/artifacts/private/constitutive_validation_comparison.png',
 'run/run_047/artifacts/private/independent_validation_report.md',
 'run/run_047/artifacts/private/main_handoff.md',
 'run/run_047/run.json',
 'run/run_047/summary.md',
]
items=[]
for rel in paths:
    p=ROOT/rel
    b=p.read_bytes()
    items.append({'path':rel,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
record={'generated_at':datetime.now().astimezone().isoformat(),
        'scope':'explicit run047 outputs only; source identities in private reports',
        'items':items}
OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(len(items),OUT)
