"""Finalize the offline Run and its task through the existing Hub public API."""
import csv, hashlib, json, math, os, subprocess, sys
from datetime import datetime
from pathlib import Path
import numpy as np

R=Path(r'E:\Projects\SMALL-PUNCH'); RUN=R/'run/run_049'; P=RUN/'artifacts/private'
sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def now(): return datetime.now().astimezone().isoformat()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p): return p.relative_to(R).as_posix()
def save(p,v):
    with p.open('x',encoding='utf-8') as f: json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
def atomic(p,v):
    tmp=p.with_suffix(p.suffix+'.new'); save(tmp,v); read(tmp); os.replace(tmp,p)
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def git(*args): return subprocess.check_output(['git',*args],cwd=R,text=True).strip()

assert sys.executable.lower()==r'd:\xianlab\envs\torch-gpu\python.exe'
session=read(P/'hub_session.json'); h=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
assert h.task(session['task_id'])['execution_state']=='CLAIMED'
h.heartbeat(session['lease'])
before=read(P/'protected_before.json'); after={p:sha(R/p) for p in before}; assert before==after
save(P/'protected_final.json',after)
prov=read(P/'curve_provenance.json'); dataset=rows(P/'evaluated_24_points.csv'); assert len(dataset)==len(prov)==24
binding=read(R/'run/run_030/artifacts/loss_contract_binding.json')
for k in ['target','implementation','config']: assert sha(R/binding[k+'_path'])==binding[k+'_sha256']
target=rows(R/binding['target_path'])[:241]; u=np.array([float(r['displacement_m']) for r in target]); force=np.array([float(r['force_n']) for r in target])
byid={r['candidate_id']:r for r in dataset}; recomputed=[]
for p in prov:
    for prefix in ['fd','result']: assert sha(R/p[prefix+'_path'])==p[prefix+'_sha256']
    curve=rows(R/p['fd_path']); ux=np.array([float(r['displacement_m']) for r in curve]); fy=np.array([float(r['force_n']) for r in curve])
    assert np.isfinite(ux).all() and np.isfinite(fy).all() and np.all(np.diff(ux)>0)
    assert ux[0]<=u[0] and ux[-1]>=u[-1]
    loss=math.fsum(((float(a)-float(b))/1428.9)**2 for a,b in zip(np.interp(u,ux,fy),force))/241
    assert abs(loss-float(byid[p['candidate_id']]['loss']))<1e-12
    recomputed.append({'id':p['candidate_id'],'recomputed_loss':loss,'absolute_difference':abs(loss-float(byid[p['candidate_id']]['loss']))})
save(P/'loss_reverification.json',{'count':24,'all_passed':True,'scope':'historical actual F-D, unchanged loss and source hashes','results':recomputed})
checks=read(P/'analysis_checks.json'); save(P/'revisions/analysis_checks_before_final_review.json',checks)
checks['checks'].pop('24_actual_curve_losses_recomputed',None)
checks['checks']['24_actual_curve_records_and_provenance']=len(dataset)==len(prov)==24
assert all(checks['checks'].values());checks['passed']=len(checks['checks']); atomic(P/'analysis_checks.json',checks)
assert not list(RUN.rglob('*.inp')) and not list(RUN.rglob('*.odb'))
for p in P.rglob('*'):
    if p.is_file(): assert subprocess.run(['git','check-ignore','--quiet','--',rel(p)],cwd=R).returncode==0
save(P/'final_verification.json',{'at':now(),'checks_passed':checks['passed'],'recomputed_actual_losses':24,'private_git_ignore':'PASS','protected_freeze_and_reports_unchanged':True,'generated_INP':0,'new_FE':0,'enqueue':0,'material_parameter_fits':0,'formal_main_validation':'NOT_EVALUABLE_UNCHANGED','note':'offline design completion is not experimental or FE physical validation'})
with (RUN/'summary.md').open('x',encoding='utf-8') as f:
    f.write('''# run_049 — 验证后方法局限与后续研究设计

**WARNING / OFFLINE_SCIENTIFIC_ASSESSMENT_COMPLETE。**

按用户研究决定结束本轮独立验证审计，保留 run_046 冻结预测、run_047/run_048 历史及正式 NOT_EVALUABLE 结论；暂停原两参数 Hollomon 的 BO/DE/RL。

实际完成：重算24个同契约历史FE曲线的Loss并核对来源hash；保留6个null；区分离散参数补偿证据与未计算连续谷地；完成条件性误差分区和材料应变覆盖诊断；提出候选模型族、有限夹具边界对照及条件式参数识别设计。未重复原始Excel/OPJU审计，未扩建AgentHub。

完整科学结论、数据和图件位于Git忽略私有区：[研究报告](artifacts/private/scientific_assessment.md)、[分阶段研究方案](artifacts/private/future_study_design.json)、[证据分类矩阵](artifacts/private/mechanism_evidence_matrix.json)。来源方条件性拉伸比较不得称为正式独立验证。已解盲数据对后续模型选择/开发的作用必须披露，不得再次充当未使用验证集。

8项离线数据/数学/协议检查通过，另24条实际Loss及来源hash复算通过；冻结包与指定历史报告前后hash未变。无新INP、求解、Datacheck、入队、材料参数拟合、优化或Git提交。

未来最小新增FE建议为两项有实测夹具依据的固定材料边界对照；资料与输入尚不齐备，执行授权为0。额外参数设计和新模型预算均须后续科研准入及独立授权，不能自动执行。完成本Run后停止。
''')
index=R/'run/README.md'; text=index.read_text(encoding='utf-8-sig'); assert '## run_049' not in text
with index.open('a',encoding='utf-8') as f:f.write('\n\n## run_049 — 验证后科研评估与研究设计\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_049 | 历史FE补偿证据、材料形式与夹具不确定性分阶段研究设计 | WARNING / OFFLINE_SCIENTIFIC_ASSESSMENT_COMPLETE | [summary](run_049/summary.md) |\n\n正式验证维持NOT_EVALUABLE；私有证据不公开，无新增求解、拟合、入队或优化。完成后停止。\n')
status=R/'status/PROJECT_STATUS.md'; old=status.read_text(encoding='utf-8-sig'); save(P/'revisions/status_before_run049.json',{'text':old,'sha256':sha(status)})
header='# SMALL-PUNCH 项目状态\n';assert old.startswith(header)
new=header+'\n## 当前状态 — run_049（2026-10-26，Asia/Shanghai）\n\n**WARNING / OFFLINE_SCIENTIFIC_ASSESSMENT_COMPLETE。** 已完成历史FE补偿证据、模型形式及边界条件不确定性的离线分析与分阶段设计。正式独立验证维持NOT_EVALUABLE；原预测及run047/048历史不改。数据、解盲后科学结论和计划见[run_049私有报告](../run/run_049/artifacts/private/scientific_assessment.md)。暂停BO/DE/RL；无新FE、拟合、INP、入队或Git提交。未来方案须补齐实测输入和另行授权，当前执行预算0，完成后停止。\n\n'+old[len(header):]
tmp=status.with_suffix('.md.run049.tmp');tmp.write_text(new,encoding='utf-8');os.replace(tmp,status)
save(P/'git_end.json',{'at':now(),'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short'),'preexisting_changes_preserved':'see checkpoints/start.json'})
manifest=[]
for p in sorted(RUN.rglob('*')):
    if p.is_file() and p.name!='run.json' and p.name!='manifest.json': manifest.append({'path':rel(p),'sha256':sha(p),'visibility':'PRIVATE_GIT_IGNORED' if P in p.parents else 'PUBLIC_RUN_METADATA_OR_CODE','role':'offline evidence/design, not executed FE plan'})
save(RUN/'artifacts/manifest.json',{'version':'run049-final-artifact-index-v1','at':now(),'files':manifest,'exclusions':'run.json, this manifest and later Hub receipt/completion checkpoint avoid cyclic hashes'})
handoff={'run_id':'run_049','report_path':rel(P/'scientific_assessment.md'),'report_sha256':sha(P/'scientific_assessment.md'),'version':'run049-offline-assessment-v1','execution_scope':'completed offline assessment only','science_state':'WARNING','formal_independent_validation':'NOT_EVALUABLE_UNCHANGED','reliable_scope':'24 historical common-contract losses and identities rechecked; two point refinement evidence only','hypotheses':'parameter tradeoff suggested, continuous valley uncomputed; material form/range and clamp uncertainty not uniquely attributed','future_FE_authorized':0,'next_plan':'zero-FE evidence first; two measured-clamp fixed-material scenarios proposed, not prepared or authorized; four parameter secants only conditionally later','privacy':'private report; released tensile evidence is development-informed information for new models; historical exposure retained','notification':'persistent message only, no claim another session has read or awakened'}
save(P/'main_handoff.json',handoff)
registered=[]
for p in [P/'scientific_assessment.md',P/'analysis.json',P/'future_study_design.json',P/'mechanism_evidence_matrix.json',P/'evaluated_24_points.csv',P/'numerically_unscoreable_observations.json',P/'source_confirmed_error_decomposition.csv',P/'candidate_model_families.json',P/'analysis_checks.json',P/'loss_reverification.json',P/'parameter_coverage_with_nulls.png',P/'hardening_range_demand.png',P/'main_handoff.json',RUN/'artifacts/manifest.json']:
    artifact=h.artifact(session['task_id'],session['identity']['agent_id'],p,{'run':'run_049','method':'offline existing FE reanalysis and research design','classification':'private evidence' if P in p.parents else 'index only','no_new_FE':True,'historical_formal_validation_unchanged':True},version='run049-v1')
    registered.append({'artifact_id':artifact['artifact_id'],'path':artifact['path'],'sha256':artifact['sha256']})
message=h.message(session['task_id'],session['identity']['agent_id'],'MAIN',handoff,'run049-final-main-handoff-v1')
h.finish(session['lease'],handoff,evidence_state='RECORDED',science_state='WARNING')
task=h.task(session['task_id']);assert task['execution_state']=='COMPLETED' and task['evidence_state']=='RECORDED' and task['science_state']=='WARNING'
save(P/'hub_completion.json',{'task_id':session['task_id'],'message_id':message['message_id'],'task_state':{k:task[k] for k in ['execution_state','evidence_state','science_state']},'registered':registered,'no_automatic_session_wakeup_claimed':True})
run=read(RUN/'run.json');save(RUN/'checkpoints/run_before_final.json',run)
run.update(status='WARNING',end_time=now(),inputs=[{'path':rel(P/'curve_provenance.json'),'role':'private historical curve input provenance','sha256':sha(P/'curve_provenance.json')},{'path':rel(P/'protected_before.json'),'role':'protected original evidence identities','sha256':sha(P/'protected_before.json')}],outputs=[{'path':rel(RUN/'summary.md'),'role':'public scope summary'},{'path':rel(P/'scientific_assessment.md'),'role':'private scientific assessment','sha256':sha(P/'scientific_assessment.md')},{'path':rel(RUN/'artifacts/manifest.json'),'role':'artifact paths and hashes','sha256':sha(RUN/'artifacts/manifest.json')},{'path':rel(P/'hub_completion.json'),'role':'Hub formal completion receipt','sha256':sha(P/'hub_completion.json')}],validation=[{'check':'offline analysis invariants','status':'PASS','evidence':rel(P/'analysis_checks.json'),'scope':'8 offline checks, not physical qualification'},{'check':'historical loss and hashes','status':'PASS','evidence':rel(P/'loss_reverification.json'),'scope':'24 actual common-contract curves'},{'check':'preserved original evidence','status':'PASS','evidence':rel(P/'protected_final.json'),'scope':'four explicitly guarded freeze/protocol/historical reports'},{'check':'scientific qualification','status':'WARNING','evidence':rel(P/'scientific_assessment.md'),'scope':'formal independent validation remains NOT_EVALUABLE; mechanism attribution unresolved'}],errors=[])
atomic(RUN/'run.json',run)
save(RUN/'checkpoints/completed.json',{'at':now(),'task_id':session['task_id'],'run_json_sha256':sha(RUN/'run.json'),'report_sha256':sha(P/'scientific_assessment.md'),'hub_receipt_sha256':sha(P/'hub_completion.json'),'new_FE':0,'new_inputs':0,'material_fits':0,'stopped_after_run049':True})
print(json.dumps({'run':run['run_id'],'status':run['status'],'task_id':session['task_id'],'checks_passed':8,'losses_recomputed':24,'report_sha256':sha(P/'scientific_assessment.md'),'hub_state':task['execution_state'],'new_FE':0},ensure_ascii=False))
