"""Re-score only the existing historical center with the exact frozen Loss."""
import sys,json,csv,hashlib,math
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from inverse.fd_loss import Curve,Target,ScientificEvidence,evaluate
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
identity=read(ROOT/'run/run_017/artifacts/loss_contract_identity.json');cfg=read(ROOT/identity['path']);ref=read(ROOT/'run/run_017/artifacts/private/reference_loss.json')
assert sha(ROOT/identity['path'])==identity['sha256'] and sha(ROOT/identity['implementation'])==identity['implementation_sha256']
assert sha(ROOT/cfg['target'])==cfg['target_sha256'] and sha(ROOT/ref['fe_source'])==ref['fe_sha256']
exp=[r for r in rows(ROOT/cfg['target']) if 0<=float(r['displacement_m'])<=.0012];fe=rows(ROOT/ref['fe_source']);assert len(exp)==241 and len(fe)==170
target=Target(Curve(tuple(float(r['displacement_m']) for r in exp),tuple(float(r['force_n']) for r in exp),'m','N'),tuple([1]*241),1428.9,cfg['version'])
curve=Curve(tuple(float(r['displacement_model_length']) for r in fe),tuple(float(r['force_model_force']) for r in fe),'m','N')
result=evaluate(target,curve,fe_status='COMPLETED_WITH_WARNINGS',evidence=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True),mode='PROVISIONAL')
assert math.isclose(result['loss'],ref['loss'],rel_tol=1e-14)
result.update(rmse_n=math.sqrt(result['loss'])*1428.9,nrmse=math.sqrt(result['loss']),source_sha256=ref['fe_sha256'],contract_sha256=identity['sha256'],source_unchanged=True)
with (ROOT/'run/run_022/artifacts/private/center_recheck.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
