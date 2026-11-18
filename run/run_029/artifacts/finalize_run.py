"""Finalize a narrow adjacent-refinement PASS while retaining historical BLOCKED."""
import hashlib,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_029';A=R/'artifacts';P=A/'private'
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def write(p,x):
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
review=read(P/'main_review.json');comp=read(P/'comparison/frozen_comparison_exact.json');session=read(P/'main_session.json');audit=read(P/'execution_audit.json')
assert review['decision']=='PASS_CENTER_ADJACENT_REFINEMENT_ONLY' and all(review['numerical_gates'].values())
assert review['run025_original_qualification']=='BLOCKED_V01_NUMERICAL_QUALIFICATION_UNCHANGED'
assert review['V02_queued'] is False and review['new_solver_jobs']==0
assert comp['all_quantitative_pass'] and all(comp['checks'].values())
assert sha(ROOT/'run/run_027/artifacts/solver/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.odb')==audit['files']['odb']['sha256']
assert sha(ROOT/'run/run_027/artifacts/candidates/SPIO_R027_CTR_M0025/SPIO_R027_CTR_M0025.inp')==audit['inp_sha256']
h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600)
assert h.task(session['odb_task_id'])['execution_state']=='COMPLETED' and h.verify_chain()
meta=read(R/'run.json');assert meta['status']=='RUNNING'
meta.update(status='WARNING',stage='adjacent center refinement passed within frozen scope',end_time=now(),outputs=[{'path':rel(p),'role':role} for p,role in [(R/'summary.md','Public report'),(P/'main_report.md','Private scientific report'),(P/'main_review.json','Frozen decision'),(P/'comparison/frozen_comparison_exact.json','Frozen metrics exact PEEQ'),(P/'odb/REPORT.md','Real ODB report'),(P/'execution_audit.json','Actual execution audit')]],validation=[{'check':'execution_identity','status':'PASS','scope':'One actual Datacheck and Full Analysis, stable original files'},{'check':'real_odb_handoff','status':'PASS','scope':'Generation2 real ODB task, 35 Hub artifacts, MAIN received message'},{'check':'five_frozen_metrics','status':'PASS','scope':'All five adjacent V01 gates pass'},{'check':'contact_mechanism','status':'WARNING','scope':'CPRESS and force transition correlated; unique cause unproven'},{'check':'prior_run025','status':'BLOCKED_UNCHANGED','scope':'Historical run014-to-V01 qualification preserved'}],errors=[{'severity':'INFO','code':'ODB_LEASE_RECOVERY','message':'Expired first ODB lease formally recovered after worker stopped; no ODB re-extraction or Solver retry','evidence':'run/run_029/artifacts/odb_recovery.json'},{'severity':'INFO','code':'OFFLINE_PEEQ_ARGUMENT_PRECISION','message':'Initial CLI PEEQ last bit rounded; original offline comparison retained and exact value rebound from ODB JSON','evidence':'run/run_029/artifacts/private/comparison/frozen_comparison_exact.json'}])
write(R/'run.json',meta)
idx=ROOT/'run/README.md';txt=idx.read_text(encoding='utf8');assert '## run_029' not in txt
idx.write_text(txt.rstrip()+'\n\n## run_029 — 中心点真实结果与相邻细化资格\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_029 | 真实ODB交接、冻结五项门槛、局部接触与数值警告审核 | WARNING / PASS_CENTER_ADJACENT_REFINEMENT_ONLY | [summary](run_029/summary.md) |\n\n原run_025数值资格BLOCKED不变；V02未入队，停止等待新的研究授权。\n',encoding='utf8')
status=ROOT/'status/PROJECT_STATUS.md';txt=status.read_text(encoding='utf8');heading='# SMALL-PUNCH 项目状态\n';assert txt.startswith(heading) and '## 当前状态 — run_029' not in txt
status.write_text(heading+'\n## 当前状态 — run_029（2026-10-24，Asia/Shanghai）\n\n**WARNING / PASS_CENTER_ADJACENT_REFINEMENT_ONLY。** 用户GUI完成唯一run_027候选，真实ODB Agent只读提取及MAIN冻结五项比较通过；此判定仅限V01→最大增量0.0025的相邻中心检查。run_025对run_014→V01的BLOCKED结论保留，四扰动Jacobian、网格及实验本构未获验证；V02未入队，无新增求解授权。见[run_029报告](../run/run_029/summary.md)。完成后停止。\n\n'+txt[len(heading):],encoding='utf8')
paths=[P/'execution_audit.json',P/'main_review.json',P/'main_report.md',P/'comparison/frozen_comparison.json',P/'comparison/frozen_comparison_exact.json',P/'comparison/aligned_241.csv',P/'comparison/full_comparison.png',P/'comparison/focus_110_116.png',P/'odb/REPORT.md',A/'task_ids.json',A/'odb_recovery.json',A/'main_review.py',A/'analyze_frozen.py',A/'correct_peeq_precision.py',R/'summary.md',R/'run.json']
manifest={'at':now(),'main_task_id':session['main_task_id'],'odb_task_id':session['odb_task_id'],'real_odb_artifact_count':review['real_odb_artifact_count'],'files':[{'path':rel(p),'sha256':sha(p),'private':p.is_relative_to(P)} for p in paths]}
mp=A/'manifest.json';assert not mp.exists();write(mp,manifest)
for p in paths+[mp]:h.artifact(session['main_task_id'],session['identity']['agent_id'],p,{'run':'run_029','source':'Real ODB Agent plus MAIN independent frozen qualification','new_solver_jobs':0},version='run029-v1')
result={'status':review['decision'],'queue_id':audit['queue_id'],'main_task_id':session['main_task_id'],'odb_task_id':session['odb_task_id'],'five_metrics':review['metrics'],'accepted':443,'rejected':19,'run025_blocked_unchanged':True,'V02_queued':False,'report':rel(P/'main_report.md')}
h.message(session['main_task_id'],session['identity']['agent_id'],'MAIN',result,'run029-main-decision-v1')
h.finish(session['lease'],result,evidence_state='RECORDED',science_state='WARNING')
assert h.verify_chain()
write(R/'checkpoints/completion.json',{'at':now(),'decision':review['decision'],'main_task_id':session['main_task_id'],'odb_task_id':session['odb_task_id'],'queue_id':audit['queue_id'],'worker_artifacts_verified':review['real_odb_artifact_count'],'manifest_sha256':sha(mp),'V02_queued':False,'new_solver_jobs':0,'audit_chain_valid':True})
print(json.dumps({'decision':review['decision'],'queue_id':audit['queue_id'],'main_task_id':session['main_task_id'],'worker_artifacts':review['real_odb_artifact_count'],'hub_chain':True}))
