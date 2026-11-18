"""Explicit run048 evidence hashes; excludes self to avoid circular digest."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'run/run_048/artifacts/private/evidence_manifest.json'
inputs=[
 'run/run_046/artifacts/private/SP_InvOpt_run046_frozen_candidates.zip',
 'run/run_046/artifacts/private/freeze/frozen_manifest.json',
 'run/run_046/artifacts/private/freeze/independent_validation_protocol.json',
 'run/run_046/artifacts/private/freeze/independent_validation_protocol.md',
 'references_private/508 RAW TENSILE TEST.opju',
 'run/run_047/artifacts/private/origin_extract.json',
 'run/run_047/artifacts/private/independent_validation_report.md',
 'run/run_017/artifacts/private/experimental_metadata.json',
 'references_private/SA508 SPT-GB.xlsx',
 'references_private/SA508 SPT-GB.opju',
]
outputs=[
 'run/run_048/checkpoints/initial.json',
 'run/run_048/artifacts/verify_inputs.py',
 'run/run_048/artifacts/compute_reassessment.py',
 'run/run_048/artifacts/test_reassessment.py',
 'run/run_048/artifacts/private/collaborator_confirmation.json',
 'run/run_048/artifacts/private/input_integrity.json',
 'run/run_048/artifacts/private/qualification_gate_audit.md',
 'run/run_048/artifacts/private/reassessment_metrics.json',
 'run/run_048/artifacts/private/restricted_pointwise_comparison.csv',
 'run/run_048/artifacts/private/fixed_band_metrics.csv',
 'run/run_048/artifacts/private/reassessment_comparison.png',
 'run/run_048/artifacts/private/independent_reassessment_report.md',
 'run/run_048/artifacts/private/main_handoff.md',
 'run/run_048/artifacts/private/test_results.txt',
 'run/run_048/run.json',
 'run/run_048/summary.md',
]
def entry(path):
    p=ROOT/path;b=p.read_bytes()
    return {'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
record={'generated_at':datetime.now().astimezone().isoformat(),
        'scope':'explicit input and output identities; private, no directory-wide scan',
        'inputs':[entry(p) for p in inputs],
        'outputs':[entry(p) for p in outputs]}
OUT.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(len(record['inputs']),len(record['outputs']),OUT)
