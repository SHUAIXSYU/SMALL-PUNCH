"""Start read-only run_029 after run_028 queue-only record."""
import hashlib,json,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_029';A=R/'artifacts'
sys.dont_write_bytecode=True
def now():return datetime.now().astimezone().isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
assert not (R/'run.json').exists()
(A/'private').mkdir(parents=True,exist_ok=True);(R/'checkpoints').mkdir(exist_ok=True)
g={k:cmd(*v) for k,v in {'branch':['branch','--show-current'],'head':['rev-parse','HEAD'],'remote':['remote','-v'],'working_tree':['status','--short']}.items()}
x={'schema_version':'1.0','run_id':'run_029','stage':'run_028 actual result audit and adjacent increment qualification','objective':'Audit one completed GUI-started job, real ODB handoff, frozen V01 primary and run014 auxiliary comparison','status':'RUNNING','start_time':now(),'end_time':None,'python_interpreter':sys.executable,'python_version':sys.version.split()[0],'git':g,'inputs':[{'path':'run/run_028/artifacts/enqueue_result.json','sha256':sha(ROOT/'run/run_028/artifacts/enqueue_result.json')},{'path':'run/run_027/artifacts/comparison_contract.json','sha256':sha(ROOT/'run/run_027/artifacts/comparison_contract.json')}],'outputs':[],'validation':[],'errors':[]}
(R/'run.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(R/'summary.md').write_text('# run_029 — 中心点进一步增量细化真实结果审核\n\nRUNNING：尚需正式执行终态、真实ODB提取及冻结门槛判定。\n',encoding='utf8')
(R/'checkpoints/start.json').write_text(json.dumps({'at':now(),'git':g,'python':sys.executable},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'run':'run_029','status':'RUNNING'}))
