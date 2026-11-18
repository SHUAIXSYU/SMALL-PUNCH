"""Finalize MAIN evidence and role handoff after independent review; no FE actions."""
import json,sys,hashlib,subprocess
from pathlib import Path
from datetime import datetime
ROOT=Path(r'E:\Projects\SMALL-PUNCH');R=ROOT/'run/run_045';A=R/'artifacts';P=A/'private';O=P/'main'
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(ROOT).as_posix()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def now():return datetime.now().astimezone().isoformat()

def main():
 analysis=read(O/'analysis.json');audit=read(P/'execution_audit.json');ids=read(A/'task_ids.json')
 hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=ids['identity']
 assert hub.task(ids['odb_task_id'])['execution_state']=='COMPLETED'
 # Read this task only: global role inbox polling could retrieve sealed historical results.
 odbtask=hub.task(ids['odb_task_id'])
 messages=[{'task_id':ids['odb_task_id'],'access_method':'public Hub.task scoped completed structured result; no global inbox scan','result':json.loads(odbtask['result'])}]
 save(P/'received_odb_messages.json',messages)
 assert odbtask['execution_state']=='COMPLETED' and odbtask['evidence_state']=='RECORDED'
 t=hub.task(ids['main_review_task_id']);assert t['execution_state']=='PENDING'
 lease=hub.claim(ids['main_review_task_id'],actor,'run045-science-main-claim-v1');save(P/'science_lease.json',lease)
 checks=read(P/'main_log_crosscheck.json')
 for s,c in zip(analysis['points'],checks):
  assert s['point_id']==c['point_id'] and s['accepted_increments']==c['msg_total_increments']==c['sta_accepted_rows']
  assert s['cutback']==c['msg_cutbacks']==c['sta_rejected_rows']
  assert c['sta_success'] and c['msg_negative_eigenvalue_messages']==0
 for r in audit['records']:
  assert sha(ROOT/r['inp_path'])==r['inp_sha256']
  for f in r['files'].values():assert sha(ROOT/f['path'])==f['sha256']
 rank=analysis['ranking'];points=analysis['points'];qualified=sum(p['qualification']=='PASS' for p in points)
 decision='PASS_TWO_POINT_ADJACENT_REFINEMENT_ONLY' if qualified==2 else 'BLOCKED_POINTWISE_REFINEMENT_QUALIFICATION'
 recommendation=('优先冻结D01/I08探索性候选集合及局限，开展补偿谷地与参数不确定性研究；暂不恢复BO/DE。可准备预注册独立拉伸验证方案，须用户明确解盲授权后才能读取。' if qualified==2 else '优先诊断未过门槛的具体数值差异，暂停继续优化和最终本构冻结；不自动追加求解。')
 lines=['# run_045 — D01/I08 数值细化结果与可识别性',f'\n**WARNING / {decision}。** 两项真实单次求解均完成，真实ODB会话通过AgentHub领取并返回证据，MAIN独立复算。数值资格只限本次各自相邻增量比较。',
 '\n## 真实执行','\n| 点 | queue_id | Datacheck | Full | 总耗时 s | 接受增量 | cutback |','|---|---|---|---|---:|---:|---:|']
 for p,r in zip(points,audit['records']):lines.append(f"| {p['point_id']} | {p['queue_id']} | 0 / success | {r['queue_status']} | {p['actual_runtime_s']} | {p['accepted_increments']} | {p['cutback']} |")
 lines+=['\n公开API单条History、每相位日志一次START/END及返回0、STA成功终止、文件hash与冻结输入一致；非仅凭ODB存在。14CPU/0GPU。Queue/Settings/Project DB在只读审计前后hash一致。耗时为Runner Datacheck+Full墙钟，MSG内Full solver墙钟另有记录，不混用。',
 '\n## 五项冻结数值门槛','\n| 点 | RMSE N ≤2 | 最大差 N ≤7.1445 | 最大正则相对差 ≤5% | absΔLoss ≤0.00065 | absΔPEEQ ≤0.02 | 判定 |','|---|---:|---:|---:|---:|---:|---|']
 for p in points:lines.append(f"| {p['point_id']} | {p['force_rmse_n']:.10g} | {p['max_absolute_force_n']:.10g} | {p['max_regularized_relative']*100:.10g}% | {abs(p['loss_change']):.12g} | {p['max_saved_peeq_absolute_change']:.10g} | {p['qualification']} |")
 lines+=['\n比较为原始→细化，0–1.2mm/241点、线性插值、原符号及正则分母max(abs原始载荷,71.445N)未变；无平滑、删点、移零或外推。最大保存PEEQ不包括未保存/拒绝试算的应变极值。',
 '\n## Loss与排序','\n| 点 | 原始Loss | 细化Loss | 有符号ΔLoss | 对实验RMSE N |','|---|---:|---:|---:|---:|']
 for p in points:lines.append(f"| {p['point_id']} | {p['original_loss']:.15g} | {p['validation_loss']:.15g} | {p['loss_change']:+.12g} | {p['refined_rmse_to_experiment_n']:.8g} |")
 lines +=[f"\n原间隔={rank['original_gap']:.12g}；两次absΔLoss之和={rank['sum_abs_loss_changes']:.12g}，比值={rank['ratio_to_original_gap']:.8g}；新间隔(I08−D01)={rank['refined_gap_i08_minus_d01']:.12g}。实际排序={rank['observed_refined_ranking']}；保守筛查={rank['screen']}。单次细化变化不是严格误差上界，也不是统计置信区间。",
 '\n## 数值和接触证据','\nMAIN独立STA/MSG复核D01 804接受/1拒绝、I08 801接受/0拒绝；负特征值消息均0。ZERO_MOMENT头与path-based tracking输入警告保留，接受/拒绝及接触力平衡详见ODB诊断。原run025 BLOCKED不改写。']
 for p in points:
  lines +=[f"\n### {p['point_id']} 诊断",'```json',json.dumps({'max_saved_peeq':p['max_saved_peeq'],'material_coverage':p['material_coverage'],'warning_events':p['warnings_by_outcome'],'blockers':p['numerical_blockers'],'contact_review':p['contact_review'],'local_jump_review':p['local_jump_review'],'focus_1p10_1p16':p['focus_summary']},ensure_ascii=False,indent=2),'```']
 lines+=['\n1.10–1.16mm接触压力与原始接受帧证据见各点focus_1p10_to_1p16mm.json/CSV及ODB报告。CPRESS>0只是受压接触代理，COPEN非有限值或绝对值≥1e30为缺失哨兵，不能解释为物理间隙；局部相关性不自动确定成因。',
 '\n## 参数可识别性',f"\n细化两条FE互比RMSE={analysis['refined_pair']['refined_mutual_fd_rmse_n']:.8g}N，最大差={analysis['refined_pair']['refined_max_abs_difference_n']:.8g}N。原参数与材料表完全未变，因此预测单轴曲线差异不因增量细化消失。真总应变1%时两候选约278.97/364.81MPa；10%时约474.49/520.55MPa。小应变段差异大、高应变逐渐接近；PEEQ是多轴等效塑性标量，不能直接当作单轴真总应变。",
 '\n分区残差见residual_intervals.csv，按固定[0,.3),[.3,.6),[.6,.9),[.9,1.2]mm分箱，未重新选Loss窗口。D01/I08为参数相距明显的竞争性低Loss候选，配合已有24个同基准数值契约可评分点提示补偿结构；此次同点细化不增加独立参数点。没有连续谷地的真实密集FE证据，不推断严格全局唯一性/非唯一性或正式置信区间。D01靠近150MPa下界的风险保留，未据此扩大边界。',
 '\n## 决策',f'\n{recommendation}',
 '\n建议先利用已有SPT残差形状、位移分区和预测本构集合量化探索性不确定性；如需新增识别点，另立求解前协议，横跨补偿方向并与数值差异比较，单独申请预算。严禁把更低Loss自动解释为SA508真实本构。当前不宣称网格收敛、全域数值稳定或夹具/实验物理验证完成。',
 '\n## 证据、边界与停止',
 '\n输入清单、比较契约及实现hash复核；原12项比较和4项排序测试重跑通过。所有曲线/实验可恢复产物位于Git忽略私有区。新Solver/datacheck/入队/重试/BO/DE/RL均0；两项先前授权已启动并各消耗1，共2，剩余0。历史拉伸信息暴露记录保留，本Run未读封存文件或派生结果，没有commit/push。完成后停止，等待新授权。']
 lines+=['\n## 固定分区残差数据','\n| 点 | 位移mm | 该区间残差RMSE N | 均偏差N | 全Loss占比 |','|---|---|---:|---:|---:|']
 for v in analysis['residual_intervals']:lines.append(f"| {v['point_id']} | {v['lo_mm']:.1f}–{v['hi_mm']:.1f} | {v['refined_residual_rmse_n']:.6g} | {v['refined_bias_n']:+.6g} | {v['loss_fraction']*100:.4g}% |")
 lines +=[f"\n两点观测细化F–D RMSE之和/细化后两候选互差RMSE={analysis['observed_refinement_signal_ratio']:.6g}。此为本次观测信号尺度比较，不是误差上界。接近的标量Loss不等于F–D形状相同；未获得实验重复性/测量误差分布，不能把低Loss集合转为正式参数置信区间。"]
 report='\n'.join(lines)+'\n';(O/'REPORT.md').write_text(report,encoding='utf-8')
 budget={'authorized_jobs':2,'started_attempts':2,'completed_software':2,'consumed':2,'remaining':0,'new_fe_started_by_this_analysis':0,'no_retries':True,'source_queue_manifest':'run/run_044/artifacts/private/queue_manifest.json'};save(P/'budget_ledger.json',budget)
 summary=f"# run_045 — D01/I08 数值细化与可识别性\n\n**WARNING / {decision}。** 两项真实单次Datacheck+Full完成；真实ODB会话提取、MAIN独立复算，{qualified}/2通过冻结五项相邻细化门槛。实际排序{rank['observed_refined_ranking']}，排序变化筛查{rank['screen']}。\n\n{recommendation}\n\n完整[私有报告](artifacts/private/main/REPORT.md)、[五指标与排序](artifacts/private/main/analysis.json)、[F–D及残差](artifacts/private/main/fd_refinement_residuals.png)、[预测本构](artifacts/private/main/predicted_constitutive_curves.png)。原历史BLOCKED保留，本Run无新求解/入队/重试或解盲，完成后停止。\n"
 (R/'summary.md').write_text(summary,encoding='utf-8')
 meta=read(R/'run.json');meta.update(status='WARNING' if qualified==2 else 'BLOCKED',end_time=now(),decision=decision)
 meta['validation']=[{'check':'real_execution_and_output_identity','status':'PASS','evidence':'two single successful phases, history and source hashes'},
 {'check':'real_odb_session_and_main_receipt','status':'PASS','evidence':ids['odb_task_id']},
 {'check':'frozen_five_gates','status':'PASS' if qualified==2 else 'BLOCKED','evidence':rel(O/'analysis.json')},
 {'check':'ranking_screen','status':'PASS' if rank['sum_abs_loss_changes']<rank['original_gap'] and qualified==2 else 'WARNING','evidence':rank['screen']},
 {'check':'uniqueness_and_physical_validation','status':'WARNING','evidence':'No strict global uniqueness, mesh convergence or tensile validation claimed'},
 {'check':'reused_tests','status':'PASS','evidence':'12 comparison + 4 ranking tests'}]
 files=[O/'candidate_constitutive_set.json',O/'analysis.json',O/'REPORT.md',O/'frozen_grid_comparison.csv',O/'residual_intervals.csv',O/'predicted_constitutive_samples.csv',O/'fd_refinement_residuals.png',O/'predicted_constitutive_curves.png',P/'execution_audit.json',P/'main_log_crosscheck.json',P/'budget_ledger.json',P/'received_odb_messages.json',P/'reused_tests.json',R/'summary.md',A/'main_analysis.py',A/'audit_dispatch.py',A/'finalize_run.py']
 meta['outputs']=[{'path':rel(p),'sha256':sha(p)} for p in files];save(R/'run.json',meta)
 idx=ROOT/'run/README.md';s=idx.read_text(encoding='utf8');assert '## run_045' not in s
 idx.write_text(s.rstrip()+f'\n\n## run_045 — D01/I08 真实数值细化与可识别性\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_045 | 两项真实ODB、冻结五指标、Loss排序与竞争本构 | {meta["status"]} / {decision} | [summary](run_045/summary.md) |\n\n未启动新求解或解盲，历史BLOCKED保留，完成后停止。\n',encoding='utf8')
 sp=ROOT/'status/PROJECT_STATUS.md';s=sp.read_text(encoding='utf8');heading='# SMALL-PUNCH 项目状态\n';assert s.startswith(heading)
 sp.write_text(heading+f'\n## 当前状态 — run_045（2026-10-26，Asia/Shanghai）\n\n**{meta["status"]} / {decision}。** 两项真实单次Datacheck+Full完成，真实ODB/MAIN独立核验，{qualified}/2通过冻结五指标；排序{rank["observed_refined_ranking"]}。{recommendation} 完整证据见[run_045](../run/run_045/summary.md)。原run025 BLOCKED及信息暴露保留；无新增求解、入队、重试或解盲，停止等待授权。\n\n'+s[len(heading):],encoding='utf8')
 manifest={'at':now(),'files':[{'path':rel(p),'sha256':sha(p)} for p in files]};save(P/'evidence_manifest.json',manifest)
 for p in files+[P/'evidence_manifest.json',R/'run.json']:hub.artifact(ids['main_review_task_id'],actor['agent_id'],p,{'run':'run_045','source':'real ODB Agent plus independent MAIN fixed comparison','no_new_solver':True},version='run045-v1')
 result={'output_run':'run_045','decision':decision,'points':points,'ranking':rank,'recommendation':recommendation,'budget':budget,'report':rel(O/'REPORT.md')}
 hub.message(ids['main_review_task_id'],actor['agent_id'],'MAIN',result,'run045-main-result-v1');hub.finish(lease,result,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain()
 save(R/'checkpoints/completion.json',{'at':now(),'decision':decision,'task_ids':ids,'hub_chain_valid':True,'qualified':qualified,'new_fe':0,'sealed_data_accessed':False,'manifest_sha256':sha(P/'evidence_manifest.json')})
 print(json.dumps({'decision':decision,'qualified':qualified,'ranking':rank,'hub_chain':True}))
if __name__=='__main__':main()
