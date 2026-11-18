"""Initialize run_026 and its formal MAIN-only offline diagnostic task."""
import json,sys,subprocess
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_026';P=R/'artifacts/private'
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from agenthub_sp_invopt.hub import Hub
assert R.name=='run_026' and not (R/'run.json').exists()
assert not (ROOT/'run/run_027').exists()
P.mkdir(parents=True,exist_ok=True);(R/'checkpoints').mkdir(exist_ok=True)
def cmd(*args):return subprocess.check_output(args,cwd=ROOT,text=True).strip()
now=datetime.now().astimezone().isoformat()
git={'branch':cmd('git','branch','--show-current'),'head':cmd('git','rev-parse','HEAD'),'remote':cmd('git','remote','-v'),'working_tree':cmd('git','status','--short')}
meta={'schema_version':'1.0','run_id':'run_026','stage':'V01 difference targeted offline diagnosis','objective':'Explain V01 vs original center difference using existing curves, contact fields and solver diagnostics; assess impact without changing run023 gates','status':'RUNNING','start_time':now,'end_time':None,'python_interpreter':sys.executable,'python_version':sys.version.split()[0],'git':git,'inputs':['run/run_014/artifacts/odb/punch_force_displacement.csv','run/run_025/artifacts/private/odb/force_displacement.csv','run/run_023/artifacts/private/comparison_contract.json'],'outputs':[],'validation':[],'errors':[]}
(R/'run.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(R/'summary.md').write_text('# run_026 — V01差异定向诊断\n\nRUNNING；只读既有结果，冻结BLOCKED结论保持。\n',encoding='utf8')
(R/'checkpoints/start.json').write_text(json.dumps({'at':now,'git':git},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600)
idn=h.register('MAIN','codex-main-run026-targeted-diagnostic')
task=h.create_task(idn['agent_id'],'MAIN','offline_numerical_diagnostic',{'run':'run_026','sources':['run_014','run_025'],'scope':'V01 numerical differences, no solver, no queue, no hidden tensile','frozen_qualification':'BLOCKED_V01_NUMERICAL_QUALIFICATION'},'run026-main-offline-v01-diagnostic-v1')
lease=h.claim(task['task_id'],idn,'main-offline-analysis-v1')
(P/'main_session.json').write_text(json.dumps({'identity':idn,'task_id':task['task_id'],'lease':lease},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'run':'run_026','task_id':task['task_id'],'interpreter':sys.executable,'git_head':git['head']}))
