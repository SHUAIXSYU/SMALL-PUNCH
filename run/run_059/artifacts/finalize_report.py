"""Finalize real Phase2 results; preserve run058 Phase1 and freeze future decisions."""
from common import *
import numpy as np,shutil
sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub

def main():
 audit=read(P/'execution_audit.json');quality=read(P/'main_independent_checks.json');a=read(P/'study_A_local_secants.json');b=read(P/'study_B_frozen_parameter_recovery.json');eq=read(P/'accepted_equilibrium_and_local_contact_v2.json');ids=read(P/'task_ids.json');integrity=read(P/'predictor_integrity_before_new_response.json')
 assert len(quality['records'])==4 and all(r['SCIENTIFIC_SCOREABILITY']=='SCOREABLE_EXPLORATORY' for r in quality['records'])
 assert read(P/'independent_metric_verification.json')['status']=='PASS'
 assert len(b['metrics'])==4 and b['no_training_or_tuning']
 source_before=read(P/'protected_sources_before.json')
 for path,h in source_before.items():assert sha(R/path)==h,path
 for path,h in audit['protected_after'].items():assert sha(R/path)==h,path
 for r in audit['records']:
  assert sha(R/r['inp_path'])==r['inp_sha256']
  for item in r['files'].values():assert sha(R/item['path'])==item['sha256']
 start=read(RUN/'checkpoints/start.json');assert git('rev-parse','HEAD')==start['git']['head'] and git('diff','--cached','--name-status')==start['git']['staged']
 oldgit=read(R/'run/run_057/checkpoints/start.json');assert sha(R/'.gitignore')==oldgit['gitignore_sha256']
 for item in oldgit['local_CAE']:assert sha(R/item['path'])==item['sha256']
 full=next(x for x in b['metrics'] if x['model']=='full_ridge');predrows=rows(P/'prospective_parameter_predictions.csv')
 decision={'version':'run059-real-prospective-scientific-decision-v1','at':now(),'EXECUTION':'PASS','NUMERICAL_QUALITY':'WARNING','LOCAL_IDENTIFIABILITY':'LIMITED','PROSPECTIVE_PARAMETER_PREDICTION':'PARTIAL','REAL_MATERIAL_VALIDATION':'NOT_EVALUABLE','scoreable_count':4,'same_numerical_contract':True,'I06_status':'QUALIFIED_WITH_LIMITATIONS','time_step_and_finite_difference_h_convergence':'NOT_EVALUABLE','Fisher_confidence_intervals':'NOT_EVALUABLE','primary_conditions':{k:a['views'][k]['condition_number'] for k in ['two_loads','five_features','full241']},'only_primary_model_better_than_constant':'full_ridge','primary_models_passing_complete_frozen_resolution_goal':[],'raw_directions_correct':{r['model']:r['raw_direction_correct_count'] for r in b['metrics']},'weak_fullcurve_half_step_RMS_N':a['views']['full241']['weak_half_step_force_RMS_N'],'P03':'OUTSIDE_TRAINING_HULL; full_ridge n error .0085869432 > half-design-step .006; warning retained','conclusion':'FE finite-amplitude local map rank2 with highly coupled columns; fullcurve retains more empirical recovery than small fixed views, but no frozen inverse meets all halfstep criteria; no unique real material identification','recommendation':'continue interpretable feature diagnostics with fullcurve benchmark, not a validated two-feature formula; do not add complexity or optimize to conceal current failure','minimum_next_FE_proposal':{'currently_authorized':0,'first_gate_unique_jobs':1,'purpose':'I06 same-parameter initial.001 max.00125 versus existing max.0025; all physical controls unchanged, only if separately authorized','scope_limit':'point-specific numerical reference only; not entire four-arm Jacobian validation','later_conditional_not_authorized':{'maximum_jobs':2,'purpose':'opposed weak normalized-parameter-direction contrasts, after numerical evidence gate; new separately frozen design/authorization required'}},'no_new_FE_or_enqueue_or_retry':True}
 save(P/'scientific_decision.json',decision)
 total=sum(r['actual_runtime_s'] for r in audit['records']);table=quality['records']
 text=['# run059 — run058 Phase2 四点前瞻识别评价','',f'完成时间：{now()}，Asia/Shanghai。**WARNING / REAL_FOUR_POINT_PROSPECTIVE_EVALUATION_COMPLETE**。','',
 '按项目“每项独立研究产出新Run”规则使用run059；复用run058预设执行审计/四ODB/MAIN科学任务，不改写run058第一阶段或run055–057冻结文件。用户完成通知已收到；本轮新增求解/Datacheck/入队/重试/INP/训练均0。','',
 '## 1. 分类结论','',
 '|维度|判定|范围|','|---|---|---|','|EXECUTION|PASS|4/4单次DC+Full真实完成，4次旧授权已消耗，无重试|','|NUMERICAL_QUALITY|WARNING|完整且探索性可评分；保留cutback/接触演化/残差接受及缺少点级增量误差证据|','|LOCAL_IDENTIFIABILITY|LIMITED|同基点同控制有限幅割线代数秩2，但方向高度相关；不是严格收敛微分导数或全局唯一性|','|PROSPECTIVE_PARAMETER_PREDICTION|PARTIAL|全曲线优于常数且方向4/4，但所有主预测器均未满足完整冻结半步目标|','|REAL_MATERIAL_VALIDATION|NOT_EVALUABLE|本轮真值为FE输入参数，不是独立SA508材料真值|','',
 '## 2. 真实执行审计与数值门控','',
 '通过当前正式AbqJobPilot公开API逐queue_id查询Queue/History/show_job/status/locate_outputs，核对Project b87d2cd6-8519-4ac3-bae6-7eb989fb2dae、14CPU0GPU、每项attempt_no=1且仅一个已启动run；日志每项DC与Full各一次start/end、return_code0，STA成功终态与ODB成功终态相互支持。Runtime CLEAN、Runner owner ABSENT、无活动Solver；没有凭ODB存在直接宣告成功。','',
 '|点|Job / queue_id|原始FD点|cutback|最大PEEQ|DC秒|Full秒|总秒|ALLPD/J|','|---|---|---:|---:|---:|---:|---:|---:|---:|']
 for row,rr in zip(table,audit['records']):
  text.append(f'|{row["candidate_id"]}|{row["job_name"]} / {row["queue_id"]}|{row["points"]}|{row["cutbacks"]}|{row["max_saved_PEEQ"]:.9f}|{rr["phase_evidence"]["DATACHECK_RUNNING"]["duration_s"]:.0f}|{rr["phase_evidence"]["FULL_RUNNING"]["duration_s"]:.0f}|{row["runtime_s"]}|{row["energy_final"]["ALLPD"]:.9f}|')
 text += ['',f'合计公开运行时长{total}秒（{total/60:.2f}min），14CPU分配成本{total*14/3600:.6f}核小时；不等于实测CPU利用率或算法训练成本。DC/Full日志时长与总时长有启动/收尾开销差异，分别保留。',
 '四项软件均COMPLETED_WITH_WARNINGS，MAIN判为SCOREABLE_EXPLORATORY。完整覆盖0–1.2mm，PEEQ全低于.85复核线及.9表末，无接受增量反力回退。原始Field/History U2/RF2逐点一致，实际RP Node ASM_SPT.1、Step_Punch_Displacement；u=-U2、F=-RF2，不取绝对值、不乘额外2pi。应力Pa/位移m/反力N；材料全表digest与冻结INP推导值一致，几何/BC/接触等及初始.001/最大.0025控制一致。',
 'MAIN独立解析STA/MSG：P01拒绝试算大应变9/负特征值1；P02大应变11/畸变1/负特征值2；P03大应变9/负特征值1/塑性迭代未尝试1；P04大应变7。接受trial均仅ZERO_MOMENT标题，DAT tracking诊断保留。拒绝trial标题不能作为已接受物理状态。',
 '逐接受STA attempt核对MSG最终接受证据：P01 443条普通force-converged+2条small-residual/estimated-correction接受；P02 432+1；P03 444+4；P04 428+0，总计1754条均有increment-completed与明确接受依据。初次严格字符串扫描未识别后者7条，原检查文件保留；依据实际MSG的EQUILIB. ACCEPTED文字完善解析v2，无修改Solver或科学门槛。配置准则接受不等于独立数值精度已证实。','',
 '## 3. 真实ODB会话与MAIN独立复核','',
 '现有SP-InvOpt ODB Codex会话被用户授权的跨会话消息激活，ODB:ODB-real-run059 / session81ee3fbf-a4d8-4ab6-836a-dcd7256518c1实际领取并完成四个原Hub任务；使用Abaqus2024自带SMAPython/odbAccess readOnly=True。36项正式Hub收据文件SHA、完整ODB文件清单和任务generation/session/producer均经MAIN核验。不是MAIN冒充ODB身份，也不是模拟worker。ODB保留Loss=null交MAIN；当前Loss是MAIN独立审查后用原冻结函数计算。',
 'MAIN逐点重核原始RF2/U2/时间、场与历史、0–1.2mm覆盖、2376积分点PEEQ最大值、源INP/ODB/STA/MSG/DAT/LOG哈希、表数据和符号，另以独立插值公式核对原生曲线与241点。每项具体复核见main_independent_checks.json。Hub正式完成结果/任务收据已读取，不读取无关MAIN历史收件箱；数据库消息不被误称自动唤醒证据。','',
 '## 4. Study A：冻结局部割线','',
 'x=ln(sigma_y/150)/ln(1000/150)，y=(n-.02)/.48，hx=hy=.025；Jx=(P02-P01)/.05、Jy=(P04-P03)/.05。载荷/1428.9N，斜率/(1428.9/1.2mm)，总面积/(1428.9*.0012m)，每view再除sqrt(m)。完全复用run057冻结local_secants实现；没有把量纲不同的未归一化列范数硬比较。下面是固定权重下的矩阵诊断，不是噪声加权Fisher信息。','',
 '|预注册输入|cos|夹角/度|smax|smin|条件数|eta_x|eta_y|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for name,v in a['views'].items():text.append(f'|{name}|{v["cosine"]:.9f}|{v["angle_deg"]:.6f}|{v["singular_values"][0]:.9f}|{v["singular_values"][1]:.9f}|{v["condition_number"]:.6f}|{v["axes"]["x"]["even_odd_ratio"]:.6f}|{v["axes"]["y"]["even_odd_ratio"]:.6f}|')
 text += ['',
 '三种主view全为代数rank2，但余弦均>.98，强烈共同幅值响应仍存在。固定五特征的条件数16.619比固定两载荷14.885更差，不能说“特征更多就独立信息更多”；完整曲线主比较最佳13.347，弱奇异方向稍增强。次级预注册独立3[F.15,F.30,K.60-.90]条件数10.499、早期2[F.15,F.30]17.116，只是先验已列出的方向诊断，未据此更换或训练主逆模型。',
 '完整曲线弱方向约(dx,dy)=(-.811161,+.584824)，显示减小sigma_y与增加n的补偿方向；其单位规范化半步线性响应RMS=3.092633N。sigma两侧真实响应RMS约23.744/24.799N，n两侧32.578/34.617N，明显大于弱组合信号。既有局部数据支持有限域参数耦合，不证明连续全局不可识别或唯一性。','',
 '|位移区间/mm|点数|Sx RMS/(N/x)|Sy RMS/(N/y)|cos|条件数|弱方向半步RMS/N|','|---|---:|---:|---:|---:|---:|---:|']
 for row in a['bands']:text.append(f'|{row["lo_mm"]:.1f}–{row["hi_mm"]:.1f}|{row["points"]}|{row["Sx_RMS_N_per_normalized_unit"]:.3f}|{row["Sy_RMS_N_per_normalized_unit"]:.3f}|{row["cosine"]:.6f}|{row["condition_number"]:.5f}|{row["weak_half_step_RMS_N"]:.6f}|')
 text += ['',
 '分区采用[lo,hi)且末段包括1.2mm，60/60/60/61共241点，无重复计权。早段方向相对较分离但绝对弱信号仅约1.25N；后段幅值更大、方向却更平行，末段条件数30.76。应联合不同阶段，不将后期较大载荷敏感性等同参数独立信息。',
 '完整窗口eta_x=.02348、eta_y=.06928，低于预设.20警示线，但不证明h收敛。所有主view相关旗标触发；条件数未越20不等于通过识别认证。未测得I06点级数值误差和观察/模型误差协方差，正式Fisher置信区间NOT_EVALUABLE，严格时间步及有限差分步长收敛NOT_EVALUABLE。','',
 '## 5. Study B：原预测器零重训前瞻检验','',
 f'新响应进入预测之前核验了原最终模型SHA {integrity["model_sha256"]}、训练25点SHA {integrity["training25_sha256"]}及ZIP/标准化/系数/lambda/代码/常数基线。原25点唯一材料参数，不使用250条外层预测当250样本，不使用新四点训练。最终推理前后SHA相同，逐项独立矩阵式再验预测。完整241点与特征模型都用实际新FE，没有重新拟合、筛选或裁剪输出。','',
 '|冻结主模型|sigma MAE/MPa|sigma RMSE/MPa|n MAE|n RMSE|原始方向正确|E_local|完整半步目标|','|---|---:|---:|---:|---:|---:|---:|---|']
 for v in b['metrics']:text.append(f'|{v["model"]}|{v["MAE_MPa_n"][0]:.6f}|{v["RMSE_MPa_n"][0]:.6f}|{v["MAE_MPa_n"][1]:.9f}|{v["RMSE_MPa_n"][1]:.9f}|{v["raw_direction_correct_count"]}/4|{v["E_local"]:.9f}|'+('PASS' if v['engineering_resolution_goal_met'] else 'NOT_MET')+'|')
 text += ['',
 '完整曲线相对常数I06，sigma/n MAE分别降低约18.99%/26.18%，RMSE分别降低约41.77%/39.82%，E_local从.707107降至.419760。它是唯一真正优于常数的主逆模型，原始方向4/4正确，但**没有任何主模型满足所有点所有坐标误差<=.0125的冻结目标**。因此总体PARTIAL而非PASS。',
 '全曲线P01的x误差.012508534略超.0125（不放宽）；P03的y误差.017889465明显超.0125，对应n误差.008586943，超过半步n=.006。P01边缘超限不是唯一失败原因；不能以舍入或平均误差掩盖P03。完整曲线最大sigma误差5.416216MPa，最大n误差.008586943。',
 '两载荷/五特征绝对方向均2/4；以model(new)-model(I06)诊断变化则3个Ridge均4/4方向正确，但这不是冻结原始预测的通过条件。其全域偏差不能被暗中重新居中。','',
 '|模型|P01增量幅度/真实|P02|P03|P04|','|---|---:|---:|---:|---:|']
 for v in b['metrics']:text.append('|'+v['model']+'|'+'|'.join(f'{x:.6f}' for x in v['incremental_active_amplitude_ratios'])+'|')
 text += ['',
 '幅度诊断独立于绝对预测：两载荷对n的增量仅恢复约7.7%–10.9%；五特征有所改善但不对称。全曲线增量约39.7%、68.7%、39.1%、114.7%，仍非一致1:1恢复，P03明显低估n负扰动。各点原始幅度、非活动轴串扰、误差与适用域见prospective_parameter_predictions.csv。七个其他原冻结模型仅按预注册次级协议执行，保存secondary_frozen_model_diagnostics.json，不提拔替换主结论。','',
 '## 6. P03凸包外推','',
 'P03真实输入(236.49902622197678MPa,.0848)是OUTSIDE_TRAINING_HULL；它虽高于单变量训练n最小.08且特征最近邻很近，仍在原联合参数凸包外。全曲线预测(239.66234257407248MPa,.09338694321799625)，sigma误差+3.163316MPa，n误差+.008586943。两载荷预测(201.710349MPa,.162634095)，五特征(213.040578MPa,.127257286)。全曲线更接近但回归向已有支持域收缩，不能把“预测落在凸包内”当作该真实测试点有训练支持。四个邻点不能证明广域外推能力。','',
 '## 7. 数值解释与证据边界','',
 '四项表/几何/接触/BC/控制完全兼容且接受警告/覆盖/PEEQ门控无阻塞，但均存在正常收敛路径中的cutback与接触压力重分布。P01/P02/P03约.858–.865mm局部载荷增加10.94–14.88N时，节点25新进入正CPRESS集合，提供接触演化相关证据；P04在1.13012–1.13312mm增加15.703N，没有新的正接触节点集合变化，不能从节点集合直接确定其成因。其接受attempt最终力平衡明确收敛。',
 '局部4–15N载荷步不是数值误差上界，也不意味着整条曲线不可信；同时，弱线性组合仅3.09N，必须保留接触路径/采样和增量误差对弱方向的影响风险。I06未点级增量精化，D01曾有的细化变化不能挪作本处界限。无法在本轮证明弱方向已严格数值分辨，因此LOCAL_IDENTIFIABILITY只判LIMITED，不能宣布严格置信区间、无噪声唯一逆映射或物理模型验证。','',
 '## 8. 次级实验SPT Loss（不是本轮研究目标）','',
 '用原run017-exploratory-fd-v1，固定0–1.2mm/241点、等权、Fref1428.9N、线性无外推、不移零/平滑，MAIN独立计算；实验不用来挑特征、重训或选择新参数。','',
 '|点|探索性Loss|实验RMSE/N|与I06响应差RMSE/N|','|---|---:|---:|---:|']
 for row in table:text.append(f'|{row["candidate_id"]}|{row["loss"]:.12f}|{row["RMSE_to_experiment_N"]:.6f}|{row["RMSE_vs_I06_N"]:.6f}|')
 text += ['',
 '这些分数只能作次级响应核验，不以最低者推荐新的材料答案；当前中心I06也是FE测试点，真实材料验证仍沿用正式NOT_EVALUABLE。','',
 '## 9. 科研决策与最小下一步','',
 '继续Feature-Based路线有价值，定位为解释性压缩/诊断和局部识别研究；目前不支持可验证的“两固定点唯一恢复sigma/n”工程公式。五特征改善回归误差但未改善局部条件数，说明矩阵几何、逆模型偏差和材料真实性是三个问题。全曲线保留更好的FE恢复能力作为性能与质量基线，但没有达到冻结全点半步标准，也不能因为平均精度较好改判PASS。',
 '先保留本次冻结测试结果，不为降低训练误差增加复杂度，也不恢复BO/DE/RL。可在另立任务后研究回归偏差/局部覆盖/特征权重等，但任何新四点参与开发后必须重新划分真正未见测试，不能改写本轮前瞻结论。',
 '当前新增FE授权0。若下一阶段需要定量可识别性证据，建议第一关仅申请1个I06同参数增量对照（初始.001、最大.00125，其余完全不变），专门估计本基点数值变化相对3.09N弱信号的量级；不重跑整个4点，不修改接触/网格。它只能给中心点证据，不能认证四臂或严格h收敛。若该关支持继续，再单独设计/授权最多2个弱方向正负组合点，检验补偿方向；不在本轮生成输入。',
 '未来身份/完整窗口/材料覆盖或严重接受态异常失败即停止，不自动补跑；若中心数值变化已与弱信号相当，先定位数值机制而非新增识别点。实验侧仍需要夹紧/摩擦/位移校正与观测不确定性证据；FE自洽结果不填补这些材料真实性缺口。','',
 '## 10. 交付与保护','',
 '结构化执行审计、真实ODB原始提取、MAIN独立检查、全部预测、5个预注册view矩阵、分区方向、数值事件、9张图、预测器前后哈希及证据清单均在本Run私有区；MAIN以旧run058科学任务登记最终科学判定。已完成4次预算消耗，零追加/重试/入队。旧run058第一阶段完整保留，源INP/ODB/实验与预测器未修改，Git HEAD/暂存两CAE删除/.gitignore与本地模型hash均保持。','未读取或利用封存拉伸及其既有分析；保留run015暴露历史，run046预测与run047/048正式NOT_EVALUABLE不变。完成后停止，等待用户新的科研决策。','']
 write(P/'scientific_report.md','\n'.join(text))
 ledger={'at':now(),'parent_authorization_run':'run_058','authorized':4,'actual_started_attempts':audit['consumed_started_attempts'],'software_completed':audit['software_completed'],'scoreable':4,'remaining_authorization':0,'automatic_retries':0,'new_solver_starts_this_analysis':0,'new_enqueue':0,'queue_ids':[r['queue_id'] for r in audit['records']],'future_FE_authorization':0}
 save(P/'authorization_consumption_final.json',ledger)
 sources={'at':now(),'old_frozen_sources_unchanged':len(source_before),'queue_Settings_Project_DB_unchanged_during_analysis':True,'input_ODB_sources_unchanged':True,'predictor_hash':integrity['model_sha256'],'git_head':git('rev-parse','HEAD'),'staged_unchanged':git('diff','--cached','--name-status')==start['git']['staged'],'local_CAE_retained':True,'protected_hashes':source_before}
 save(P/'final_preservation_check.json',sources)
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);tid=ids['science_task_id'];assert hub.task(tid)['execution_state']=='PENDING';lease=hub.claim(tid,ids['identity'],'run059-main-science-claim-v1');save(P/'science_lease.json',lease)
 files=[p for p in sorted(A.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and 'mplconfig' not in p.parts and p.name not in ['task_ids.json','identity.json','audit_lease.json','science_lease.json','evidence_manifest.json','agenthub_completion_receipt.json'] and not p.name.startswith('lease_')]
 entries=[{'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]
 save(P/'evidence_manifest.json',{'version':'run059-static-scientific-evidence-v1','at':now(),'files':entries,'excludes':['self','later completion receipt','sessions/leases','cache','live Run/index/status metadata']})
 registered=[]
 for p in files+[P/'evidence_manifest.json']:
  if p.is_relative_to(P):assert subprocess.run(['git','check-ignore','--quiet','--',rel(p)],cwd=R).returncode==0
  item=hub.artifact(tid,ids['identity']['agent_id'],p,{'run':'run_059','execution_run':'run_058','scope':'existing results read-only; MAIN-reviewed frozen A/B evaluation'},version='run059-final-v1');registered.append({'path':rel(p),'sha256':item['sha256']})
 body={k:decision[k] for k in ['EXECUTION','NUMERICAL_QUALITY','LOCAL_IDENTIFIABILITY','PROSPECTIVE_PARAMETER_PREDICTION','REAL_MATERIAL_VALIDATION']};body.update(run='run_059',report_path=rel(P/'scientific_report.md'),report_sha256=sha(P/'scientific_report.md'),evidence_manifest_path=rel(P/'evidence_manifest.json'),evidence_manifest_sha256=sha(P/'evidence_manifest.json'),consumed=4,new_FE=0,conditions=decision['primary_conditions'],primary_fullcurve_beats_constant=True,no_primary_passed_frozen_halfstep=True)
 msg=hub.message(tid,ids['identity']['agent_id'],'MAIN',body,'run059-final-scientific-handoff-v1');hub.finish(lease,body,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain()
 save(P/'agenthub_completion_receipt.json',{'at':now(),'science_task_id':tid,'execution_audit_task_id':ids['execution_audit_task_id'],'ODB_task_ids':ids['odb_task_ids'],'science_task':hub.task(tid),'registered_artifacts':registered,'outbox_message_id':msg['message_id'],'audit_chain_valid':True,'MAIN_read_real_ODB_completed_results':True,'no_automatic_other_session_notification_claim':True})
 write(RUN/'summary.md','# run_059 — run_058 Phase2 前瞻识别评价\n\n**WARNING：EXECUTION PASS / NUMERICAL_QUALITY WARNING / LOCAL_IDENTIFIABILITY LIMITED / PROSPECTIVE_PARAMETER_PREDICTION PARTIAL / REAL_MATERIAL_VALIDATION NOT_EVALUABLE。** 四项单次DC+Full完成，真实ODB会话经Hub领取并提取，MAIN独立核验4/4探索性可评分。三种主输入均为局部有限幅代数秩2但高度耦合；完整曲线冻结预测优于常数且方向4/4，却未通过所有点半步分辨门槛。\n\n见[私有科研报告](artifacts/private/scientific_report.md)、[科学判定](artifacts/private/scientific_decision.json)、[前瞻预测表](artifacts/private/prospective_parameter_predictions.csv)、[A矩阵](artifacts/private/study_A_local_secants.json)、[B评价](artifacts/private/study_B_frozen_parameter_recovery.json)、[证据清单](artifacts/private/evidence_manifest.json)、[AgentHub收据](artifacts/private/agenthub_completion_receipt.json)。使用新Run编号保留run058第一阶段，复用既有任务；所有冻结和I06限制不变。\n\n已授权四次真实尝试均已消耗；本轮新FE/Datacheck/入队/重试/训练/优化均0，未读拉伸，无Git提交。建议后续另行申请1个I06中心数值对照作为门控，当前不生成或执行。完成后停止。\n')
 important=[P/'scientific_report.md',P/'scientific_decision.json',P/'execution_audit.json',P/'study_A_local_secants.json',P/'study_B_frozen_parameter_recovery.json',P/'evidence_manifest.json',P/'agenthub_completion_receipt.json']
 save(A/'manifest.json',{'version':'run059-artifacts-v1','files':[{'path':rel(p),'sha256':sha(p),'private':True} for p in important]})
 j=read(RUN/'run.json');shutil.copyfile(RUN/'run.json',RUN/'checkpoints/run_before_complete.json');j.update(status='WARNING',end_time=now(),outcome='REAL_FOUR_POINT_PROSPECTIVE_EVALUATION_COMPLETE',inputs=[{'path':'run/run_057/artifacts/prepared_batch.json','role':'frozen four candidates','sha256':sha(R/'run/run_057/artifacts/prepared_batch.json')},{'path':'run/run_058/artifacts/private/queue_manifest.json','role':'phase1 queue identities','sha256':sha(R/'run/run_058/artifacts/private/queue_manifest.json')}],outputs=[{'path':rel(p),'role':'actual prospective analysis evidence','sha256':sha(p)} for p in important],validation=[{'check':'actual execution','status':'PASS','evidence':rel(P/'execution_audit.json'),'scope':'four single attempts; no new starts'},{'check':'real ODB session and MAIN review','status':'PASS','evidence':rel(P/'MAIN_real_ODB_receipt_verification.json'),'scope':'36 receipts and four completed true ODB tasks'},{'check':'frozen metrics independent verification','status':'PASS','evidence':rel(P/'independent_metric_verification.json'),'scope':'five Gram/SVD checks and raw frozen predictions'},{'check':'local identifiability','status':'LIMITED','evidence':rel(P/'study_A_local_secants.json'),'scope':'finite amplitude same-base/control; no error covariance or h/time convergence'},{'check':'prospective predictions','status':'PARTIAL','evidence':rel(P/'study_B_frozen_parameter_recovery.json'),'scope':'fullcurve improves but none meets all frozen halfstep goals'}],errors=[],classifications={k:decision[k] for k in ['EXECUTION','NUMERICAL_QUALITY','LOCAL_IDENTIFIABILITY','PROSPECTIVE_PARAMETER_PREDICTION','REAL_MATERIAL_VALIDATION']},new_FE=0,new_queue=0,new_INP=0,consumed_prior_authorized_attempts=4,remaining_authorized_attempts=0,agenthub_science_task_id=tid,predictor_changed=False,tensile_content_read=False)
 temp=RUN/'run.json.tmp';temp.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');read(temp);temp.replace(RUN/'run.json')
 index=R/'run/README.md';old=index.read_bytes();assert b'run_059' not in old;extra='\n\n## 新分析 Run — run_059（run_058 Phase2）\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_059 | 真实四ODB、MAIN复核、冻结A/B前瞻识别 | WARNING / LIMITED / PARTIAL | [summary](run_059/summary.md) |\n\n4/4单次完成且探索性可评分；全曲线预测优于常数但未通过完整半步目标，当前新FE预算0，完成后停止。\n';index.write_bytes(old+extra.encode())
 status=R/'status/PROJECT_STATUS.md';old=status.read_bytes();prefix='# SMALL-PUNCH 项目状态\r\n'.encode();assert old.startswith(prefix)
 note='\r\n## 当前状态 — run_059（2026-10-27，Asia/Shanghai；run_058 Phase2）\r\n\r\n**WARNING / REAL_FOUR_POINT_PROSPECTIVE_EVALUATION_COMPLETE。** 四项真实单次DC+Full完成，真实ODB会话领取提取，MAIN独立复核4/4探索性可评分。局部识别LIMITED；完整曲线冻结预测优于常数且方向4/4，但无主模型满足所有半步标准，前瞻预测PARTIAL。详见[run_059](../run/run_059/summary.md)。4次授权已消耗，新FE/入队/重试/训练/拉伸读取/Git提交0，完成后停止。I06与历史冻结/正式NOT_EVALUABLE均保持。\r\n';status.write_bytes(prefix+note.encode()+old[len(prefix):])
 save(RUN/'checkpoints/completed.json',{'at':now(),'status':'WARNING','report_sha256':sha(P/'scientific_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'science_task_id':tid,'classifications':j['classifications'],'no_new_execution':True,'stopped':True})
 print(json.dumps({'status':'WARNING','classifications':j['classifications'],'report_sha256':sha(P/'scientific_report.md'),'evidence_sha256':sha(P/'evidence_manifest.json'),'Hub_task':tid,'registered_artifacts':len(registered),'actual_consumed_attempts':4,'new_FE':0}))

if __name__=='__main__':main()
