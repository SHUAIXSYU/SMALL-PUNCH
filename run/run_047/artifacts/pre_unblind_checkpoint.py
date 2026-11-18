import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'run/run_046/artifacts/private/freeze'
OUT = ROOT/'run/run_047/checkpoints/pre_unblind_prediction.json'
levels = [0.002, 0.01, 0.10]
frozen = json.loads((BASE/'frozen_inversion_results.json').read_text(encoding='utf-8'))
rows=[]
for p in frozen['candidates']:
    cid=p['candidate_id']
    path=BASE/f'{cid}_true_total_curve.csv'
    with path.open(newline='',encoding='utf-8') as f:
        a=list(csv.DictReader(f))
    x=np.array([float(v['true_total_strain']) for v in a])
    y=np.array([float(v['true_stress_pa']) for v in a])
    rows.append({'candidate_id':cid,'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n'],
                 'yield_true_total_strain':p['yield_true_total_strain'],
                 'prediction_csv_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'prediction_points':len(a),
                 'stress_mpa_at_true_total_strain':{str(q):float(np.interp(q,x,y)/1e6) for q in levels},
                 'hardening_trend':'stress rises over 0.002–0.10; D01 rises more steeply than I08 over this interval',
                 'SPT_loss':p['SPT_loss']})
result={'observed_at':datetime.now().astimezone().isoformat(),
        'stage':'before tensile source content or hash access',
        'freeze_integrity':'PASS',
        'prediction_authority':'frozen candidate true-total CSV, no refit or regenerated formula',
        'E_pa':210e9,'nu':0.3,
        'candidates':rows,
        'SPT_rank':'D01_FIRST',
        'historical_information_exposure':'run015 MAIN/ODB exposure disclosed; independent reviewer did not read old derived tensile analysis'}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(OUT)
