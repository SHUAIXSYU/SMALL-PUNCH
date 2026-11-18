"""Register existing read-only diagnosis; retain historical run025 qualification."""
import hashlib,json,sys,subprocess
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_026';A=R/'artifacts';P=A/'private'
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from agenthub_sp_invopt.hub import Hub
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def now():return datetime.now().astimezone().isoformat()
diag=read(P/'diagnosis.json');session=read(P/'main_session.json')
assert diag['frozen_qualification']=='BLOCKED_V01_NUMERICAL_QUALIFICATION'
assert diag['source_count']=={'C':170,'V01':274}
assert abs(diag['full']['rmse_difference_n']-3.9987751586240563)<1e-10
assert abs(diag['full']['max_abs_difference_n']-19.558200999730843)<1e-10
assert not (ROOT/'run/run_023/artifacts/solver/SPIO_R023_V02_NP').exists() or not any((ROOT/'run/run_023/artifacts/solver/SPIO_R023_V02_NP').iterdir())
assert read(ROOT/'run/run_025/artifacts/private/main_comparison.json')['qualification']=='BLOCKED_V01_NUMERICAL_QUALIFICATION'
for key,path in [('C','run/run_014/artifacts/solver/SPIO_R014_Q200_N010/SPIO_R014_Q200_N010.odb'),('V01','run/run_023/artifacts/solver/SPIO_R023_V01_CTR/SPIO_R023_V01_CTR.odb')]:
 assert sha(ROOT/path)==diag['contact_odb_sha256'][key]
for key,digest in diag['source_sha256'].items():
 assert sha(ROOT/({'C_curve':'run/run_014/artifacts/odb/punch_force_displacement.csv','C_raw':'run/run_014/artifacts/odb/punch_history_raw.csv','V_curve':'run/run_025/artifacts/private/odb/force_displacement.csv','V_raw':'run/run_025/artifacts/private/odb/raw_history.csv','target':'run/run_017/artifacts/private/canonical_fd_source_confirmed.csv','contact':'run/run_026/artifacts/private/contact_frames.csv','C_sta':'run/run_014/artifacts/solver/SPIO_R014_Q200_N010/SPIO_R014_Q200_N010.sta','C_msg':'run/run_014/artifacts/solver/SPIO_R014_Q200_N010/SPIO_R014_Q200_N010.msg','V_sta':'run/run_023/artifacts/solver/SPIO_R023_V01_CTR/SPIO_R023_V01_CTR.sta','V_msg':'run/run_023/artifacts/solver/SPIO_R023_V01_CTR/SPIO_R023_V01_CTR.msg','sensitivity':'run/run_022/artifacts/private/analysis/sensitivity.json'}[key]))==digest
ignored=subprocess.run(['git','check-ignore','--quiet','run/run_026/artifacts/private/diagnosis.json'],cwd=ROOT).returncode==0
assert ignored
summary='''# run_026 — V01 数值差异定向诊断

**WARNING：定向离线诊断完成；run_025 的 `BLOCKED_V01_NUMERICAL_QUALIFICATION` 不变。** C 与 V01 的冻结241点力差 RMSE 3.998775 N、最大差19.558201 N（1.14 mm）。V01 原始接受帧在1.125–1.131 mm增载22.474 N；原模型在1.138811 mm的真实保存节点仍比V01低19.536 N，因此差异不只是末段插值。保存帧接触压力与接触转变相吻合，但无法从两次计算唯一确认数值成因。

1.10–1.20 mm的21个固定点贡献约68.86%的力差平方和；全窗口差为实验参考力的0.280%、已观察最小参数扰动RMS信号的9.97%。中心Loss变化−0.0004900，已评估点排序不变；run_022弱敏感性方向和未计算近邻排序尚无数值误差界。

建议先另行授权**一个**同中心、更小最大增量的定向数值验证，再审议受限探索性BO/DE。V02仍未入队；本轮无Solver、Datacheck、入队或优化。完整计算、区间表、局部接触字段、原始采样与两张图存于Git忽略的[私有报告](artifacts/private/main_report.md)和[证据目录](artifacts/private/diagnosis.json)。保留封存验证资料禁读与历史信息暴露声明。
'''
(R/'summary.md').write_text(summary,encoding='utf8')
meta=read(R/'run.json');meta.update(status='WARNING',stage='Targeted offline diagnosis complete; prior numerical qualification remains BLOCKED',end_time=now(),outputs=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'role':role} for p,role in [(R/'summary.md','Public summary'),(P/'main_report.md','Private scientific report'),(P/'diagnosis.json','Structured metrics'),(P/'contact_extraction.json','Read-only ODB contact evidence'),(P/'full_difference.png','Whole-window plot'),(P/'focus_105_120_readable.png','Local contact plot')]],validation=[{'check':'source_odb_immutable','status':'PASS','scope':'Both ODB hashes before/after read unchanged'},{'check':'frozen_formula_reproduction','status':'PASS','scope':'241-point RMSE, max difference and both Loss values reproduce run025'},{'check':'contact_field','status':'PASS','scope':'Both ODBs contain same 67-node contact pair CPRESS/COPEN at saved frames'},{'check':'causal_mechanism','status':'WARNING','scope':'Contact transition and pressure correlate with force path; two discretizations insufficient for unique cause'},{'check':'prior_qualification','status':'BLOCKED','scope':'run025 frozen force RMSE/max gates remain failed; V02 withheld'}],errors=[{'severity':'INFO','code':'OFFLINE_SCRIPT_REPAIRS','message':'Three offline diagnostic script attempts preserved in checkpoints/analysis_attempts.json; no solver or queue calls'}])
(R/'run.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
index=ROOT/'run/README.md';txt=index.read_text(encoding='utf-8-sig');assert '## run_026' not in txt
index.write_text(txt+'\n\n## run_026 — V01 数值差异定向诊断\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_026 | 既有F–D、接触场与数值事件的局部归因及科研影响 | WARNING（离线完成；run_025门槛仍BLOCKED） | [summary](run_026/summary.md) |\n\nV02未入队；下一步建议另行授权一个中心定向验证，未执行新求解。\n',encoding='utf8')
status=ROOT/'status/PROJECT_STATUS.md';txt=status.read_text(encoding='utf-8-sig');heading='# SMALL-PUNCH 项目状态\n';assert txt.startswith(heading)
status.write_text(heading+'\n## 当前状态 — run_026（2026-10-24，Asia/Shanghai）\n\n**WARNING：V01差异定向诊断完成；run_025 的 BLOCKED 数值资格保持。** 1.14 mm差异对应原模型稀疏接受帧与V01已接受的接触压力/反力变化；不能仅归因于插值，亦不能单凭两次计算确认唯一机制。建议下一步另行授权一个更小最大增量的中心验证，暂不进入实际BO/DE或修改接触/网格。V02未入队，见[run_026报告](../run/run_026/summary.md)。封存验证资料禁读和历史暴露事实保留，旧Run结论未改。\n\n'+txt[len(heading):],encoding='utf8')
files=[R/'summary.md',R/'run.json',P/'main_report.md',P/'diagnosis.json',P/'contact_probe.json',P/'contact_extraction.json',P/'contact_frames.csv',P/'contact_nodes_focus.csv',P/'interval_metrics.csv',P/'focus_aligned.csv',P/'focus_events.csv',P/'raw_focus.csv',P/'full_difference.png',P/'focus_105_120_readable.png',P/'probe_contact_odb.py',P/'extract_contact_readonly.py',P/'diagnose.py',P/'render_focus.py',R/'checkpoints/analysis_attempts.json']
manifest={'at':now(),'task_id':session['task_id'],'methods':['Abaqus 2024 Python readOnly ODB contact field extraction','Torch-GPU NumPy frozen-grid offline computation','STA/MSG accepted-attempt alignment'],'files':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':sha(p),'private':p.is_relative_to(P)} for p in files]}
(A/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
files.append(A/'manifest.json')
h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=3600);h.heartbeat(session['lease'])
for p in files:h.artifact(session['task_id'],session['identity']['agent_id'],p,{'run':'run_026','provenance':'Existing run014/run023/run025/read-only contact fields and frozen experimental grid; no Solver'},version='run026-v1')
result={'status':'WARNING_TARGETED_DIAGNOSIS_COMPLETE','prior_qualification':'BLOCKED_V01_NUMERICAL_QUALIFICATION','max_difference_n':diag['full']['max_abs_difference_n'],'max_at_mm':diag['full']['max_at_mm'],'rmse_n':diag['full']['rmse_difference_n'],'cause':'Contact-transition/accepted-path difference supported; precise cause unresolved','recommended_next':'One separately authorized center max-increment refinement before limited BO/DE','V02_queued':False,'new_solver_jobs':0,'report':'run/run_026/artifacts/private/main_report.md'}
h.message(session['task_id'],session['identity']['agent_id'],'MAIN',result,'run026-main-diagnosis-result-v1');h.finish(session['lease'],result,evidence_state='RECORDED',science_state='WARNING')
checkpoint={'at':now(),'run_status':'WARNING','prior_qualification':'BLOCKED_V01_NUMERICAL_QUALIFICATION','task_id':session['task_id'],'manifest_sha256':sha(A/'manifest.json'),'run_json_sha256':sha(R/'run.json'),'new_solver_jobs':0,'V02_queued':False,'hub_chain_verified':h.verify_chain()}
(R/'checkpoints/completed.json').write_text(json.dumps(checkpoint,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'task_id':session['task_id'],'status':result['status'],'manifest_files':len(files),'hub_chain_verified':checkpoint['hub_chain_verified']}))
