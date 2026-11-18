"""Verify the one frozen refined D01 reference and original target before comparing new results."""
from pathlib import Path
import json,csv,sys,hashlib,math
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_053/artifacts/private';sys.path.insert(0,str(R))
from inverse.fd_loss import Curve,Target,ScientificEvidence,evaluate,interpolate
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
cc=read(R/'run/run_051/artifacts/comparison_contract.json');binding=cc['loss_binding'];old=read(R/'run/run_027/artifacts/comparison_contract.json')
for k in ['target','config','implementation']:assert sha(R/binding[k+'_path'])==binding[k+'_sha256']
assert sha(R/cc['baseline_fd_path'])==cc['baseline_fd_sha256']
source=read(R/cc['baseline_result_path']);assert source['job_name']=='SPIO_R043_V_D01_M00125' and source['queue_id']=='q_dd23233452c544469eaebaff3fec2d8b'
assert source['odb_sha256']==cc['baseline_odb_sha256'] and source['max_saved_peeq']<.9 and source['fd_window_coverage']['covers_fixed_window']
data=rows(R/binding['target_path'])[:241];u=tuple(float(x['displacement_m']) for x in data);force=tuple(float(x['force_n']) for x in data)
assert u==tuple(old['grid_m']) and u[0]==0 and u[-1]==.0012
target=Target(Curve(u,force,'m','N'),(1.,)*241,1428.9,binding['version'])
fd=rows(R/cc['baseline_fd_path']);curve=Curve(tuple(float(x['displacement_m']) for x in fd),tuple(float(x['force_n']) for x in fd),'m','N')
value=evaluate(target,curve,fe_status='COMPLETED_WITH_WARNINGS',evidence=ScientificEvidence(provenance_verified=True,units_and_sign_verified=True,numerical_quality_accepted=True),mode='PROVISIONAL')
aligned=interpolate(curve,u);manual=math.fsum(((a-b)/1428.9)**2 for a,b in zip(aligned,force))/241
assert abs(value['loss']-cc['baseline_SPT_loss'])<1e-15 and abs(manual-value['loss'])<1e-15 and abs(value['loss']-.000502000275)<1e-12
report={'status':'PASS_FROZEN_REFERENCE_IDENTITY_AND_LOSS','baseline_job':source['job_name'],'queue_id':source['queue_id'],'FD_path':cc['baseline_fd_path'],'FD_sha256':sha(R/cc['baseline_fd_path']),'ODB_sha256':source['odb_sha256'],'actual_points':len(fd),'grid_points':241,'loss':value['loss'],'manual_recompute_loss':manual,'RMSE_to_experiment_N':1428.9*math.sqrt(value['loss']),'mode':'exploratory/provisional frozen target; not formal independent tensile validation','no_alternative_baseline_selected':True,'loss_result':value}
with (P/'D01_reference_check.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2,allow_nan=False)
print(json.dumps({'D01_loss':value['loss'],'FD_points':len(fd),'grid_points':241,'reference_identity':'PASS'}))
