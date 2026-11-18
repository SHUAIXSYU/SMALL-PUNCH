"""Complete run050 with protected hashes and existing Hub methods only."""
from pathlib import Path
from datetime import datetime
import json,hashlib,subprocess,sys,os
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_050';P=RUN/'artifacts/private';sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def rel(p):return p.relative_to(R).as_posix()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def atomic(p,v):
 t=p.with_suffix(p.suffix+'.tmp');save(t,v);read(t);os.replace(t,p)
session=read(P/'hub_session.json');h=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);h.heartbeat(session['lease'])
assert h.task(session['odb_task_id'])['execution_state']=='COMPLETED'
protected=read(P/'protected_before.json');assert all(sha(R/p)==v for p,v in protected.items());save(P/'protected_final.json',protected)
payload=read(RUN/'artifacts/odb_task_payload.json');source_checks=[]
for q in payload['points']:
 assert sha(R/q['inp_path'])==q['inp_sha256'] and sha(R/q['odb_path'])==q['odb_sha256']
 source_checks.append({'candidate_id':q['point_id'],'inp_sha256':q['inp_sha256'],'odb_sha256':q['odb_sha256'],'unchanged':True})
assert not list(RUN.rglob('*.inp')) and not list(RUN.rglob('*.odb'))
private_files=[p for p in P.rglob('*') if p.is_file()]
assert all(subprocess.run(['git','check-ignore','--quiet','--',rel(p)],cwd=R).returncode==0 for p in private_files)
save(P/'final_integrity_checks.json',{'at':now(),'protected_files_unchanged':protected,'large_source_hashes':source_checks,'private_files_git_ignored':len(private_files),'new_INP':0,'new_ODB':0,'solver_or_datacheck':0,'enqueue':0,'parameter_refits':0,'formal_independent_validation':'NOT_EVALUABLE_UNCHANGED'})
save(P/'auxiliary_inspection_notes.json',{'resolved':True,'scientific_impact':'none; actual analysis/check scripts passed','notes':['A shell inspection first referenced a guessed true-curve CSV name; corrected to actual frozen_manifest-listed D01_true_total_curve.csv before analysis','Two auxiliary report inspections referenced absent energy_stage_partition/main_handoff names; actual files were enumerated and source result/task APIs used','An auxiliary print attempted list slicing on the artifacts dictionary; corrected to inspect its actual mapping; no scientific file modification or computation failure','ODB probe/extraction adapter exceptions are retained in odb/probe_attempt1_error.txt, probe_attempt2_error.txt and extract_attempt1_error.txt; subsequent actual extractions/checks completed']})
with (RUN/'summary.md').open('x',encoding='utf-8') as f:f.write('''# run_050 — 高塑性应变与模型误差定向研究

**WARNING / EXISTING_ODB_SPATIAL_ENERGY_REVIEW_COMPLETE。**

真实“SP-InvOpt ODB”会话通过AgentHub领取并完成两项既有精化ODB的只读空间/能量提取，MAIN独立核对CAX4积分点位置与轴对称参考权重、24项阈值体积分数、直接全局能量及8项应变区间功分解。实际输出包含四个接受保存帧的空间场、参考/当前体积分数、径向/厚度分区、接触信息与离散塑性功估计。

完整科学结论及私有数据见[MAIN报告](artifacts/private/scientific_report.md)、[ODB结构化回传](artifacts/private/odb/spatial_energy_result.json)、[MAIN复核](artifacts/private/main_review_checks.json)、[四阶段图](artifacts/private/peeq_four_stage_comparison.png)及[下一步建议](artifacts/private/next_step_decision.json)。近似耗散份额不等于Punch RF2贡献，PEEQ不等于单轴真总应变；正式独立验证维持NOT_EVALUABLE。

未来优先补高应变材料依据，再考虑单独授权最多两项高应变延拓敏感性对照。有限夹具边界对照仍缺实测参数，不能生成具体输入；不追加识别点或BO/DE。建议不构成执行授权。

原INP/ODB、run046冻结包及指定run048/049历史报告和生成器hash保持不变；产物位于Git忽略私有区。无新INP、Solver、Datacheck、入队、参数拟合、BO/DE/RL或Git提交。已解盲信息的开发数据角色及历史暴露事实保留。完成后停止。
''')
idx=R/'run/README.md';text=idx.read_text(encoding='utf-8-sig');assert '## run_050' not in text
with idx.open('a',encoding='utf-8') as f:f.write('\n\n## run_050 — 高塑性应变空间、能量与外推风险\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_050 | 真实ODB空间/能量只读提取、MAIN独立核验与最小机制验证设计 | WARNING / EXISTING_ODB_SPATIAL_ENERGY_REVIEW_COMPLETE | [summary](run_050/summary.md) |\n\n近似能量不作RF2分解；正式验证与历史结论保留，无新输入、拟合或求解，完成后停止。\n')
sp=R/'status/PROJECT_STATUS.md';old=sp.read_text(encoding='utf-8-sig');save(P/'status_before_run050.json',{'sha256':sha(sp),'text':old})
header='# SMALL-PUNCH 项目状态\n';assert old.startswith(header)
new=header+'\n## 当前状态 — run_050（2026-10-26，Asia/Shanghai）\n\n**WARNING / EXISTING_ODB_SPATIAL_ENERGY_REVIEW_COMPLETE。** 真实ODB会话经AgentHub完成精化D01/I08四阶段积分点空间/接触和离散塑性功提取，MAIN独立核对体积、能量与冻结材料范围。科学结论和数据见[run_050私有报告](../run/run_050/artifacts/private/scientific_report.md)。近似耗散不等于RF2贡献，正式独立验证仍NOT_EVALUABLE；历史冻结与暴露记录保留。未来方案需新输入证据和明确授权，当前无新FE、INP、入队、拟合或优化，完成后停止。\n\n'+old[len(header):]
t=sp.with_suffix('.md.run050.tmp');t.write_text(new,encoding='utf-8');os.replace(t,sp)
save(P/'git_final.json',{'at':now(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'working_tree':subprocess.check_output(['git','status','--short'],cwd=R,text=True),'preexisting_changes':'preserved; see checkpoints/start.json'})
manifest=[]
for p in sorted(RUN.rglob('*')):
 if p.is_file() and p.name!='run.json' and p!=RUN/'artifacts/manifest.json':manifest.append({'path':rel(p),'sha256':sha(p),'visibility':'PRIVATE_GIT_IGNORED' if P in p.parents else 'PUBLIC_CODE_OR_SCOPE_METADATA'})
save(RUN/'artifacts/manifest.json',{'version':'run050-evidence-index-v1','at':now(),'files':manifest,'excluded':'self/run.json and later Hub receipt/completion checkpoint avoid cyclic hashes'})
handoff={'run':'run_050','version':'run050-main-scientific-review-v1','report_path':rel(P/'scientific_report.md'),'report_sha256':sha(P/'scientific_report.md'),'odb_task_id':session['odb_task_id'],'MAIN_status':'WARNING','formal_independent_validation':'NOT_EVALUABLE_UNCHANGED','facts':'four saved stages, actual IP-weighted fields/volumes and direct ALLPD checked','approximation':'S.Mises*dPEEQ reference-volume estimate and strain-bin split, not direct local dissipation or RF2 contribution','recommendation':'high-p continuation evidence/sensitivity before more identification or BO/DE; fixture comparison remains conditional on measured inputs','future_authorized_jobs':0,'new_FE':0,'new_INP':0,'parameter_fit':0,'persistent_message_is_not_automatic_session_wakeup':True}
save(P/'main_handoff.json',handoff)
h.message(session['odb_task_id'],session['identity']['agent_id'],'ODB',{'review_run':'run_050','report_path':handoff['report_path'],'report_sha256':handoff['report_sha256'],'MAIN_independent_checks':'reference integration,24 threshold fractions,8 direct energy/stage-bin sums checked','science_state':'WARNING; load attribution and physical validity unresolved'},'run050-main-review-ack-v1')
registered=[]
for p in [P/'scientific_report.md',P/'main_spatial_independent_check.json',P/'main_global_energy_check.json',P/'main_hardening_work_consistency.json',P/'main_energy_comparison.json',P/'main_review_checks.json',P/'frozen_material_scope.json',P/'next_step_decision.json',P/'boundary_research_design.json',P/'peeq_four_stage_comparison.png',P/'main_handoff.json',RUN/'artifacts/manifest.json']:
 a=h.artifact(session['main_task_id'],session['identity']['agent_id'],p,{'run':'run_050','scope':'offline existing-result review and future design only','source_ODB_task':session['odb_task_id'],'not_direct_force_attribution':True,'private_evidence':P in p.parents},version='run050-v1');registered.append({'artifact_id':a['artifact_id'],'path':a['path'],'sha256':a['sha256']})
message=h.message(session['main_task_id'],session['identity']['agent_id'],'MAIN',handoff,'run050-final-main-result-v1');h.finish(session['lease'],handoff,evidence_state='RECORDED',science_state='WARNING')
mt=h.task(session['main_task_id']);assert mt['execution_state']=='COMPLETED'
save(P/'hub_completion.json',{'at':now(),'main_task_id':session['main_task_id'],'odb_task_id':session['odb_task_id'],'message_id':message['message_id'],'registered':registered,'execution_state':mt['execution_state'],'evidence_state':mt['evidence_state'],'science_state':mt['science_state'],'real_ODB_session_completed':True})
run=read(RUN/'run.json');save(RUN/'checkpoints/before_final.json',run)
run.update(status='WARNING',end_time=now(),outputs=[{'path':rel(RUN/'summary.md'),'role':'public scope summary'},{'path':rel(P/'scientific_report.md'),'role':'private scientific report','sha256':sha(P/'scientific_report.md')},{'path':rel(RUN/'artifacts/manifest.json'),'role':'evidence manifest','sha256':sha(RUN/'artifacts/manifest.json')},{'path':rel(P/'hub_completion.json'),'role':'formal Hub completion receipt','sha256':sha(P/'hub_completion.json')}],validation=[{'check':'real ODB session and MAIN independent checks','status':'PASS','evidence':rel(P/'main_review_checks.json'),'scope':'41 ODB manifest files;8 saved stages;24 threshold volume checks; direct energy identities'},{'check':'source and frozen evidence unchanged','status':'PASS','evidence':rel(P/'final_integrity_checks.json'),'scope':'two original INP/ODB hashes and explicitly protected freeze/history/generator'},{'check':'scientific inference boundary','status':'WARNING','evidence':rel(P/'scientific_report.md'),'scope':'no exact local dissipation or RF2 attribution; high-p causal dominance and fixture equivalence not established'}],errors=[{'code':'READONLY_EXTRACTION_ADAPTER_EXCEPTIONS_RESOLVED','severity':'INFO','message':'Initial inspection/adapter exceptions retained; subsequent extraction and actual scientific checks passed','evidence':rel(P/'auxiliary_inspection_notes.json'),'resolution':'corrected repository/field sequence access and actual artifact names; originals unchanged'}])
atomic(RUN/'run.json',run)
save(RUN/'checkpoints/completed.json',{'at':now(),'run_json_sha256':sha(RUN/'run.json'),'report_sha256':sha(P/'scientific_report.md'),'hub_receipt_sha256':sha(P/'hub_completion.json'),'new_FE':0,'new_inputs':0,'stopped_after_run050':True})
print(json.dumps({'run':'run_050','status':run['status'],'main_task_id':session['main_task_id'],'odb_task_id':session['odb_task_id'],'report_sha256':sha(P/'scientific_report.md'),'registered_MAIN_artifacts':len(registered),'new_jobs':0}))
