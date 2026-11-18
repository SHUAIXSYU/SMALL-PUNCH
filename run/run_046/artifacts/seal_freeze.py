"""Verify and seal candidate package, then register existing AgentHub MAIN evidence."""
import csv,hashlib,json,sys,zipfile,subprocess
from pathlib import Path
from datetime import datetime
import numpy as np
ROOT=Path(r'E:\Projects\SMALL-PUNCH');R=ROOT/'run/run_046';A=R/'artifacts';P=A/'private';F=P/'freeze'
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub

def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def write_new(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def atomic(p,v):
 temp=p.with_name(p.name+'.tmp');write_new(temp,v);assert read(temp)==v;temp.replace(p)
def rows(p):
 with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))

def main():
 session=read(P/'hub_session.json');hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);hub.heartbeat(session['lease'])
 assert hub.task(session['task_id'])['execution_state']=='CLAIMED' and hub.verify_chain()
 results=read(F/'frozen_inversion_results.json');protocol=read(F/'independent_validation_protocol.json');assert read(P/'validation_tests.json')['exit_code']==0
 differences={}
 for pid in ['D01','I08']:
  params=read(F/(pid+'_parameters.json'));rr=rows(F/(pid+'_true_total_curve.csv'));table=rows(F/(pid+'_abaqus_yield_stress_plastic_strain.csv'))
  assert len(rr)==10803 and len(table)==(51 if pid=='D01' else 40)
  e=np.array([float(v['true_total_strain']) for v in rr]);s=np.array([float(v['true_stress_pa']) for v in rr]);p=np.array([float(v['uniaxial_plastic_strain']) for v in rr])
  assert e[0]==0 and e[-1]==.9 and np.all(np.diff(e)>0) and np.isfinite(s).all() and np.all(np.diff(s)>0)
  assert np.max(abs(e-s/210e9-p))<1e-15 and p.min()>=0 and p.max()<.9
  assert sha(ROOT/params['source_inp'])==params['source_inp_sha256']
  assert params['SPT_loss']==next(v['SPT_loss'] for v in results['candidates'] if v['candidate_id']==pid)
  differences[pid]={'sigma_y_mpa':params['sigma_y_mpa'],'n':params['n'],'SPT_loss':params['SPT_loss'],'file_rows':len(rr),'plastic_rows':len(table)}
 grid=rows(F/'validation_primary_grid.csv');assert len(grid)==981 and float(grid[0]['true_total_strain'])==.002 and float(grid[-1]['true_total_strain'])==.1
 assert protocol['unblind_authorized'] is False if 'unblind_authorized' in protocol else protocol['status']=='PREREGISTERED_NO_UNBLIND_AUTHORIZATION'
 assert sha(A/'validation_metrics.py')==protocol['implementation_sha256']==sha(F/'validation_metrics_frozen.py')
 assert sha(ROOT/'inverse/hollomon.py')==sha(F/'hollomon_frozen.py')==results['candidates'][0]['generator_sha256']
 # The unopened holdout is not hashed or enumerated. Only exact allowed input references are verified.
 for item in read(F/'input_provenance.json')['files']:assert sha(ROOT/item['path'])==item['sha256']
 method_note={'observed_at':now(),'source_url':protocol['method_source']['url'],'facts_supported':['engineering to true stress/log strain conversion, before necking only','Abaqus stress vs plastic strain and p=epsilon_true_total-sigma/E'],
  'source_role':'SIMULIA-authored primary technical documentation, 2025 online edition; installed solver remains2024 and was not invoked','not_claimed':'SA508 parameter truth, measured metadata, acceptable error tolerance','2024_url_attempt':'403 unavailable; verified 2025 primary text instead, no installed software changes'}
 write_new(F/'method_references.json',method_note)
 (F/'handoff_to_independent_reviewer.md').write_text('''# 授权后的独立复核交接\n\n这是未来交接模板，不是当前解盲授权。优先由未读保留拉伸数据的人复核；不继承含拉伸或混合报告的历史上下文。\n\n1. 获得用户明确授权和限定原始文件后，验证本包manifest/hash；任何不一致停止。\n2. 只提供本包、SPT来源方声明及授权读取的原始拉伸文件，禁止提供旧封存分析作为答案。独立登记批次/状态、量纲、定义、颈缩与原始重复试样，来源不明时先报告。\n3. 严格按independent_validation_protocol.json执行，主窗不覆盖则null，不为某候选单独改窗。R0.2_E210只作统一参考诊断，不冒称标准Rp0.2。\n4. 分别保留解析预测和实际Abaqus分段表辅助结果，不能挑选较优的视图。先独立导出与登记验证结果，再向MAIN报告，保留历史信息暴露声明。\n5. 不回调参数、E、Loss、评分和预测；不启动FE、BO、DE或RL。未知实验容差不补造材料验证PASS。\n''',encoding='utf-8')
 # Freeze package has no self-hash dependency. Every payload file is listed once.
 manifest_path=F/'frozen_manifest.json'
 files=sorted(p for p in F.iterdir() if p.is_file())
 manifest={'version':'run046-candidate-freeze-manifest-v1','frozen_at':now(),'no_holdout_content_access':True,'history_exposure_disclosed':True,
  'format':{'json':'UTF-8, finite JSON numbers, full Python double roundtrip precision','csv':'UTF-8, comma, LF newline, .17g floats; stressPa, strain dimensionless','prediction_domain':'true total0–0.9; plastic0–0.9 separately; no physical validity claim for whole range'},
  'source_producer':{'path':rel(A/'freeze_candidates.py'),'sha256':sha(A/'freeze_candidates.py'),'git_head':read(R/'checkpoints/start.json')['git']['head']},
  'files':[{'path':rel(p),'bundle_path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in files],
  'immutability':'Hash-bound snapshot and create-only outputs, not Windows ACL; later altered bytes are detected. No post-unblind replacement.',
  'unblind_authorized':False}
 write_new(manifest_path,manifest)
 bundle=P/'SP_InvOpt_run046_frozen_candidates.zip'
 with zipfile.ZipFile(bundle,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files+[manifest_path]:z.write(p,arcname=p.name)
 with zipfile.ZipFile(bundle,'r') as z:
  assert z.testzip() is None
  for v in manifest['files']:assert hashlib.sha256(z.read(v['bundle_path'])).hexdigest()==v['sha256']
 receipt={'version':'run046-freeze-receipt-v1','frozen_at':manifest['frozen_at'],'state':'FROZEN_AWAITING_EXPLICIT_UNBLIND_AUTHORIZATION','curves_frozen':True,
  'bundle':{'path':rel(bundle),'sha256':sha(bundle),'bytes':bundle.stat().st_size},'manifest':{'path':rel(manifest_path),'sha256':sha(manifest_path)},
  'results':{'path':rel(F/'frozen_inversion_results.json'),'sha256':sha(F/'frozen_inversion_results.json')},
  'validation_protocol':{'path':rel(F/'independent_validation_protocol.json'),'sha256':sha(F/'independent_validation_protocol.json')},
  'curves':[{'candidate_id':pid,'true_total_path':rel(F/(pid+'_true_total_curve.csv')),'true_total_sha256':sha(F/(pid+'_true_total_curve.csv')),
   'plastic_path':rel(F/(pid+'_abaqus_yield_stress_plastic_strain.csv')),'plastic_sha256':sha(F/(pid+'_abaqus_yield_stress_plastic_strain.csv')),
   'parameters_path':rel(F/(pid+'_parameters.json')),'parameters_sha256':sha(F/(pid+'_parameters.json'))} for pid in ['D01','I08']],
  'readiness':'Ready to request explicit authorization for preregistered comparison; formal same-state validation remains gated by experimental provenance/definition/uniformity. No physical PASS threshold invented.',
  'task_id':session['task_id'],'new_fe':0,'new_queue':0,'holdout_access':False}
 write_new(A/'freeze_receipt.json',receipt)
 summary='''# run_046 — 候选本构冻结与独立验证准备\n\n**WARNING / FROZEN_AWAITING_EXPLICIT_UNBLIND_AUTHORIZATION。** 已结束当前探索性优化阶段，冻结D01当前最佳已评估候选和I08竞争性替代候选。完整精度参数、最新探索性SPT Loss、点级数值资格PASS、两个数值契约来源、目标身份及限制均已保存。\n\n每条真总应变曲线0–0.9含10,803点，Abaqus塑性表0–0.9分别51/40点，与已求解INP材料行逐值一致；固定E210GPa、nu0.3，保留候选真总应变解释。真总应变1%时应力约278.97/364.81MPa，相差85.83MPa；两曲线不是置信区间。\n\n独立验证已预注册：真实量/工程量与总/塑性应变区分、颈缩前适用条件、批次/材料状态门控、固定主窗0.002–0.10真总应变981点、预设子区间、绝对/相对误差和两候选排序。覆盖不足则主评分null，不缩窗。初始sigma_y不等于Rp0.2；仅另给固定E210统一偏移诊断。没有实验容差依据，不杜撰物理PASS阈值。\n\n11项合成测试通过，输出和ZIP内每项SHA核验通过。见[冻结收据](artifacts/freeze_receipt.json)、[完整私有包](artifacts/private/SP_InvOpt_run046_frozen_candidates.zip)、[冻结结果](artifacts/private/freeze/frozen_inversion_results.json)、[验证协议](artifacts/private/freeze/independent_validation_protocol.md)、[预测曲线](artifacts/private/freeze/candidate_constitutive_comparison.png)。原始SPT数据仅绑定身份未修改，封存拉伸及派生结果未访问。\n\n可以申请明确解盲授权，并优先安排未接触保留数据的复核人员。此处就绪不等于已经解盲、已确认同材或已经完成物理验证；历史run015信息暴露、run025 BLOCKED和D09历史成本/次数UNKNOWN保留。没有Solver/datacheck/入队/重试/新优化/RL或Git提交。本Run完成后停止。\n'''
 (R/'summary.md').write_text(summary,encoding='utf8')
 checklist={'version':'run046-pre-unblind-readiness-v1','frozen_predictions':True,'frozen_parameters_and_SPT_losses':True,'frozen_validation_protocol':True,
  'synthetic_tests_passed':11,'curves_and_deployed_tables_verified':True,'bundle_and_payload_hashes_verified':True,
  'new_unblinding_authorization':False,'independent_untouched_reviewer_assigned':False,
  'post_authorization_experiment_material_state_and_definitions':'UNKNOWN_UNTIL_AUTHORIZED_AUDIT','physical_accuracy_acceptance_threshold':None,
  'exact_historic_all_FE_attempt_cost':'UNKNOWN, explicit ledger retains interrupted D09 limitations',
  'decision':'READY_TO_REQUEST_PREREGISTERED_UNBLIND_COMPARISON; no claim of completed independent validation','holdout_not_opened_or_rehashed':True}
 write_new(P/'readiness_checklist.json',checklist)
 meta=read(R/'run.json');save_meta=meta.copy();write_new(R/'checkpoints/run_before_finalize.json',save_meta)
 meta.update(status='WARNING',end_time=now(),decision=receipt['state'])
 meta['inputs']=[{'path':p,'sha256':sha(ROOT/p),'role':'allowed frozen evidence'} for p in ['run/run_039/summary.md','run/run_043/summary.md','run/run_045/summary.md','run/run_045/artifacts/private/main/analysis.json','inverse/hollomon.py']]
 output_files=[A/'freeze_receipt.json',bundle,manifest_path,F/'frozen_inversion_results.json',F/'independent_validation_protocol.json',F/'independent_validation_protocol.md',F/'candidate_constitutive_comparison.png',P/'validation_tests.json',P/'readiness_checklist.json',A/'freeze_candidates.py',A/'validation_metrics.py',A/'test_validation_metrics.py',A/'seal_freeze.py',R/'summary.md']
 meta['outputs']=[{'path':rel(p),'role':'frozen evidence','sha256':sha(p)} for p in output_files]
 meta['validation']=[{'check':'two_candidate_curve_and_material_table_identity','status':'PASS','evidence':'10803 samples each; exact51/40 deployed rows'},
  {'check':'synthetic_validation_metrics_tests','status':'PASS','evidence':'11 tests, no experimental holdout read'},
  {'check':'frozen_package_hashes','status':'PASS','evidence':rel(A/'freeze_receipt.json')},
  {'check':'ready_to_request_unblinding','status':'PASS','scope':'preregistered comparison permission only, no access yet'},
  {'check':'independent_same_material_validation','status':'WARNING','scope':'material state/definitions/uniformity and untouched reviewer not confirmed; no physical PASS threshold'},
  {'check':'historical_exposure_and_attempt_cost','status':'WARNING','scope':'history retained; unknown totals not fabricated'}]
 meta['errors']=[{'code':'READONLY_DIAGNOSTIC_DEFAULT_ENCODING','severity':'INFO','message':'One display-only read used Windows GBK and failed; repeated with explicit UTF-8 successfully, no data changes','resolution':'UTF-8 retained for all frozen artifacts'}]
 atomic(R/'run.json',meta)
 idx=ROOT/'run/README.md';s=idx.read_text(encoding='utf8');assert '## run_046' not in s
 temp=idx.with_name(idx.name+'.tmp');temp.write_text(s.rstrip()+'\n\n## run_046 — 候选本构冻结与独立验证准备\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_046 | 冻结两组本构及SPT结果，预注册独立验证并封装hash证据 | WARNING / FROZEN_AWAITING_EXPLICIT_UNBLIND_AUTHORIZATION | [summary](run_046/summary.md) |\n\n不解盲、不求解；停止等待用户明确授权。\n',encoding='utf8');temp.replace(idx)
 sp=ROOT/'status/PROJECT_STATUS.md';s=sp.read_text(encoding='utf8');heading='# SMALL-PUNCH 项目状态\n';assert s.startswith(heading)
 text=heading+'\n## 当前状态 — run_046（2026-10-26，Asia/Shanghai）\n\n**WARNING / FROZEN_AWAITING_EXPLICIT_UNBLIND_AUTHORIZATION。** 当前探索性优化阶段结束，已冻结D01最佳已评估及I08替代候选完整参数、0–0.9真总应变预测及原Abaqus塑性表、最新SPT Loss与点级PASS证据。独立验证协议与主窗/误差/缺失/颈缩规则在任何新拉伸访问前冻结，11项合成测试及完整hash封包核验通过。可以申请明确解盲比较授权；同材状态、定义及未暴露复核人员仍需核实，不能宣称已完成验证或唯一识别。见[run_046](../run/run_046/summary.md)。无新求解/入队/优化/解盲；历史暴露和BLOCKED保留，完成后停止。\n\n'+s[len(heading):]
 temp=sp.with_name(sp.name+'.tmp');temp.write_text(text,encoding='utf8');temp.replace(sp)
 write_new(A/'manifest.json',{'at':now(),'files':[{'path':rel(p),'sha256':sha(p),'private':p.is_relative_to(P)} for p in output_files],'freeze_state':receipt['state']})
 for p in output_files+[A/'manifest.json',R/'run.json']:
  hub.artifact(session['task_id'],session['identity']['agent_id'],p,{'run':'run_046','scope':'SPT-only predictions and prospective validation; no unblinding or FE'},version='run046-v1')
 result={'output_run':'run_046','status':receipt['state'],'frozen_candidates':differences,'receipt_path':rel(A/'freeze_receipt.json'),'bundle_sha256':sha(bundle),'protocol_sha256':sha(F/'independent_validation_protocol.json'),'unblind_authorized':False,'new_fe':0}
 hub.message(session['task_id'],session['identity']['agent_id'],'MAIN',result,'run046-frozen-result-v1');hub.finish(session['lease'],result,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain()
 write_new(R/'checkpoints/completion.json',{'at':now(),'task_id':session['task_id'],'state':receipt['state'],'receipt_sha256':sha(A/'freeze_receipt.json'),'hub_chain_valid':True,'new_fe':0,'holdout_access':False})
 print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
