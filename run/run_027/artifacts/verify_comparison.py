"""Capture prior unit tests plus real V01 self-comparison under the new frozen contract."""
import csv,hashlib,importlib.util,json,math,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];A=ROOT/'run/run_027/artifacts'
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from inverse.fd_loss import Curve,Target
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
contract=read(A/'comparison_contract.json');base=read(ROOT/contract['run023_contract_path'])
assert sha(ROOT/contract['comparison_implementation_path'])==contract['comparison_implementation_sha256']
testfile=ROOT/contract['tested_by'];assert sha(testfile)==contract['tests_sha256']
r=subprocess.run([sys.executable,'-B',str(testfile)],cwd=ROOT,text=True,capture_output=True)
assert r.returncode==0 and 'Ran 12 tests' in r.stderr and '\nOK\n' in r.stderr
spec=importlib.util.spec_from_file_location('frozen_compare',ROOT/contract['comparison_implementation_path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
target_data=rows(ROOT/contract['target_path'])[:241]
assert len(target_data)==241
grid=tuple(base['grid_m']);assert all(abs(float(r['displacement_m'])-u)<1e-17 for r,u in zip(target_data,grid))
target=Target(Curve(grid,tuple(float(r['force_n']) for r in target_data),'m','N'),tuple([1.]*241),1428.9,'run017-exploratory-fd-v1')
vrows=rows(ROOT/contract['primary']['original_fd_path']);crow=rows(ROOT/contract['auxiliary']['fd_path'])
v=Curve(tuple(float(x['displacement_m']) for x in vrows),tuple(float(x['force_n']) for x in vrows),'m','N')
c=Curve(tuple(float(x['displacement_model_length']) for x in crow),tuple(float(x['force_model_force']) for x in crow),'m','N')
selfcheck=m.compare(target,v,v,base,original_status='COMPLETED_WITH_WARNINGS',validation_status='COMPLETED_WITH_WARNINGS')
priorcheck=m.compare(target,c,v,base,original_status='COMPLETED_WITH_WARNINGS',validation_status='COMPLETED_WITH_WARNINGS')
assert selfcheck['status']=='CURVE_GATE_PASS' and selfcheck['force_rmse_n']==selfcheck['max_absolute_force_n']==selfcheck['loss_change']==0
assert math.isclose(selfcheck['original_loss'],0.048334917442418086,abs_tol=1e-13)
assert math.isclose(priorcheck['force_rmse_n'],3.9987751586240563,abs_tol=1e-11)
assert math.isclose(priorcheck['max_absolute_force_n'],19.558200999730843,abs_tol=1e-11)
result={'recorded_at':datetime.now().astimezone().isoformat(),'interpreter':sys.executable,'unit_test_file':contract['tested_by'],'unit_test_sha256':contract['tests_sha256'],'unit_test_exit_code':r.returncode,'unit_test_stderr':r.stderr,'test_count':12,'real_V01_self_comparison':selfcheck,'prior_C_vs_V01_reproduction':priorcheck,'comparison_implementation_sha256':contract['comparison_implementation_sha256'],'loss_implementation_sha256':contract['loss_implementation_sha256'],'status':'PASS_OFFLINE_TESTS_ONLY','new_candidate_solved':False}
with (A/'comparison_test_result.json').open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
print(json.dumps({'status':result['status'],'tests':result['test_count'],'V01_self_rmse_n':selfcheck['force_rmse_n'],'prior_difference_rmse_n':priorcheck['force_rmse_n']}))
