"""Close existing-results Phase2, register evidence, preserve all prior Runs."""
from common62 import *
from agenthub_sp_invopt.hub import Hub
import numpy as np

def main():
 ids=read(P/'task_ids.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=ids['identity'];tid=ids['science_task_id']
 odb=hub.task(ids['odb_task_id']);assert odb['execution_state']=='COMPLETED' and odb['lease_agent']=='ODB:ODB-real-run062'
 folder=P/'odb/I06_REFINED';receipts=read(folder/'handoff_receipts.json');manifest=read(folder/'manifest.json');verified=[]
 for f in receipts['registered']:
  assert sha(R/f['path'])==f['sha256'],f['path'];verified.append(f['path'])
 for f in manifest['files']:assert sha(R/f['path'])==f['sha256'],f['path']
 assert hub.verify_chain();save(P/'MAIN_ODB_handoff_verification.json',{'at':now(),'status':'PASS','task_id':ids['odb_task_id'],'actual_ODB_agent':odb['lease_agent'],'actual_ODB_session':odb['lease_session'],'generation':odb['generation'],'registered_artifacts_verified':len(verified),'manifest_entries_verified':len(manifest['files']),'handoff_receipt_sha256':sha(folder/'hub_completion_receipt.json'),'audit_chain_verified':True,'no_simulated_ODB_worker':True})
 m=read(P/'refinement_metrics.json');checks=read(P/'MAIN_independent_data_review.json');num=read(P/'MAIN_independent_raw_numerical_audit.json');fields=read(P/'PEEQ_stage_field_comparison.json');contact=read(P/'MAIN_contact_mechanism_review.json');execution=read(P/'execution_audit.json');start=read(RUN/'checkpoints/start.json');protected=read(P/'protected_sources_before.json')
 assert checks['original']['SCIENTIFIC_SCOREABILITY']==checks['refined']['SCIENTIFIC_SCOREABILITY']=='SCOREABLE'
 assert not checks['original']['force_recoil'] and not checks['refined']['force_recoil']
 # Independently check the exact frozen bin and ratio, not a post-hoc PASS threshold.
 assert .1<m['R_RMSE']<=.25 and abs(m['force_difference_RMSE_N']/3.092632613282926-m['R_RMSE'])<1e-15
 for path,digest in protected.items():assert sha(R/path)==digest,path
 for path,digest in execution['protected_after'].items():assert sha(R/path)==digest,'Unexpected project mutation during read-only phase'
 assert git('rev-parse','HEAD')==start['git']['head'] and git('diff','--cached','--name-status')==start['git']['staged']
 oldgit=read(R/'run/run_061/checkpoints/start.json');assert sha(R/'.gitignore')==oldgit['gitignore_sha256']
 for p in oldgit['local_CAE']:assert sha(R/p['path'])==p['sha256']
 status={'EXECUTION':'PASS','SOFTWARE_STATUS':'COMPLETED_WITH_WARNINGS','NUMERICAL_QUALITY':'WARNING','SCIENTIFIC_SCOREABILITY':'SCOREABLE_WITH_LIMITATIONS','I06_POINT_REFINEMENT':'SUPPORTED','I06_POINT_REFINEMENT_scope':'observed adjacent increment response closeness at this center, not formal/asymptotic convergence PASS','WEAK_DIRECTION_RESOLUTION':'LIMITED','LOCAL_IDENTIFIABILITY':'LIMITED','REAL_MATERIAL_VALIDATION':'NOT_EVALUABLE','R_risk_band':m['risk_band'],'no_retroactive_change_to_run059':True}
 save(P/'scientific_status.json',status)
 ledger={'at':now(),'parent_authorization_run':'run_061','authorized_total':1,'queued_identity_count':1,'started_attempts':1,'consumed_attempts':1,'successful_datacheck_count':1,'successful_full_count':1,'automatic_or_unexpected_retry_count':0,'remaining_unstarted_authorized_attempts':0,'queue_id':'q_392e020abc59422c9cb6a93f35b235d2','job':'SPIO_R060_I06_M00125','inp_sha256':execution['record']['inp_sha256'],'odb_sha256':execution['record']['files']['odb']['sha256'],'software_status':'COMPLETED_WITH_WARNINGS','scientific_status':status,'new_FE_authorized_in_this_analysis':0,'Agent_started_solver_or_datacheck':False,'no_new_queue':True}
 save(P/'authorization_ledger_consumed.json',ledger)
 oe=read(P/'original_energy_summary.json')['outputs'];ne=read(P/'refined_energy_summary.json')['outputs'];pd0=oe['ALLPD']['last'][1];pd1=ne['ALLPD']['last'][1]
 seg='\n'.join(f"|{x['lower_mm']:.1f}–{x['upper_mm']:.1f}|{x['points']}|{x['RMSE_N']:.9f}|{x['max_abs_N']:.9f}|{100*x['sum_squares_fraction']:.2f}%|" for x in m['segments'])
 field=fields['stages'][-1];sigchange=abs(m['delta_loss'])/m['original_loss'];oldrmse=1428.9*np.sqrt(m['original_loss']);newrmse=1428.9*np.sqrt(m['refined_loss'])
 report=f'''# run_062 — run_061 Phase2：I06 Numerical Resolution Qualification

完成时间：{now()}，Asia/Shanghai。项目Run协议要求每项独立科研产出新编号，因此保留run_061授权/入队记录，将本次Phase2登记为run_062。全部比较来自真实已有求解和真实ODB会话，无新增FE。

## 判定

|维度|结论|
|---|---|
|EXECUTION|PASS|
|SOFTWARE_STATUS|COMPLETED_WITH_WARNINGS|
|NUMERICAL_QUALITY|WARNING|
|SCIENTIFIC_SCOREABILITY|SCOREABLE_WITH_LIMITATIONS|
|I06_POINT_REFINEMENT|SUPPORTED：仅此中心、此窗口、两个相邻最大增量之间的观测稳定性|
|WEAK_DIRECTION_RESOLUTION|LIMITED|
|LOCAL_IDENTIFIABILITY|LIMITED，run_059原结论不变|
|REAL_MATERIAL_VALIDATION|NOT_EVALUABLE|

SUPPORTED不是正式时间步收敛PASS。run060没有预设经过验证的收敛合格阈值，本报告不移用别的Run阈值或事后造标准。R风险提示是NONNEGLIGIBLE，不能误报为≤0.1的小变化档。

## 真实执行与文件身份

Job SPIO_R060_I06_M00125；queue q_392e020abc59422c9cb6a93f35b235d2；Project b87d2cd6-8519-4ac3-bae6-7eb989fb2dae。INP SHA f944338d77fa7798d3546dd51075f149f886a4fd015b37fba28c58878311b906。新ODB SHA {execution['record']['files']['odb']['sha256']}。源清单、INP、原ODB及所有受保护证据完整校验。原INP与新INP仅max .0025→.00125及两处事前批准身份注释不同，逆转后逐字节一致；参数236.49902622197678MPa/.0968、34行材料表、E/nu、几何/网格/BC/接触/加载/输出不变。

公开API Queue/History/detail/status/outputs与原LOG/STA/MSG/DAT交叉核验：只有一次attempt_no=1，DC一次22秒、返回0，Full一次288秒、返回0，总310秒；14CPU/0GPU。STA成功终态和ODB JOB_STATUS_COMPLETED_SUCCESSFULLY一致。无重试、额外本批Job、中断恢复、活动Runner/Solver/目标锁。当前分析不改变Queue/Settings/project.db哈希。原I06 DC33秒/Full261秒/总294秒，细化总耗时约增加5.44%，不能把不同CPU墙钟等同于算法成本比较。

MAIN经AgentHub完成既有执行审计，真实SP-InvOpt ODB会话以ODB:ODB-real-run062、session {odb['lease_session']}领取既有任务{ids['odb_task_id']}。Abaqus2024 Python readOnly=True打开新旧ODB，源文件前后SHA保持；新814帧/原440帧。正式Hub artifact收据{len(verified)}项和静态清单{len(manifest['files'])}项均由MAIN重新验hash，不冒称本地模拟worker是独立会话。原输出和历史提取不改，补充场只写本Run私有目录。

MAIN独立逐点核对全部RP History/CSV/Field：Node ASM_SPT.1、SET_PUNCH_RP、Step_Punch_Displacement；u=-U2、F=-RF2，m/N，无2π附加因子。原生位移严格递增、从0覆盖1.200000057mm，时间到1；Field/History U2/RF2最大差均0，材料完整表摘要与INP相符，2376 IP/帧，最大PEEQ<.9。

## 冻结F–D与Loss比较

严格复用run060 comparison_contract及其预先测试实现，原241个实验位移0–1.2mm、run017-exploratory-fd-v1、Fref1428.9N、等权、原生折线线性插值。不移零、不平滑、删点、外推或改窗。MAIN用独立NumPy算术复核Python fsum比较器和两项Loss公式，原Loss与冻结来源完整精度吻合。

|指标|实际结果|
|---|---:|
|F–D差RMSE|{m['force_difference_RMSE_N']:.15g} N|
|最大绝对载荷差|{m['max_absolute_force_difference_N']:.15g} N，0.98mm|
|最大正则相对差|{m['max_regularized_relative_difference']*100:.9f}%（0.015mm）|
|原I06 Loss|{m['original_loss']:.17g}|
|细化I06 Loss|{m['refined_loss']:.17g}|
|有符号ΔLoss|{m['delta_loss']:.15g}|
|绝对ΔLoss|{m['absolute_delta_loss']:.15g}|
|原/新对实验RMSE|{oldrmse:.9f} / {newrmse:.9f} N|

相对差分母严格max(abs(F_original),71.445N)。细化Loss变化仅为原Loss的{sigchange*100:.6f}%，下降不代表物理真实性改善，也不能以其排序判断数值精度。实验失配远大于本中心相邻细化差，但本轮不能唯一归因于本构、夹具、测量或参数误差。

|位移/mm|点数|F–D差RMSE/N|最大差/N|差平方和贡献|
|---|---:|---:|---:|---:|
{seg}

分段采用左闭右开、最后含1.2mm，互不重复共241点。末段差平方和36.81%，早期0–.3mm也占32.95%，不是只在末段有差。补充窗口0.97–.99mm贡献20.10%，1.10–1.16mm贡献16.49%（后者RMSE .756499N、最大2.036635N于1.125mm）；不将这些诊断窗口替代冻结全窗口。

## 接触与接受增量

最大差.98mm位于node24压力建立/载荷快速增加区：原曲线node24从.974854mm的0到.977854mm的103.403MPa，再到.980854mm的303.581MPa；细化曲线.974681mm为0，.976181mm为13.557MPa，.979181mm为254.236MPa。原生步与插值括点密度不同，压力建立采样区间重叠，不能把首个正压力采样位置差直接称为精确接触起始位移偏差。已知的是差异与接触演化、接受路径及采样/插值相关；现有数据不足以唯一分离三者或确定接触是唯一原因。

1.10–1.16mm有原20/新40个真实保存帧。node23首个正压力样本分别约1.124854mm/44.759MPa和1.124681mm/56.396MPa；末段继续增压。此区不是本次最大241点差的位置。node22未在该窗出现正压力；node230没有接触场值；node23/24的COPEN哨兵保持缺失，不被当作实际间隙。正CPRESS仅为压力代理，不宣称已经证明完整接触状态因果关系。

MAIN独立匹配每个接受STA attempt到其专属MSG块：原439/新813个接受增量均有TIME INCREMENT COMPLETED与明确力平衡收敛、零残差或small-residual/estimated-correction接受证据，无未确认项。原18次拒绝/18cutback、细化6次拒绝/6cutback；总平衡迭代706→1084。原拒绝试算警告含大应变9、负特征值3、塑性积分未尝试2、畸变2；新仅拒绝试算大应变2，无负特征值或畸变标题。两者接受试算均仅ZERO_MOMENT1条。DAT均有解析刚体主面下path tracking回退到state tracking的警告，这不是本轮主动修改接触算法。两条原生F–D均无负载荷步。保留WARNING，不把拒绝试算当已接受物理状态，也不把正常软件结束等同于全局数值资格PASS。

## PEEQ、空间与能量

全部保存帧/IP最大PEEQ：{m['original_max_PEEQ']:.15g}→{m['refined_max_PEEQ']:.15g}，差{m['delta_global_max_PEEQ']:.12g}，均低于材料表上界.9且未触及.85复核提示。

按各自原生位移插值每保存帧全局最大PEEQ的标量历史，在.3/.6/.9/1.2mm的差依次约.000105188/.000457766/.000421381/.000339568，保留左右括帧；这是标量最大值诊断，不是同一积分点场插值。各自最近真实帧与目标偏差均<3微米，仍明确中间三阶段不在精确相同位移。2376 IP按同网格/同参考轴对称权重配对，近阶段加权场差RMSE约.000125/.000124/.000125；只能描述近阶段差异。终态位移完全相同，PEEQ参考体积加权场差RMSE={field['PEEQ_reference_volume_weighted_difference_RMSE']:.12g}，最大单IP差={field['PEEQ_max_abs_IP_difference']:.12g}，位于element378/IP2、r_ref约.120826mm/z_ref .488260mm，PEEQ .364464→.380755。这说明全局最大值接近不能替代局部场差审核；该单IP参考体积约占全体0.000406%，不等于RF2贡献。

终态ALLPD {pd0:.12g}→{pd1:.12g} J，差{pd1-pd0:.12g} J（{100*(pd1-pd0)/pd0:.6f}%）。ALLSD/ALLAE均0，外功/内能等历史保存于原始提取；塑性功/参考体积占比不能当Punch载荷贡献。

## 核心R与可识别性

完整分母=3.092632613282926N RMS，来源SHA和字段均与run059冻结记录一致。R={m['R_RMSE']:.17g}，中心细化差约为弱方向半步信号的13.99%，弱信号约为中心差的{1/m['R_RMSE']:.6f}倍。属于0.1<R≤0.25预注册NONNEGLIGIBLE；既非≤.1档，也未达>.5高风险档。最大差/弱RMS={m['max_difference_over_weak_RMS_descriptive']:.9f}是不同统计量的描述比，不套用主R分档。

额外明确标记的探索性投影：把此中心差向量投向旧run059 full241弱左奇异向量，RMS分量约.160084N、相对弱信号5.1763%。这不是重建Jacobian，不是参数偏差、置信区间或严格误差上界，不能替代主R和扰动点误差审核。

本中心的相邻设置总体接近，增加点级稳定性信心；观测弱信号比中心差大，存在分辨空间，但14%并非可一概忽略。只检查一个中心，不能排除四个扰动点的误差、接触非线性或步长依赖影响弱方向；WEAK_DIRECTION_RESOLUTION保持LIMITED。

run059两载荷/五特征/全曲线条件数14.884724/16.619303/13.347458，列余弦.989884/.992146/.987621保持。高相关是原同契约有限割线数据事实，本中心检查不消除它。完整曲线条件稍好且冻结前瞻预测优于常数，然而半步分辨要求未全满足；这些历史评价不重算、不升级。当前主要证据支持参数方向耦合、稀疏训练支持与特征压缩共同限制逆模型；数值分辨风险较之前更受约束，仍未被全部排除。无独立噪声协方差，不生成Fisher置信区间。真实材料验证依旧NOT_EVALUABLE。

## 科研决策和最小预算

不建议继续机械细化I06中心，也不恢复BO/DE或为了降低Loss增加参数点。完整241点F–D继续作为主反演基线；两载荷/五特征保留作可解释诊断或辅助输入，不宜现阶段宣传为已具稳定独立反演能力的方法。优先研究sigma_y/n弱方向可识别性及模型信息限制，保留已有材料形式误差问题，不能由本轮判断其唯一机制。

当前无需立即新增FE：建议先使用已冻结响应/残差作离线可识别性和多信息设计。如果下一阶段需要把旧局部Jacobian作为定量识别依据，最小完整补证方案是单独申请P01–P04各一次相邻max .0025→.00125细化，共4个新Job，复用本次已细化中心，不增加第五点。这样才能从四个臂的实际变化检查弱方向差分误差；只细化一对可作筛查，不能补齐完整两列的数值资格。预算建议不是授权，当前不生成输入、不入队、不执行；若有失败/不完整/超表或未解释接受态异常，停止该研究，不重试、不自动再减半。

本次授权1次已实际消耗1次，余额0；新分析授权FE0。后续任何计算必须另行批准。run046/047/048及run055–061全部历史保持，未读取拉伸或封存分析、未改预测器、未重训Ridge/重算旧Jacobian或优化。Git HEAD/.gitignore/既有两CAE索引删除和本地模型完整。AgentHub仅正式接口，无SQLite直接编辑。完成后停止。
'''
 write(P/'scientific_report.md',report)
 save(P/'preservation_final.json',{'at':now(),'protected_source_count':len(protected),'all_hashes_unchanged':True,'git_head':git('rev-parse','HEAD'),'staged':git('diff','--cached','--name-status'),'gitignore_sha256':sha(R/'.gitignore'),'local_CAE_intact':True,'AbqProject_protected_hashes_unchanged':True,'no_new_solver_datacheck_queue_retry':True})
 # Verify static artifacts once more and record public references without exposing curves.
 files=[p for p in sorted(A.rglob('*')) if p.is_file() and p.name not in ['evidence_manifest.json','agenthub_completion_receipt.json','task_ids.json'] and 'lease' not in p.name and p.name!='identity.json' and '__pycache__' not in p.parts]
 save(P/'evidence_manifest.json',{'version':'run062-Phase2-static-evidence-v1','at':now(),'files':[{'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],'excludes':'self, MAIN session/lease files, ODB lease/identity files, later Hub receipt, live run/index/status metadata'})
 lease=hub.claim(tid,actor,'run062-MAIN-scientific-review-v1');save(P/'science_lease.json',lease)
 registered=[]
 for path in [P/'execution_audit.json',P/'MAIN_ODB_handoff_verification.json',P/'MAIN_independent_data_review.json',P/'MAIN_independent_raw_numerical_audit.json',P/'refinement_metrics.json',P/'MAIN_contact_mechanism_review.json',P/'PEEQ_stage_field_comparison.json',P/'authorization_ledger_consumed.json',P/'scientific_status.json',P/'scientific_report.md',P/'evidence_manifest.json']:
  r=hub.artifact(tid,actor['agent_id'],path,{'run':'run_062','parent_execution':'run_061','scope':'real existing ODB extraction and independent MAIN frozen comparison'},version='run062-v1');registered.append({'path':rel(path),'sha256':r['sha256']})
 body={'output_run':'run_062','parent_execution_run':'run_061','queue_id':ledger['queue_id'],'status':status,'RMSE_N':m['force_difference_RMSE_N'],'max_difference_N':m['max_absolute_force_difference_N'],'R':m['R_RMSE'],'risk_band':m['risk_band'],'authorized_consumed':1,'new_FE':0,'report_path':rel(P/'scientific_report.md'),'report_sha256':sha(P/'scientific_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'decision':'center adjacent-refinement supported; weak/local identification LIMITED; no immediate additional FE, optional separately authorized four-arm precision qualification'}
 msg=hub.message(tid,actor['agent_id'],'MAIN',body,'run062-MAIN-scientific-handoff-v1');hub.finish(lease,body,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain()
 save(P/'agenthub_completion_receipt.json',{'at':now(),'main_science_task_id':tid,'audit_task_id':ids['execution_audit_task_id'],'ODB_task_id':ids['odb_task_id'],'registered_artifacts':registered,'message_id':msg['message_id'],'task':hub.task(tid),'audit_chain_verified':True,'message_is_not_automatic_cross_session_wakeup':True})
 important=[P/'scientific_report.md',P/'refinement_metrics.json',P/'execution_audit.json',P/'scientific_status.json',P/'evidence_manifest.json',P/'agenthub_completion_receipt.json',P/'authorization_ledger_consumed.json']
 save(A/'manifest.json',{'version':'run062-artifacts-v1','files':[{'path':rel(p),'role':'Phase2 evidence','private':True,'sha256':sha(p)} for p in important]})
 write(RUN/'summary.md',f'''# run_062 — run_061 Phase2：I06数值分辨率

**WARNING / I06_REFINEMENT_ANALYSIS_COMPLETE。** 唯一真实Job单次DC/Full成功，COMPLETED_WITH_WARNINGS，22+288=310秒；真实ODB Agent提取，MAIN独立复核可评分。新增FE/入队/重试0，原授权1次已消耗，历史Run不变。

细化F–D差RMSE **{m['force_difference_RMSE_N']:.9f}N**，最大差 **{m['max_absolute_force_difference_N']:.9f}N于0.98mm**；Loss **{m['original_loss']:.12f}→{m['refined_loss']:.12f}**。R=**{m['R_RMSE']:.12f}**，处于预注册0.1–0.25不可忽略提示区间。原/新cutback18→6，最大PEEQ .702750385→.703089952，表覆盖满足。

EXECUTION PASS；NUMERICAL_QUALITY WARNING；I06_POINT_REFINEMENT SUPPORTED（点级相邻设置范围）；WEAK_DIRECTION_RESOLUTION LIMITED；LOCAL_IDENTIFIABILITY LIMITED；REAL_MATERIAL_VALIDATION NOT_EVALUABLE。不能把中心差当四臂数值误差上界或已收敛Jacobian，run059前瞻评价不变。

见[科研报告](artifacts/private/scientific_report.md)、[结构化指标](artifacts/private/refinement_metrics.json)、[证据清单](artifacts/private/evidence_manifest.json)、[AgentHub收据](artifacts/private/agenthub_completion_receipt.json)。当前建议先离线研究耦合/信息设计，不再机械细化中心；若必须完整资格核验旧Jacobian，需另行批准四个扰动臂各一次细化共4Job，本轮不准备或执行。完成后停止。
''')
 j=read(RUN/'run.json');save(RUN/'checkpoints/run_before_close.json',j)
 j.update(status='WARNING',end_time=now(),outcome='I06_REFINEMENT_ANALYSIS_COMPLETE',inputs=[{'path':'run/run_060/artifacts/prepared_batch.json','role':'frozen input','sha256':sha(R/'run/run_060/artifacts/prepared_batch.json')},{'path':'run/run_060/artifacts/comparison_contract.json','role':'frozen comparator contract','sha256':sha(R/'run/run_060/artifacts/comparison_contract.json')},{'path':'run/run_061/artifacts/private/queue_manifest.json','role':'original authorized queue evidence','sha256':sha(R/'run/run_061/artifacts/private/queue_manifest.json')}],outputs=[{'path':rel(p),'role':'post-run analysis evidence','sha256':sha(p)} for p in important],validation=[{'check':'real single DC/Full and identity','status':'PASS','evidence':rel(P/'execution_audit.json'),'scope':'1attempt, no retry, complete terminal output'},{'check':'real ODB handoff and MAIN data review','status':'PASS','evidence':rel(P/'MAIN_ODB_handoff_verification.json'),'scope':'real ODB session task receipt and independent raw checks'},{'check':'numerical process','status':'WARNING','evidence':rel(P/'MAIN_independent_raw_numerical_audit.json'),'scope':'no unresolved severe accepted warnings; retained ZERO_MOMENT/DAT fallback'},{'check':'weak-direction risk','status':'WARNING','evidence':rel(P/'refinement_metrics.json'),'scope':'R .139906 in preregistered .1-.25 exploratory bin, not convergence PASS'}],scientific_status=status,actual_authorization_consumed=1,new_FE=0,new_queue=0,automatic_retries=0,agent_started_solver_datacheck=False,agenthub_science_task=tid,queue_id=ledger['queue_id'],tensile_access=False)
 temp=RUN/'run.json.tmp';write(temp,json.dumps(j,ensure_ascii=False,indent=2)+'\n');read(temp);temp.replace(RUN/'run.json')
 index=R/'run/README.md';old=index.read_bytes();assert b'run_062' not in old
 index.write_bytes(old+('\n\n## 新结果 Run — run_062（run_061 Phase2）\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_062 | 真实I06细化ODB、独立数值复核、冻结比较和弱方向R | WARNING / 点级SUPPORTED / 识别LIMITED | [summary](run_062/summary.md) |\n\n单次完成、RMSE .432677914N、R .139906018（.1–.25提示），不升级run059。当前分析新增FE/入队/重试0，完成后停止。\n').encode())
 statusfile=R/'status/PROJECT_STATUS.md';old=statusfile.read_bytes();first=old.find(b'\n')+1
 note=f'\n## 当前状态 — run_062（{now()[:10]}，Asia/Shanghai；run_061 Phase2）\n\n**WARNING / I06_REFINEMENT_ANALYSIS_COMPLETE。** 唯一I06细化单次DC/Full真实完成，真实ODB Agent与MAIN独立复核可评分；FD差RMSE .432677914N、最大2.757653824N于.98mm，R .139906018落入.1–.25提示。点级相邻稳定性SUPPORTED，弱方向/局部识别仍LIMITED，正式材料验证NOT_EVALUABLE。详见[run_062](../run/run_062/summary.md)。原授权1次已消耗，本轮新FE/入队/重试/训练0，历史冻结保持，完成后停止。\n'
 statusfile.write_bytes(old[:first]+note.encode()+old[first:])
 save(RUN/'checkpoints/completed.json',{'at':now(),'scientific_status':status,'report_sha256':sha(P/'scientific_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'Hub_task':tid,'no_further_work_authorized':True})
 print(json.dumps({'status':status,'report_path':rel(P/'scientific_report.md'),'report_sha256':sha(P/'scientific_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'AgentHub':'COMPLETED_RECORDED_CHAIN_VALID','future_FE_prepared_or_run':0}))
if __name__=='__main__':main()
