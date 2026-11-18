"""Finalize one-input preparation evidence and stop without enqueue or execution."""
from prepare import *
import shutil

def main():
 point=read(P/'candidate_identity.json');cc=read(A/'comparison_contract.json');baseline=read(P/'I06_baseline_audit.json');pre=read(P/'public_preflight_dry_run.json');ss=read(P/'hub_session.json');start=read(RUN/'checkpoints/start.json')
 tests=subprocess.run([sys.executable,'-B',str(A/'test_resolution.py')],cwd=R,text=True,capture_output=True)
 save(P/'offline_tests.json',{'at':now(),'interpreter':sys.executable,'returncode':tests.returncode,'stdout':tests.stdout,'stderr':tests.stderr,'tests':8,'scope':'synthetic comparison/risk/stage arithmetic plus real input identity and no-write checks'})
 assert tests.returncode==0
 sources=read(P/'source_manifest.json')['sources']
 for item in sources:assert sha(R/item['path'])==item['sha256'],item['path']
 assert sha(R/point['inp_path'])==point['inp_sha256'] and not any((R/point['working_dir']).iterdir())
 assert point['comparison_contract_sha256']==sha(A/'comparison_contract.json')
 for p,h in pre['protected_before'].items():assert sha(R/p)==h
 assert git('rev-parse','HEAD')==start['git']['head'] and git('diff','--cached','--name-status')==start['git']['staged']
 old=read(R/'run/run_057/checkpoints/start.json');assert sha(R/'.gitignore')==old['gitignore_sha256']
 for item in old['local_CAE']:assert sha(R/item['path'])==item['sha256']
 weak=cc['weak_reference']['value_RMS_N']
 protocol=f'''# run060 — I06相邻时间增量比较协议

冻结时间：{cc['frozen_at']}。机器契约comparison_contract.json，SHA-256 {sha(A/'comparison_contract.json')}。新结果尚不存在，当前只批准单候选准备，求解与入队授权均0。

## 唯一基准与候选

基准SPIO_R030_I06_L：sigma_y=236.49902622197678MPa，n=.0968，原INP SHA {point['source_inp_sha256']}、ODB SHA {point['source_odb_sha256']}。材料34行、p0–.9、E210GPa/nu.3、真总应变解释候选Hollomon全部保持；原440点FD、439接受增量、18cutback、maxPEEQ .7027503848075867，ZERO_MOMENT、DAT tracking及历史进程证明缺口保留。I06仍QUALIFIED_WITH_LIMITATIONS，未升级为独立时间步收敛基准。

候选{point['job_name']}，INP SHA {point['inp_sha256']}。唯一数值变化max increment .0025→.00125；initial .001、time1、min1e-12、inc999999，所有材料/几何/网格/接触/摩擦/BC/压入/输出保持。两处Job/Run身份注释更新；回退允许的3处变更后可逐字节恢复原源文件。输入、工作目录、预期ODB绝对路径见prepared_batch.json，不能猜测或更换位置。

## 比较输入及固定规则

未来仅在独立授权的一次DC成功后Full真实结束、文件身份与实际RP/符号/单位核实并且无活动占用后执行；真实ODB Agent只读提取，MAIN独立审核。原与新曲线统一使用run017-exploratory-fd-v1的精确实验位移0–1.2mm/241点，等权、Fref1428.9N、原生折线线性插值，无外推/裁剪/平滑/删点/移零或柔度再校正。Loss目标、配置与源码SHA绑定机器契约。不完整或无效时返回null，不以部分曲线比较。

固定报告F-D差RMSE、最大绝对差及位移、最大正则相对差及位移；相对分母为max(abs(F_original),71.445N)。使用相同参考曲线方向；不把相对差换成新曲线分母。分别给原/新冻结Loss、有符号delta与绝对delta、原/新最大保存帧PEEQ和差、cutback/收敛/警告、接触事件及实际成本。

## 弱方向比值与风险提示

参考run059 full241有限幅Jacobian弱方向半步响应的完整精度{weak!r}N RMS，其文件与字段SHA已绑定。定义R=RMSE(F_new−F_original)/{weak!r}N。显示3.09N仅为舍入，不作为计算分母。

|R范围|对应本次FD差RMSE/N|探索性提示|
|---|---|---|
|0≤R≤.1|≤{weak*.1:.12f}|观测中心变化较小|
|.1<R≤.25|>{weak*.1:.12f}且≤{weak*.25:.12f}|不可忽略|
|.25<R≤.5|>{weak*.25:.12f}且≤{weak*.5:.12f}|弱方向解释风险明显|
|R>.5|>{weak*.5:.12f}|弱方向解释高风险|

这些是求解前预注册的工程提示，不是经过验证的数值收敛、观察噪声或材料验收标准。低R不能自动产生全局收敛PASS。另报最大绝对差/弱方向RMS，仅作不同统计量的描述性量级比，不套用R_RMSE的分区。单次变化不是严格误差上界，不使用D01历史细化差当I06上界。

## PEEQ共同阶段与保存帧差异

共同压入阶段预设.3/.6/.9/1.2mm。每条历史按自身实际RP位移对每保存帧全局最大PEEQ做线性标量插值，保留左右括帧的索引/位移/PEEQ，不外推；这不是重建连续场，也不是同一材料积分点的PEEQ。另选距离目标位移最近的实际保存帧，距离相同选较早帧，记录真实位移偏差、frame/increment/time、最大值和位置。两模型不能按相同帧编号或强行认为最近帧等于精确相同阶段。

最近帧离目标>3微米则标阶段采样不充分/待复核；3微米来自原max.0025×1.2mm步长的位移跨度，只是匹配复核线，不是PEEQ误差阈值。字段不足则该项NOT_EVALUABLE，不制造数值。最大PEEQ取全部保存帧、全部实际积分点，不取百分位或只看终态；核验表末.9，PEEQ>=.85必须复核。

## 接触、接受与拒绝试算

保留1.10–1.16mm所有原始接受帧和节点23及由真实拓扑确定邻接节点的CPRESS/COPEN。另检查全窗局部峰值以及既有.68–.70、.85–.88、.97–.99mm接触演化相关区间，不能据此删点或改窗口。abs(COPEN)>=1e30或非有限值按缺失/sentinel记录，不能解释为真实间隙；CPRESS>0只表示正压力代理。没有相应字段就标NOT_EVALUABLE。

所有警告与最终平衡证据按实际STA increment/attempt绑定MSG本试算块；区分拒绝试算、最终接受及small-residual/estimated-correction接受。接受中的局部载荷上升/压力变化可有物理接触关联，但不自动确定唯一机制；不得把原始步载荷差直接当数值误差。

## 结论边界与停止

身份/数值契约不符、DC/Full失败、输出不全、窗口不覆盖、PEEQ超表或接受态严重异常未解释时停止定量准入，保留证据/null，不修补、重试或追加。反力回退与接触异常保留精确幅度和上下文，不能因为微小负步就宣称材料失败。无可靠噪声/模型协方差不形成Fisher置信区间。

本次只检验I06中心在两个相邻最大增量设置下的响应变化；不证明P01–P04同精度，不重算/修改run059 Jacobian或预测结果，不验证全参数域、网格、夹具或真实材料。未来任何新精度数据应单独标识，不能静默混入旧反演训练集。

run055交叉验证、run056设计、run057预测器、run058队列历史、run059 A/B评价均保持；不重训Ridge、不改变特征、扰动或材料。正式真实材料验证保持NOT_EVALUABLE，run046冻结和run047/048历史不变；保留此前信息暴露事实，当前不读拉伸或封存分析。

## 未来授权

仅建议单独申请本唯一冻结INP/完整SHA/Job/工作目录、正式Project b87d2cd6-8519-4ac3-bae6-7eb989fb2dae、14CPU0GPU、一次DC成功后一次Full、零自动重试，Solver由用户GUI启动。本轮不登记执行额度、不实际入队、不启动任何Abaqus进程。完成准备后停止。
'''
 write(P/'comparison_protocol.md',protocol)
 report=f'''# run060 — I06 Numerical Resolution Qualification Preparation

完成：{now()}，Asia/Shanghai。**WARNING / PREPARED_TO_REQUEST_ONE_I06_RESOLUTION_RUN**。

本轮已实际完成唯一候选生成、逐字节允许差异核验、8项轻量测试、正式AbqJobPilot公开Preflight/Dry-run和AgentHub登记。当前新FE授权0、实际入队0、Solver/Datacheck启动0，无参数识别点、重训或优化。

## 基准事实

I06完整参数sigma_y=236.49902622197678MPa,n=.0968。源INP {point['source_inp']}；完整SHA {point['source_inp_sha256']}。源ODB {point['source_odb']}；完整SHA {point['source_odb_sha256']}。所有原始输出/既有提取哈希核验，DC和Full成功的历史证据、440点完整FD、Node ASM_SPT.1、u=-U2/F=-RF2、Field/History既有一致性核对；最大PEEQ .7027503848075867<.9材料表末。439接受增量/18cutback，接受trial一条ZERO_MOMENT，被拒试算的大应变、负特征值、畸变标题独立保留。DAT tracking与旧进程来源缺口不抹去，资格继续QUALIFIED_WITH_LIMITATIONS，不宣称新ODB提取或独立时间步收敛。

## 唯一输入

Job：{point['job_name']}。

INP：{point['inp_absolute_path']}。

SHA-256：{point['inp_sha256']}。

Working Directory：{point['working_dir_absolute']}。

数值契约run060-I06-adjacent-increment-m00125-v1，initial .001、max .00125、min1e-12、time1、inc999999。相对源仅最大增量.0025→.00125与2处身份注释变化。逆转这3处变更可逐字节恢复源INP；34行塑性表原始字节完全一致，E/nu、几何/网格/接触/摩擦/BC/加载/输出均未变，无相对INCLUDE外部依赖。原模型和历史结果不改。

## 冻结比较

机器协议comparison_contract.json（SHA {sha(A/'comparison_contract.json')}）与comparison_protocol.md在任何新结果前冻结。沿用run017-exploratory-fd-v1的精确241点原实验网格、0–1.2mm、Fref1428.9N、等权/线性/无移零平滑外推；重新计算I06基准Loss={baseline['recomputed_loss']!r}，匹配历史完整精度。比较FD RMSE、最大绝对差与位置、正则相对差（原曲线为分母、71.445N下限）、Loss变化、全保存帧最大PEEQ及共同阶段PEEQ、接受/拒绝警告、cutback/接触与成本。

run059完整弱方向参考={weak!r}N RMS，原矩阵/归一化来源与SHA绑定。R=细化FD差RMSE/该值，0.1/.25/.5对应RMSE约.309263/.773158/1.546316N。只作预设探索风险区间，没有新造正式收敛PASS门槛，也没有沿用其他基点的数值变化当本处上界。

PEEQ在.3/.6/.9/1.2mm按各自原生RP位移定位：明确区分标量max历史插值与最近真实保存帧；保留括帧/偏差/位置。3微米阶段偏差复核线不等于PEEQ精度阈值。原基准各阶段记录已生成；未来字段缺失返回NOT_EVALUABLE。全局max取所有保存帧/IP。

## 工程预检与测试

当前正式AbqJobPilot0.2.2公开接口，Project ID b87d2cd6-8519-4ac3-bae6-7eb989fb2dae；当前Settings=PERSISTED，D:\\ABAQUS2024\\Commands\\abq2024.bat真实存在，14CPU0GPU、Datacheck与Full开启。Runtime CLEAN、Runner owner ABSENT，无范围外可执行任务、同Job/输入/输出目录历史冲突。目标目录空，公开Preflight=PREVIEW_READY、Dry-run=DRY_RUN_READY，无job_id，未入队、未调用Solver或datacheck。Project/Queue/Settings/project.db在预览前后及收尾哈希一致。预览不代表真实Abaqus语法、许可或收敛验证。

8项测试覆盖同曲线零变化、已知偏移/分母/Loss公式、R区间端点、非法单位/目标、失败或不完整曲线拒绝、PEEQ括帧/无外推、输入逐字节可逆性、无队列/求解写入，实际全部通过。MAIN在当前会话完成获准离线文件准备，通过正式Hub任务登记；未冒称另一个CAE会话已经领取。无直接SQLite或Queue JSON编辑。

## 决策

值得单独申请这1项Job以测量本中心相邻增量变化相对约3.09N弱信号的量级。一次中心细化能支持“此参数/模型/窗口/两设置间观测差异”的结论；不能给严格数值误差上界、渐近时间步/网格收敛，不能给四扰动点/整个Jacobian同精度认证或真实SA508验证。大R或未解释异常应先定位，不自动继续减半、追加点或优化。

run059两载荷/五特征方向高度耦合、完整曲线是当前最好的主反演输入但前瞻半步标准未全通过、真实材料验证NOT_EVALUABLE的结论均不改。后续需绑定本唯一SHA、Job、工作目录、Project、14CPU0GPU、单次DC+Full、零重试及用户GUI启动的明确授权；本轮没有执行预算。

Git忽略规则与2项已暂存CAE索引删除保持，两份本地模型hash不变；未重复清理索引，没有commit/push/reset/clean。冻结预测器、run055–059及相关源记录逐项核对保持；不读拉伸或封存分析，不用解盲资料调参。完成后停止。
'''
 write(P/'scientific_report.md',report)
 save(P/'scientific_decision.json',{'at':now(),'status':'WARNING','engineering_preparation':'PASS','I06_baseline':'QUALIFIED_WITH_LIMITATIONS','INP_prepared':1,'numerical_change_only':'max .0025->.00125','material_and_all_other_physics_unchanged':True,'preflight':'PASS','dry_run':'PASS','weak_RMS_reference_N':weak,'risk_boundaries':[.1,.25,.5],'formal_numerical_convergence_thresholds':None,'worth_requesting_one_separate_solve':True,'authorized_new_FE':0,'new_queue':0,'solver_datacheck_started':False,'run059_conclusions_unchanged':True,'REAL_MATERIAL_VALIDATION':'NOT_EVALUABLE','new_hypotheses_not_verified_by_preparation':True})
 save(P/'preservation_final.json',{'at':now(),'source_records_unchanged':len(sources),'current_HEAD':git('rev-parse','HEAD'),'staged':git('diff','--cached','--name-status'),'gitignore_sha256':sha(R/'.gitignore'),'local_CAE':[{'path':item['path'],'sha256':sha(R/item['path'])} for item in old['local_CAE']],'protected_AbqJobPilot_hashes':pre['protected_after'],'output_directory_empty':not any((R/point['working_dir']).iterdir())})
 files=[p for p in sorted(A.rglob('*')) if p.is_file() and p.name not in ['hub_session.json','evidence_manifest.json','agenthub_completion_receipt.json'] and '__pycache__' not in p.parts]
 save(P/'evidence_manifest.json',{'version':'run060-static-evidence-v1','at':now(),'files':[{'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],'excludes':['self','live lease','later receipt','Run/index/status metadata']})
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);hub.heartbeat(ss['lease']);records=[]
 for p in files+[P/'evidence_manifest.json']:
  if p.is_relative_to(P):assert subprocess.run(['git','check-ignore','--quiet','--',rel(p)],cwd=R).returncode==0
  rec=hub.artifact(ss['task_id'],ss['identity']['agent_id'],p,{'run':'run_060','scope':'single candidate preparation and pre-solve protocol only; no execution authority'},version='run060-final-v1');records.append({'path':rel(p),'sha256':rec['sha256']})
 body={'run':'run_060','status':'PREPARED_TO_REQUEST_ONE_I06_RESOLUTION_RUN','job_name':point['job_name'],'inp_sha256':point['inp_sha256'],'manifest_path':rel(A/'prepared_batch.json'),'manifest_sha256':sha(A/'prepared_batch.json'),'report_path':rel(P/'scientific_report.md'),'report_sha256':sha(P/'scientific_report.md'),'baseline_status':'QUALIFIED_WITH_LIMITATIONS','preflight_passed':1,'dry_run_passed':1,'new_FE':0,'new_queue':0}
 msg=hub.message(ss['task_id'],ss['identity']['agent_id'],'MAIN',body,'run060-final-preparation-handoff-v1');hub.finish(ss['lease'],body,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain()
 save(P/'agenthub_completion_receipt.json',{'at':now(),'task_id':ss['task_id'],'task':hub.task(ss['task_id']),'registered_artifacts':records,'outbox_message_id':msg['message_id'],'audit_chain_valid':True,'other_Codex_reception_not_claimed':True})
 write(RUN/'summary.md','# run_060 — I06数值分辨能力验证准备\n\n**WARNING / PREPARED_TO_REQUEST_ONE_I06_RESOLUTION_RUN。** I06原始输入/ODB/440点完整历史与数值警告已核验，继续QUALIFIED_WITH_LIMITATIONS。唯一候选SPIO_R060_I06_M00125已冻结；仅最大增量.0025→.00125及2处身份注释变化，材料/其余模型字节保持。当前Preflight/Dry-run通过，8项测试通过。\n\n见[冻结清单](artifacts/prepared_batch.json)、[比较契约](artifacts/comparison_contract.json)、[比较协议](artifacts/private/comparison_protocol.md)、[私有报告](artifacts/private/scientific_report.md)、[证据清单](artifacts/private/evidence_manifest.json)、[AgentHub收据](artifacts/private/agenthub_completion_receipt.json)。\n\n比较绑定run059弱方向3.092632613N RMS与预设.1/.25/.5风险比，只是探索提示而非正式收敛标准；中心检查不能认证P01–P04或整个Jacobian。run055–059冻结、预测器、原科学结论及Git治理保持。当前新增FE授权0，未入队/求解/Datacheck/重试/重训/优化/拉伸读取/Git提交，完成后停止等待单独授权。\n')
 important=[A/'prepared_batch.json',A/'comparison_contract.json',P/'scientific_report.md',P/'comparison_protocol.md',P/'evidence_manifest.json',P/'agenthub_completion_receipt.json']
 save(A/'manifest.json',{'version':'run060-artifact-index-v1','files':[{'path':rel(p),'sha256':sha(p),'private':p.is_relative_to(P)} for p in important]})
 j=read(RUN/'run.json');shutil.copyfile(RUN/'run.json',RUN/'checkpoints/run_before_complete.json');j.update(status='WARNING',end_time=now(),outcome='PREPARED_TO_REQUEST_ONE_I06_RESOLUTION_RUN',inputs=[{'path':rel(P/'source_manifest.json'),'role':'bounded old-source provenance','sha256':sha(P/'source_manifest.json')}],outputs=[{'path':rel(p),'role':'frozen preparation evidence','sha256':sha(p)} for p in important],validation=[{'check':'baseline identity/control/coverage','status':'QUALIFIED_WITH_LIMITATIONS','evidence':rel(P/'I06_baseline_audit.json'),'scope':'existing I06 numerical warnings and lack of time convergence retained'},{'check':'input exact allowed diff','status':'PASS','evidence':rel(P/'input_byte_audit.json'),'scope':'one max increment plus2 identity comments; all material bytes fixed'},{'check':'public previews','status':'PASS','evidence':rel(P/'public_preflight_dry_run.json'),'scope':'one Preflight/Dry-run, no mutation or Solver launch'},{'check':'offline verification','status':'PASS','evidence':rel(P/'offline_tests.json'),'scope':'8 mathematical/identity tests'}],errors=[],new_INP=1,new_FE_authorized=0,new_queue=0,solver_datacheck_started=False,predictor_retrained=False,tensile_access=False,agenthub_task_id=ss['task_id'])
 tmp=RUN/'run.json.tmp';tmp.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');read(tmp);tmp.replace(RUN/'run.json')
 index=R/'run/README.md';oldindex=index.read_bytes();assert b'run_060' not in oldindex;extra='\n\n## 新准备 Run — run_060\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_060 | 唯一I06增量细化输入、弱方向比值及比较协议冻结 | WARNING（仅准备） | [summary](run_060/summary.md) |\n\n仅最大增量.0025→.00125，Preflight/Dry-run及8项测试通过；当前新FE授权0、未入队/求解，完成后停止等待单独授权。\n';index.write_bytes(oldindex+extra.encode())
 status=R/'status/PROJECT_STATUS.md';oldstatus=status.read_bytes();prefix='# SMALL-PUNCH 项目状态\r\n'.encode();assert oldstatus.startswith(prefix)
 note=f'\r\n## 当前状态 — run_060（{now()[:10]}，Asia/Shanghai）\r\n\r\n**WARNING / PREPARED_TO_REQUEST_ONE_I06_RESOLUTION_RUN。** I06源身份/完整FD核验，QUALIFIED_WITH_LIMITATIONS保持；唯一最大增量.00125候选冻结，材料和其余模型字节不变。公开Preflight/Dry-run与8项离线测试通过；比较协议绑定run059弱响应3.092632613N RMS及.1/.25/.5探索风险区间。见[run_060](../run/run_060/summary.md)。当前新FE授权0、未入队/求解/Datacheck/重训/优化，历史冻结/Git治理保持，完成后停止。\r\n';status.write_bytes(prefix+note.encode()+oldstatus[len(prefix):])
 save(RUN/'checkpoints/completed.json',{'at':now(),'status':'WARNING','job_name':point['job_name'],'inp_sha256':point['inp_sha256'],'manifest_sha256':sha(A/'prepared_batch.json'),'report_sha256':sha(P/'scientific_report.md'),'comparison_contract_sha256':sha(A/'comparison_contract.json'),'new_INP':1,'new_FE':0,'new_queue':0,'stopped':True})
 print(json.dumps({'status':'WARNING','job':point['job_name'],'inp_sha256':point['inp_sha256'],'preflight':'PASS','dry_run':'PASS','tests':8,'report_sha256':sha(P/'scientific_report.md'),'manifest_sha256':sha(A/'prepared_batch.json'),'source_records_preserved':len(sources),'Hub_task':ss['task_id'],'new_FE':0,'new_queue':0}))

if __name__=='__main__':main()
