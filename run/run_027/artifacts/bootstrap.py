"""Start run_027 and formally dispatch one CAE input-preparation task."""
import hashlib,json,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_027';A=R/'artifacts';P=A/'private'
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from agenthub_sp_invopt.hub import Hub
assert not (R/'run.json').exists()
P.mkdir(parents=True,exist_ok=True);(R/'checkpoints').mkdir(exist_ok=True)
def now():return datetime.now().astimezone().isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(*args):return subprocess.check_output(args,cwd=ROOT,text=True).strip()
source=ROOT/'run/run_023/artifacts/candidates/SPIO_R023_V01_CTR/SPIO_R023_V01_CTR.inp'
assert sha(source)=='14006d69c15e6fd4be021b889964e5add51e724d52fd03ff817b0f80b747c2ff'
old=b'0.001, 1., 1e-12, 0.005';assert source.read_bytes().count(old)==1
job='SPIO_R027_CTR_M0025';target=A/'candidates'/job/(job+'.inp');work=A/'solver'/job
assert not target.exists() and not work.exists()
git={'branch':cmd('git','branch','--show-current'),'head':cmd('git','rev-parse','HEAD'),'remote':cmd('git','remote','-v'),'working_tree':cmd('git','status','--short')}
meta={'schema_version':'1.0','run_id':'run_027','stage':'single-center input preparation','objective':'Prepare one max-increment-refined center candidate and freeze adjacent comparison without enqueue or solver','status':'RUNNING','start_time':now(),'end_time':None,'python_interpreter':sys.executable,'python_version':sys.version.split()[0],'git':git,'inputs':[{'path':str(source.relative_to(ROOT)).replace('\\','/'),'sha256':sha(source)}],'outputs':[],'validation':[],'errors':[]}
(R/'run.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(R/'summary.md').write_text('# run_027 — 单一中心点进一步增量细化准备\n\nRUNNING；无入队或求解。\n',encoding='utf8')
(R/'checkpoints/start.json').write_text(json.dumps({'at':now(),'git':git},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600)
identity=h.register('MAIN','codex-main-run027-preparation')
payload={'run':'run_027','purpose':'exactly one candidate, offline preparation only','job_name':job,'source_inp_absolute':str(source),'source_sha256':sha(source),'candidate_inp_absolute':str(target),'working_dir_absolute':str(work),'parameters':{'sigma_y_mpa':200.0,'n':0.1,'E_pa':210000000000.0,'nu':0.3,'max_plastic_strain':0.9},'change':{'keyword':'*Static','old_line':'0.001, 1., 1e-12, 0.005','new_line':'0.001, 1., 1e-12, 0.0025','max_increment_old':0.005,'max_increment_new':0.0025},'must_preserve':['all other INP bytes','material table','geometry','mesh','BC','contact','loading','outputs','historical inputs'], 'forbidden':['Solver','Datacheck','enqueue','V02','hidden tensile data','DE/BO/RL','commit/push'],'expected_output':'candidate INP, parameter JSON, byte-diff evidence, SHA-256, private CAE report and Hub result'}
task=h.create_task(identity['agent_id'],'CAE','prepare_single_increment_refinement',payload,'run027-cae-one-center-max0025-v1',depends=('dcdbafc0-8c90-40fb-94b4-eb277e357eb7',))
h.approve(task['task_id'],identity['agent_id'],'generate_inp');h.approve(task['task_id'],identity['agent_id'],'verify_inp')
h.message(task['task_id'],identity['agent_id'],'CAE',payload,'run027-cae-handoff-v1')
(P/'main_identity.json').write_text(json.dumps({'identity':identity,'cae_task_id':task['task_id']},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(A/'cae_task.json').write_text(json.dumps({'task_id':task['task_id'],'assigned_role':'CAE','approved_actions':['generate_inp','verify_inp'],'job_name':job,'source_sha256':sha(source),'candidate_inp':str(target),'working_dir':str(work),'enqueue_approved':False,'solver_approved':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'run':'run_027','task_id':task['task_id'],'job':job,'source_sha256':sha(source)}))
