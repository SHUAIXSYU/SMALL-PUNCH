"""Freeze static evidence and record preparation-only completion through AgentHub."""
from common import *
import csv, shutil, zipfile
sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub

def main():
    start=read(RUN/'checkpoints/start.json');old=read(R/'run/run_056/artifacts/private/prospective_design_contract.json')
    generated=read(P/'candidate_generation.json');preview=read(P/'preflight_dry_run_results.json');model=read(P/'predictor_freeze_receipt.json')
    ss=read(P/'hub_session.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);hub.heartbeat(ss['lease'])
    # Record the complete final test invocation and any earlier resolved test defect separately.
    result=subprocess.run([sys.executable,'-B',str(A/'test_frozen_preparation.py')],cwd=R,text=True,capture_output=True)
    save(P/'preparation_tests.json',{'at':now(),'interpreter':sys.executable,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'tests':11,'scope':'input identity and material/skeleton invariance; no-write API evidence; packaged inference; synthetic A/B metrics; constant-baseline discrimination; Git preservation','initial_resolved_test_failure':rel(RUN/'checkpoints/initial_test_failure.json')})
    assert result.returncode==0
    assert read(P/'I06_public_API_recheck.json')['status']['status']=='COMPLETED'
    assert preview['preflight_passed']==preview['dry_run_passed']==4
    for f,h in preview['protected_after'].items():assert sha(R/f)==h
    assert git('rev-parse','HEAD')==start['head'] and git('diff','--cached','--name-status')==start['staged']
    assert sha(R/'.gitignore')==start['gitignore_sha256']
    for m in start['local_CAE']:assert sha(R/m['path'])==m['sha256']
    for s in read(P/'source_manifest.json')['sources']:assert sha(R/s['path'])==s['sha256'],s['path']
    for p in generated['points']:
        assert sha(R/p['inp_path'])==p['inp_sha256'] and not any((R/p['working_dir']).iterdir())
    freeze_at=now()
    contract={'version':'run057-prospective-identification-evaluation-v1','frozen_at':freeze_at,'parent_contract':rel(R/'run/run_056/artifacts/private/prospective_design_contract.json'),'parent_contract_sha256':sha(R/'run/run_056/artifacts/private/prospective_design_contract.json'),'parent_semantics_unchanged':True,'baseline':old['baseline'],'baseline_status':'QUALIFIED_WITH_LIMITATIONS','parameter_normalization':old['parameter_normalization'],'evaluation_A':old['evaluation_A'],'evaluation_B':old['evaluation_B'],'numerical_admission_and_stops':old['numerical_admission_and_stops'],'numerical_contract':'run030-standard-m0025-hollomon-v1','loss_contract':'run017-exploratory-fd-v1','numerics':old['numerics'],'material':old['material'],'features':{'loads_mm':[.15,.30,.45,.60,.75,.90,1.05,1.20],'slopes_N_per_mm':'endpoint secants .15-.30,.30-.60,.60-.90,.90-1.20mm','areas_J':'exact native polyline trapezoids with inserted boundary points, no resampling approximation','full241_grid_m':'linspace(0,.0012,241)','sign':'u=-U2, F=-RF2, no extra axisymmetric multiplier','no_smoothing_shift_extrapolation':True},'predictor_package':model,'metric_implementation':rel(A/'prospective_metrics.py'),'metric_implementation_sha256':sha(A/'prospective_metrics.py'),'inference_implementation':rel(A/'predict_frozen.py'),'inference_implementation_sha256':sha(A/'predict_frozen.py'),'sign_roundoff_only_zero_tolerance':1e-12,'not_a_scientific_threshold_change':True,'future_candidates':[{'candidate_id':p['candidate_id'],'design_id':p['design_id'],'job_name':p['job_name'],'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n'],'x':p['x'],'y':p['y'],'inp_path':p['inp_path'],'inp_sha256':p['inp_sha256']} for p in generated['points']],'evaluation_state':'FROZEN_BEFORE_ANY_NEW_FE; A/B metrics NOT_EVALUABLE until real admitted outputs','future_authority':{'FE_evaluation_budget_authorized':0,'INP_preparation_authorized':4,'attempts_per_future_job_if_authorized':1,'automatic_retries':0,'requires_explicit_frozen_job_hash_workdir_project_run_authorization':True,'user_GUI_start_only':True,'V02_and_other_job_allowances_not_reused':True}}
    save(P/'comparison_contract.json',contract)
    protocol='''# run057 — 前瞻性评价执行协议（未来四点输出前冻结）

本协议仅把run056设计落实为4份输入和已冻结预测器，不改run056的参数、特征、门槛和科学边界。权威机器记录为comparison_contract.json及其父run056 v2。当前FE执行预算0，4份INP准备已获准，未入队、未求解。

## 基准和同一性

复用I06：236.49902622197678 MPa，n=.0968；u=-U2、F=-RF2，Node ASM_SPT.1、Step_Punch_Displacement。真实DC和Full完成，原440点提取与当前INP/ODB/原生历史哈希一致。I06与四点全部采用初始.001/最大.0025、最小1e-12、time1、inc999999；14CPU0GPU。保留18cutback、被拒试算警告、ZERO MOMENT、DAT tracking与旧进程证明缺口，资格为QUALIFIED_WITH_LIMITATIONS；不是时间步收敛误差上界。没有第五个中心输入。不得以其他中心或.00125结果替代。

## Study A：局部响应与特征区分

四点完整精度取prepared_batch.json；x=ln(sigma_y/150)/ln(1000/150)，y=(n-.02)/.48，hx=hy=.025，两轴中央割线分母.05。主view：固定2 F(.15)/F(.90)，固定5 F(.15)/F(.30)/F(.60)/F(.90)/Wtotal，完整241点。次view：早期2 F(.15)/F(.30)，独立3 F(.15)/F(.30)/K(.60-.90)。不得事后选最有利组合。

载荷/Fref，斜率/(Fref/1.2mm)，总面积/(Fref*.0012m)，每view行再/sqrt(m)，Fref1428.9N是尺度而非噪声。曲线统一0–1.2mm/241点线性插值；面积仍按原始折线与精确边界梯形积分。无平滑、删除、零点移动、外推。报告两列方向/范数、余弦/夹角、SVD、条件数、显式秩容差，0–.3/.3–.6/.6–.9/.9–1.2mm分段分布。奇异时条件数为null且注明SINGULAR，不能造有限数。

每轴保留两侧割线、偶分量(plus+minus)/2-center与奇分量(plus-minus)/2及其范数比eta。单一扰动幅度不能验证h收敛。预注册警示：|cos|>=.98、condition>=20、eta>.20、弱方向半步载荷RMS<=2N；它们不是通用识别定理或测得噪声阈值。若数值不确定性不能排除弱方向退化，结论UNRESOLVED。无可信误差协方差，正式Fisher置信区间NOT_EVALUABLE。

## Study B：真正未见FE点的原始参数预测

使用byte-identical run055最终25点模型，见frozen_predictor/predictor_contract.json。不是250条外层预测拼成模型；250条为交叉验证记录，最终每个Ridge只用25个不同参数点全量拟合。two_ridge lambda=.01，five_ridge/full_ridge lambda=.0001，均来自run055训练期规则；run057只核验及封包，没有替换。固定均值、尺度、系数、截距、特征及支持域。四点B全部完成前不重训、筛选、调参、重新标准化；不使用真实拉伸数据。

主比较原始未裁剪预测的MPa/n MAE、RMSE、最大与逐点绝对/相对误差；报告参数边界、凸包及特征最近邻支持度。常数I06基线和原run055均值/中位数必须保持来源区别。n负臂P03在已有联合训练凸包外，其他三臂在内；四点仅验证I06邻域，不能称广域验证。

E_local=sqrt(mean over 4x2 (((qhat-qtrue)/.025)^2))，常数I06为sqrt(.5)。分辨工程目标：每点每坐标误差<=.0125，活动轴符号四点正确，E_local严格小于常数基线。浮点1e-12零容差只用于符号分类，不改变原始预测或科学误差门槛。另报model(newFD)-model(I06FD)相对真实扰动的增量诊断，不能据此重新居中或替代绝对预测。

A映射分离与B回归精度分别结论，不互相代替。完整曲线的数值纹理、已有稀疏覆盖和回归偏差都要保留。不能因为常数已很接近就宣告识别成功。

## 数值门控、预算与执行

完整Job/INP SHA/ODB/queue_id与尝试身份；DC成功后Full成功、窗口完整、PEEQ<.9；接受trial严重警告、未解释反力/接触异常或身份不一致需停止/不可评分。PEEQ>=.85、拒绝>50或拒绝/接受>10%、耗时>20min触发复核，非自动Solver停机。负反力步保留精确幅值和上下文；拒绝试算警告不作为接受物理状态。历史六个null不改。失败不补跑、不改参数、不换模型；缺项只做partial A/B，不伪造完整Jacobian。

本轮没有新FE授权。未来需绑定本批4个完整哈希、工作目录、Project ID b87d2cd6-8519-4ac3-bae6-7eb989fb2dae，14CPU0GPU、每项一次DC成功后Full、零自动重试；用户GUI手动启动，明确批量模式或逐项模式及AUTO_STOP_UNAVAILABLE风险。原I06294s仅是历史成本；规划4–20min/项、总16–80min不是保证。先在未来入队时重新预检运行状态/覆盖冲突。当前预览不证明Abaqus真实语法、许可证、数值收敛或物理有效。

保留run046冻结、run047/048正式NOT_EVALUABLE及历史run015暴露记录。未读拉伸或其封存分析，不做材料重新标定，不执行新优化。完成本次准备后停止。
'''
    write(P/'prospective_evaluation_protocol.md',protocol)
    prepared={'version':'run057-four-prospective-INPs-frozen-v1','frozen_at':freeze_at,'status':'PREPARED_PREVIEW_PASSED_NO_EXECUTION_AUTHORIZATION','baseline_status':'QUALIFIED_WITH_LIMITATIONS','project_id':'b87d2cd6-8519-4ac3-bae6-7eb989fb2dae','project_path':'agenthub_sp_invopt/abqjobpilot_project','project_absolute_path':str(R/'agenthub_sp_invopt/abqjobpilot_project'),'numerical_contract':'run030-standard-m0025-hollomon-v1','loss_contract':'run017-exploratory-fd-v1','parent_design':contract['parent_contract'],'parent_design_sha256':contract['parent_contract_sha256'],'comparison_contract_path':rel(P/'comparison_contract.json'),'comparison_contract_sha256':sha(P/'comparison_contract.json'),'protocol_path':rel(P/'prospective_evaluation_protocol.md'),'protocol_sha256':sha(P/'prospective_evaluation_protocol.md'),'predictor_package_path':model['package_path'],'predictor_package_sha256':model['package_sha256'],'agenthub_task_id':ss['task_id'],'preparation_actor':ss['identity']['agent_id'],'resources':{'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0},'order':[p['job_name'] for p in generated['points']],'points':generated['points'],'preflight_passed':4,'dry_run_passed':4,'new_queue':0,'new_FE':0,'future_solver_authorization_required':True}
    save(A/'prepared_batch.json',prepared)
    with (A/'batch_identity.csv').open('x',encoding='utf-8',newline='') as stream:
        keys=['candidate_id','job_name','sigma_y_mpa','n','inp_absolute_path','inp_sha256','working_dir_absolute','expected_odb_absolute']
        w=csv.DictWriter(stream,fieldnames=keys);w.writeheader();w.writerows({k:p[k] for k in keys} for p in generated['points'])
    report=['# run057 — I06四点输入与前瞻预测器冻结','',f'完成：{now()}。**WARNING / READY_TO_REQUEST_FOUR_PROSPECTIVE_RUNS_WITH_LIMITATIONS**。','',
        '## 实际执行与权限','',
        '本次用户授权仅四份候选准备及离线模型核验/公开预览。当前会话MAIN直接完成文件准备和独立数学/身份检查，通过正式Hub登记MAIN任务；没有声称另一个CAE Codex会话领取或完成。没有跨会话自动唤醒、没有假worker、没有入队或启动Solver/datacheck。当前新FE预算0。','',
        '## I06基准','',
        '当前公开API返回COMPLETED，旧DC/Full日志均return_code=0，ODB成功终态与源INP/ODB完整哈希匹配；重新核对STA/MSG和440点原始历史/正向FD，RP为Node ASM_SPT.1，u=-U2/F=-RF2，完整覆盖1.2mm且与run055已有特征和241点逐值一致。439接受增量、18cutback、PEEQ .7027503848075867，材料表上界.9。接受trial仅ZERO_MOMENT；被拒试算的大应变/负特征值/畸变不冒称接受态物理异常。DAT tracking与历史进程证明缺口保留。','I06符合原探索性门控并与未来四点控制相同，但没有自身独立时间步细化验证；资格QUALIFIED_WITH_LIMITATIONS，不能成为已收敛Jacobian的精度证明。当前未发现需停候选准备的身份/覆盖/控制硬失败；不追加第五中心、也不以其他精化中心替代。','',
        '## 候选输入与一致性','',
        '所有候选来源于原I06，初始.001/最大.0025、最小1e-12/time1/inc999999保持。材料仅替换*Plastic数据行，另外三处注释更新Job/参数身份。其余原始字节与有效物理骨架保持一致，包括E210GPa、nu.3、几何/网格/摩擦/接触/夹持/压入-1.2mm/能量和RP输出。无INCLUDE等外部相对路径依赖。','',
        '|候选|Job|sigma_y MPa|n|表行数|SHA-256|','|---|---|---:|---:|---:|---|']
    for p in generated['points']:report.append(f'|{p["candidate_id"]}|{p["job_name"]}|{p["sigma_y_mpa"]!r}|{p["n"]!r}|{p["material_rows"]}|{p["inp_sha256"]}|')
    report+=['','应力Pa、塑性应变无量纲，首行sigma_y×1e6，严格单调、0–.9覆盖；生成器源码SHA及材料变换定义已绑定。原I06材料表可由同生成器逐值复现；四张新表解析/密集解析曲线比较均满足.001插值容差。仅行数自适应变化，不改变物理材料族。','',
        '## 预测器冻结与前瞻性','',
        f'优先执行run056绑定，完整原模型文件SHA保持{model["original_model_sha256"]}。最终模型是run055以25个唯一参数点全量拟合，不是250条外层预测或各折系数拼接。复核训练IDs/原矩阵/内层选择与固定lambda重算，以及独立SVD推理；不采用新模型替换，未来4点没有结果也未参与训练。',
        '主模型two_ridge lambda=.01、five_ridge/full_ridge lambda=.0001；输入特征/均值/尺度/截距/回归系数与支持域已封包。常数I06单独冻结；其他run055既有模型及参数均保留作原预注册次级诊断。包内同时保存25点完整FE训练数据、每样本来源、训练和特征代码快照、SHA清单及只推理入口。所有含可恢复曲线内容均Git忽略。',
        f'预测包SHA-256：{model["package_sha256"]}。训练25点文件SHA-256：{model["training_25_sha256"]}。','',
        '## 工程预览与测试','',
        '当前正式AbqJobPilot0.2.2公开API返回Settings=PERSISTED；Abaqus2024路径存在，14CPU0GPU、DC/Full开启。Runner owner ABSENT，Runtime CLEAN，现有Queue无其他可执行任务；4个Job/INP无重复，工作目录全空且独立。4/4 PREVIEW_READY、4/4 DRY_RUN_READY，Queue/Settings/Project/project.db哈希前后一致，未创建queue_id或求解输出。预览不能代替真实Abaqus语法、许可证、收敛和物理检验。',
        '11项测试通过：源模型与候选差异、数值控制篡改检测、材料单位/单调/范围、dry-run保护、无外推、冻结推理与原模型一致、25唯一训练组、合成割线/SVD退化、常数基线不能通过半步分辨目标，以及Git保护。首次测试发现常数基线浮点归一化产生极小假符号，已以1e-12 roundoff-only零判别修复并保留失败检查点；不改原预测、不改run056门槛，不是FE重试。','',
        '## 限制、停止与下一步','',
        'Study A同中心/同控制割线与Study B冻结逆模型前瞻参数预测严格分开。4个邻点只检验局部；P03负n臂在现有联合训练凸包外，不保证泛化/成功。旧25点覆盖稀疏、两参数响应可能高度耦合、全曲线数值纹理敏感、单步长及I06自身误差未知；不做正式Fisher置信区间、全域唯一性或材料真值宣称。',
        '身份/合同偏离、DC/Full失败、窗口不全、材料范围超出、接受态严重异常或不兼容均按冻结门控停止/保留null，不自动修补、补跑或改参。警告与实际失败分开。未来若需要实际4次计算，应授权prepared_batch.json绑定的唯一Job/INP完整hash/工作目录/Project，14CPU0GPU、每项一次DC成功后Full、零重试、仅用户GUI启动，并明确AUTO_STOP_UNAVAILABLE执行风险；本轮仅达到有条件申请运行授权的准备状态。','',
        'Git忽略哈希与2个暂存CAE索引删除完整保留，本地2份CAE哈希未变。没有新CAE二进制，没有Git提交/推送/重置/清理。原用户project.db等改动保留；所有131项受保护旧源记录不变，run046/047/048/053/055/056历史不覆盖。未读拉伸原件或封存分析，保留run015历史暴露事实；未来模型开发不能借用该文件而仍称独立验证。','',
        '证据：prepared_batch.json、I06_baseline_audit.json、candidate_generation.json、comparison_contract.json、prospective_evaluation_protocol.md、predictor_freeze_receipt.json、preflight_dry_run_results.json、preparation_tests.json、evidence_manifest.json和AgentHub收据。完成后停止，无未来计算自动执行。','']
    write(P/'scientific_report.md','\n'.join(report))
    save(P/'scientific_decision.json',{'status':'WARNING','baseline':'QUALIFIED_WITH_LIMITATIONS','INP_frozen':4,'preflight':4,'dry_run':4,'predictors_frozen_before_future_FE':True,'ready_to_request_four_jobs':'CONDITIONAL_YES','new_FE_authorized':0,'new_enqueues':0,'new_solver_datacheck':0,'no_tensile_used':True,'report_sha256':sha(P/'scientific_report.md'),'candidate_manifest_sha256':sha(A/'prepared_batch.json')})
    save(P/'git_preservation_final.json',{'at':now(),'head':git('rev-parse','HEAD'),'status':git('status','--short'),'staged':git('diff','--cached','--name-status'),'gitignore_sha256':sha(R/'.gitignore'),'local_CAE_hashes':[{'path':m['path'],'sha256':sha(R/m['path'])} for m in start['local_CAE']],'CAE_deleted':0,'Git_index_mutations_this_run':0})
    # Register complete immutable output hashes using the formal Hub interface.
    static=[p for p in sorted(A.rglob('*')) if p.is_file() and p.name not in ['hub_session.json','evidence_manifest.json','manifest.json','agenthub_completion_receipt.json'] and '__pycache__' not in p.parts]
    entries=[{'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in static]
    save(P/'evidence_manifest.json',{'version':'run057-static-evidence-v1','at':now(),'files':entries,'excludes':['self','live lease','later completion receipt','run metadata/index/status']})
    count=0
    for p in static+[P/'evidence_manifest.json']:
        if p.is_relative_to(P):assert subprocess.run(['git','check-ignore','--quiet','--',rel(p)],cwd=R).returncode==0,rel(p)
        hub.artifact(ss['task_id'],ss['identity']['agent_id'],p,{'run':'run_057','scope':'authorized offline input/predictor preparation only','no_FE_or_enqueue':True},version='run057-final-v1');count+=1
    write(RUN/'summary.md','# run_057 — 前瞻性四点输入与预测器冻结\n\n**WARNING / READY_TO_REQUEST_FOUR_PROSPECTIVE_RUNS_WITH_LIMITATIONS。** I06身份/原始提取/同数值控制复核通过，资格QUALIFIED_WITH_LIMITATIONS。四份独立材料变体INP及完整SHA已冻结，4/4公开Preflight和4/4 Dry-run通过。run055全25点最终预测器原文件不变，25点训练身份/代码/系数/支持域和常数I06基线均已封包；Study A/B沿用run056冻结规则。\n\n见[冻结批次](artifacts/prepared_batch.json)、[私有报告](artifacts/private/scientific_report.md)、[前瞻评价协议](artifacts/private/prospective_evaluation_protocol.md)、[预测器包](artifacts/private/SPIO_run057_frozen_predictors.zip)、[静态证据](artifacts/private/evidence_manifest.json)。11项测试通过；Git暂存2个CAE索引删除和本地文件保留。\n\nI06未独立时间步精化、P03为轻微联合凸包外推，样本覆盖/参数耦合/数值误差仍限制识别结论。当前执行预算0、入队0、Solver/Datacheck0，没有新中心、重试、材料拟合、拉伸读取、优化或Git提交。仅具备申请具体四Job授权的工程准备条件，完成后停止。\n')
    pubfiles=[A/'prepared_batch.json',A/'batch_identity.csv',P/'scientific_report.md',P/'evidence_manifest.json',P/'comparison_contract.json',P/'SPIO_run057_frozen_predictors.zip']
    save(A/'manifest.json',{'version':'run057-artifact-index-v1','files':[{'path':rel(p),'sha256':sha(p),'private':p.is_relative_to(P)} for p in pubfiles]})
    j=read(RUN/'run.json');shutil.copyfile(RUN/'run.json',RUN/'checkpoints/run_before_complete.json')
    j.update(status='WARNING',end_time=now(),outcome='READY_TO_REQUEST_FOUR_PROSPECTIVE_RUNS_WITH_LIMITATIONS',inputs=[{'path':rel(P/'source_manifest.json'),'role':'bounded protected source identities','sha256':sha(P/'source_manifest.json')}],outputs=[{'path':rel(p),'role':'frozen preparation evidence','sha256':sha(p)} for p in pubfiles],validation=[{'check':'I06 identity and control','status':'QUALIFIED_WITH_LIMITATIONS','evidence':rel(P/'I06_baseline_audit.json'),'scope':'existing complete reference; not independent time-step refinement'},{'check':'INP material and skeleton','status':'PASS','evidence':rel(P/'candidate_generation.json'),'scope':'four material-only variants plus allowed identity comments'},{'check':'public API previews','status':'PASS','evidence':rel(P/'preflight_dry_run_results.json'),'scope':'4/4 previews/dry-runs, queue/Project/Settings unchanged'},{'check':'predictor identity and all25 refit verification','status':'PASS','evidence':rel(P/'predictor_freeze_receipt.json'),'scope':'unchanged final model; no prospective data or new selection'},{'check':'offline tests','status':'PASS','evidence':rel(P/'preparation_tests.json'),'scope':'11 tests'}],errors=[{'code':'SIGN_ROUNDOFF_TEST_DEFECT','severity':'RESOLVED','message':'Floating-point normalization of constant center caused spurious sign; 1e-12 numerical-zero classification fixed before prospective outputs; raw predictions and scientific gates unchanged','evidence':rel(RUN/'checkpoints/initial_test_failure.json')}],agenthub_task_id=ss['task_id'],new_INP=4,new_FE=0,new_queue=0,solver_datacheck_started=False,baseline_status='QUALIFIED_WITH_LIMITATIONS',material_refit=False,tensile_content_read=False)
    tmp=RUN/'run.json.tmp';tmp.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');read(tmp);tmp.replace(RUN/'run.json')
    # Append the new run; preserve all earlier index/status bytes.
    index=R/'run/README.md';oldindex=index.read_bytes();addition='\n\n## 新授权 Run — run_057\n\n| Run | 阶段 | 目标 | 状态 | 总结 |\n| --- | --- | --- | --- | --- |\n| run_057 | Prospective Identification Batch Preparation | I06四点材料变体、冻结预测器与公开预览 | WARNING（仅准备） | [summary](run_057/summary.md) |\n\n四输入/完整SHA与A/B前瞻协议冻结，4/4预检和dry-run通过；I06带限制，11项测试通过，新FE/入队0。仅可申请明确四Job运行授权，当前完成后停止。\n'
    assert b'run_057' not in oldindex;index.write_bytes(oldindex+addition.encode())
    status=R/'status/PROJECT_STATUS.md';oldstatus=status.read_bytes();header='# SMALL-PUNCH 项目状态';prefix=(header+'\r\n').encode();assert oldstatus.startswith(prefix)
    note='\r\n## 当前状态 — run_057（2026-10-27，Asia/Shanghai）\r\n\r\n**WARNING / READY_TO_REQUEST_FOUR_PROSPECTIVE_RUNS_WITH_LIMITATIONS。** I06原提取/输入/同控制复核、四个独立INP及完整哈希冻结；4/4公开Preflight和Dry-run通过，run055原最终25点预测器封包不变，11项离线测试通过。I06未独立精化且P03凸包外推限制保留；详见[run_057](../run/run_057/summary.md)。新FE预算0、未入队/求解/Datacheck/重试/优化/拉伸读取/Git提交，停止等待明确授权。\r\n'
    status.write_bytes(prefix+note.encode()+oldstatus[len(prefix):])
    completion={'run':'run_057','status':'PREPARED_WITH_LIMITATIONS','new_INP':4,'new_FE':0,'new_queue':0,'preflight_passed':4,'dry_run_passed':4,'predictor_package_sha256':model['package_sha256'],'manifest_path':rel(A/'prepared_batch.json'),'manifest_sha256':sha(A/'prepared_batch.json'),'report_path':rel(P/'scientific_report.md'),'report_sha256':sha(P/'scientific_report.md'),'baseline':'QUALIFIED_WITH_LIMITATIONS','actual_other_Codex_delivery_not_claimed':True}
    message=hub.message(ss['task_id'],ss['identity']['agent_id'],'MAIN',completion,'run057-preparation-completion-v1')
    hub.finish(ss['lease'],completion,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain()
    save(P/'agenthub_completion_receipt.json',{'at':now(),'task_id':ss['task_id'],'task':hub.task(ss['task_id']),'artifacts_registered':count,'outbox_message_id':message['message_id'],'audit_chain_valid':True,'message_delivery_scope':'persisted MAIN inbox/outbox only; not proof another Codex session received or read'})
    save(RUN/'checkpoints/completed.json',{'at':now(),'status':'WARNING','candidate_manifest_sha256':sha(A/'prepared_batch.json'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'agenthub_task_id':ss['task_id'],'new_FE':0,'new_queue':0,'new_INP':4,'git_staged_unchanged':git('diff','--cached','--name-status')==start['staged']})
    print(json.dumps({'status':'WARNING','baseline':'QUALIFIED_WITH_LIMITATIONS','new_INP':4,'preflight':4,'dry_run':4,'tests':11,'new_queue':0,'new_FE':0,'manifest_sha256':sha(A/'prepared_batch.json'),'report_sha256':sha(P/'scientific_report.md'),'hub_task':ss['task_id'],'hub_artifacts':count}))

if __name__=='__main__':main()
