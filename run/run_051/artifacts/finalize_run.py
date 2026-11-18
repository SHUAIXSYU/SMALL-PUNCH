"""Finalize the tested, independently prepared two-scenario package, with zero FE authorization."""
from pathlib import Path
from datetime import datetime
import sys,json,hashlib,subprocess,os
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_051';A=RUN/'artifacts';P=A/'private';sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return p.relative_to(R).as_posix()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def atomic(p,v):
 t=p.with_suffix(p.suffix+'.new');save(t,v);read(t);os.replace(t,p)

def main():
 contract=read(A/'material_contract.json');prepared=read(A/'prepared_batch.json');review=read(P/'main_preflight_dry_run.json');energy=read(P/'energy_basis_audit.json');tests=read(P/'unit_test_run.json');tangents=read(P/'exported_tangent_checks.json');session=read(P/'hub_session.json');cae=read(P/'cae_task_identity.json')
 assert tests['return_code']==0 and tests['tests']==18 and tangents['all_checks_passed'] and review['preflight_passed']==review['dry_run_passed']==2
 assert review['queue_unchanged'] and all(p['all_nonplastic_bytes_identical'] and p['original_low_rows_identical'] for p in review['points'])
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);hub.heartbeat(session['lease']);ct=hub.task(cae['task_id']);assert ct['execution_state']=='COMPLETED'
 protected=read(P/'protected_before.json');assert all(sha(R/p)==v for p,v in protected.items())
 old047=R/'run/run_047/artifacts/private/independent_validation_report.md';assert sha(old047)=='e9c118714ba39d12662a31304c57140e95144cb7d0b4b5dddd9bd20d3d7bdf52'
 for f in read(R/'run/run_046/artifacts/private/freeze/frozen_manifest.json')['files']:assert sha(R/f['path'])==f['sha256']
 assert sha(A/'highp_envelope.py')==contract['implementation_sha256'] and sha(A/'material_contract.json')==prepared['material_contract_sha256']
 assert len(list(RUN.rglob('*.inp')))==2 and not list(RUN.rglob('*.odb'))
 for p in prepared['points']:
  assert sha(R/p['inp_path'])==p['inp_sha256'] and not any((R/p['working_dir']).iterdir())
 private_files=[p for p in P.rglob('*') if p.is_file()];assert all(subprocess.run(['git','check-ignore','--quiet','--',rel(p)],cwd=R).returncode==0 for p in private_files)
 save(P/'final_integrity.json',{'at':now(),'protected_originals_unchanged':protected,'run047_historical_report_sha256':sha(old047),'all_19_frozen_manifest_files_unchanged':True,'candidate_INP_count':2,'new_solver_attempts':0,'new_queue_items':0,'private_files_ignored':len(private_files),'no_parameter_refit_or_tensile_input':True})
 lines=['# run_051 — D01 高塑性应变硬化包络准备','\n**WARNING / READY_TO_REQUEST_TWO_EXPLORATORY_SOLVES。** 本Run只准备两个独立材料敏感性候选，尚未获得Solver/Datacheck或入队授权；不能把工程预览通过当求解或科学验证。',
 '\n## A. 塑性功口径确认',
 '\nrun050的70.9847%/69.2637%来自v2：每个保存帧间用实际S.Mises与ΔPEEQ，在阈值处拆分并累计PEEQ>.1之后的增量功。它们不是按终态区域分类的全部历史功；后者v1对应95.8417%/94.9326%。已有805/802保存帧、每帧2376个CAX4积分点和参考体积权重，足以开展这种离散重构。估计仍有保存帧路径线性/参考体积假设，终态与直接ALLPD差约.116%/.112%，不是直接局部耗散，任何比例都不等于Punch RF2份额。',
 '\n本轮核对来源hash、v1/v2定义和分项总和，未重新启动提取或求解。p>.1的比例也不能直接更名为本次p_switch后的比例，因为两阈值不同。',
 '\n## B. 修改起点与不可改动的低段',
 f"\n冻结D01：σy=152.3086335396325MPa，n=.23066241424320405，E=210GPa，ν=.3。按其原真总应变Hollomon预测，σ(ε_total=.10)={contract['p_switch_D01_analytic_stress_pa']/1e6:.15g}MPa，因此p_switch=.10−σ/E={contract['p_switch']:.17g}。这里没有使用已解盲拉伸的应力。",
 f"\n材料衔接以已求解D01的分段线性表为权威：其在p_switch处为{contract['deployed_anchor_stress_pa']/1e6:.15g}MPa，与解析值差{contract['analytic_minus_deployed_anchor_pa']/1e6:.9g}MPa。保留这项既有离散误差，不通过重采样低段来纠正。两候选各保留36条原低段行字节，仅加一个共线switch行；低段曲线数值差约5.96e-8Pa，为浮点舍入量级。p_switch是设计坐标，不是已认证的材料有效性界限。",
 '\n## C. 预先固定的无量纲包络',
 '\n设原部署表为σ0(p)，H0=dσ0/dp。t=(p−p_switch)/.05；S(t)=0(t≤0)，6t⁵−15t⁴+10t³(0<t<1)，1(t≥1)。H01/H02分别用H(p)=H0(p)[1∓.5S(t)]，并积分后与原应力连续连接。p≤p_switch完全保留原部署曲线。过渡结束p≈.14774053后硬化速率为0.5/1.5倍；这不是应力直接乘0.5/1.5，也不是新反演的σy/n组合。',
 '\n±50%是事前声明的对称工程扰动：最低速率仍正、最终速率比3:1，提供可辨的敏感性对照；.05过渡避免在switch突加50%切线变化。没有真实高p数据支持其为材料上下界，也不是统计置信区间，未按任何拉伸拟合或新FE/Loss调整。',
 '\n原解析调制在起点/过渡末端连续并保持衔接切线；原表自身的旧节点斜率跳变保留，Abaqus导出的线性表不宣称全局C¹。首个新表段相对原段切线仅约∓.02637%；全部分段切线为正。H01最小切线约106.734MPa/单位p，H02约320.201MPa/单位p。',
 '\n在p=.5，原D01为688.275MPa，H01/H02为593.745/782.806MPa；在p=.9，原为788.407MPa，候选为643.811/933.003MPa。以上是材料应力差，不能当作尚未求解的SPT载荷差。',
 '\n## D. 数值与工程验证',
 '\n18项unittest实际通过：源hash、switch定义、低段函数及行文本保持、块外字节、衔接应力/切线、正硬化、对称/排序、范围、分段线性插值误差界、独立数值积分和非法输入等。额外检查实际导出表所有secant硬化倍率范围与正性，不只检查目标解析导数。测试加载器最初有本机GBK解码问题，已显式UTF-8修复并保留失败记录；没有修改环境或历史文件。',
 '\n两表均82行，覆盖p=0–.9。分段误差界使用|σ″|Δp²/8，并保留所有原表节点、switch和过渡端点，避免跨越既有斜率跳变误用界。两候选最大相对界分别9.794e-6/9.556e-6；这相对于本次部署表包络目标，不是对真实材料的误差界。',
 '\n真实CAE会话通过AgentHub领取生成/核验授权，生成两份独立INP。MAIN独立确认：只有*Plastic数据行不同；E/ν、初始屈服、所有低段原行及块外每个字节相同，包括几何/网格/BC/摩擦/接触/加载/输出和Static(.001,1,1e-12,.00125)、inc999999。旧heading注释与旧材料显示名保留以满足字节不变；真实Job身份由下列文件/API请求和hash界定，不按旧注释推断。',
 '\n| ID | Job | 完整INP SHA-256 | Preflight / Dry-run |','|---|---|---|---|']
 for p in prepared['points']:lines.append(f"| {p['candidate_id']} | {p['job_name']} | `{p['inp_sha256']}` | PREVIEW_READY / DRY_RUN_READY |")
 lines += ['\n正式Project身份和PERSISTED Settings已由MAIN公开API重新核验：AbqJobPilot0.2.2，Abaqus2024命令文件存在，14CPU/0GPU、Datacheck与Full配置为真、自动关机关闭。CAE及MAIN均只调用公开preflight和dry-run；Project/Settings/Queue哈希未变，工作目录为空、queue_id=null，无Solver/Datacheck执行。公开预览不验证Abaqus语法、许可证、收敛或材料物理正确性。',
 '\n## E. 冻结未来比较与停止条件',
 '\n未来以精化D01作为唯一旧FE控制，采用固定run017-exploratory-fd-v1、0–1.2mm、241点、Fref1428.9N、等权及线性插值；不平移/平滑/外推/删点。比较F–D差RMSE/最大值及位置、分区响应、Loss/ΔLoss、PEEQ覆盖、直接ALLPD/应变分区估计、1.10–1.16mm接受帧与接触、cutback/接受和拒绝警告及耗时。详见comparison_contract.json的hash绑定。',
 '\n2N RMSE与7.1445N最大差只用作预先声明的工程效应标记，不是统计显著性、物理准确性或故意改变材料后仍必须满足的数值资格门槛。旧D01相邻细化的.3383N只是该点观测差异，不是新包络的数值误差上界。若数值警告/局部突跳不能解释，即使效果大也不能归因于材料硬化；不评分记null，不补跑。',
 '\n若仅高段本构变化产生可复核的F–D变化，可判定该延拓是敏感因素，不能认定唯一实验误差来源。若两候选都不敏感，只能降低此±50%/当前switch与过渡尺度的优先级，不能排除全部高应变模型问题；优先补齐实测夹具条件后做边界对照，再考虑补偿谷地横向识别点，不直接恢复BO/DE。',
 '\n## F. 授权建议与研究边界',
 '\n值得申请恰好两次独立探索性求解，绑定prepared_batch.json中冻结完整hash/路径/工作目录；14CPU/0GPU、每Job最多一次Datacheck成功后一次Full、零重试、用户GUI手动启动。当前执行授权为0，不实际入队。任何身份不明、输出冲突、运行恢复冲突、Datacheck/Full失败、F–D窗口不覆盖、实际PEEQ超.9或未解释严重接受态异常均停止，不自动补点或扩大预算。',
 '\n本轮不重新反演参数、不使用解盲拉伸校准包络、不读取封存旧泄漏分析、不修改run046冻结包或独立验证历史。正式独立验证继续NOT_EVALUABLE，历史暴露事实保留；未来如使用已解盲资料开发模型，须列为开发信息而非未使用验证集。',
 '\n产物：material_contract.json、comparison_contract.json、prepared_batch.json；私有材料图material_envelope_comparison.png、energy_basis_audit.json、unit_test_run.json、exported_tangent_checks.json、main_preflight_dry_run.json。候选hash/路径、实际CAE身份与所有证据登记AgentHub。']
 with (P/'REPORT.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
 with (RUN/'summary.md').open('x',encoding='utf-8') as f:f.write('''# run_051 — 高应变硬化包络离线准备

**WARNING / READY_TO_REQUEST_TWO_EXPLORATORY_SOLVES。**

已核实run050两种塑性功口径，并以冻结D01为唯一基准完成H01/H02后续硬化扰动。幅度和过渡在材料表/新INP生成前冻结；保留低段与原数值控制，未反向拟合任何拉伸资料。

18项离线单元测试通过，材料表插值界和实际切线检查通过；真实CAE通过AgentHub完成两份独立INP，MAIN独立核对只有塑性表行变化，公开API2/2 Preflight与2/2 Dry-run通过。Queue/Settings未变，未执行Solver、Datacheck、入队或优化。

完整[私有报告](artifacts/private/REPORT.md)、[材料契约](artifacts/material_contract.json)、[未来比较协议](artifacts/comparison_contract.json)、[冻结候选清单](artifacts/prepared_batch.json)和[材料对比图](artifacts/private/material_envelope_comparison.png)。工程包络不是真实材料置信边界，准备/预览不代表科学验证。可申请两次新的独立求解，当前未授权执行；停止等待用户决定。历史冻结预测、NOT_EVALUABLE及暴露声明保留。
''')
 idx=R/'run/README.md';old=idx.read_text(encoding='utf-8-sig');assert '## run_051' not in old
 with idx.open('a',encoding='utf-8') as f:f.write('\n\n## run_051 — D01高应变硬化包络准备\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_051 | 塑性功口径核对、两份低段保持的材料包络及真实CAE预览 | WARNING / READY_TO_REQUEST_TWO_EXPLORATORY_SOLVES | [summary](run_051/summary.md) |\n\n无新求解/入队/优化，不修改原预测，完成后停止。\n')
 sp=R/'status/PROJECT_STATUS.md';prior=sp.read_text(encoding='utf-8-sig');save(P/'status_before_run051.json',{'text':prior,'sha256':sha(sp)})
 header='# SMALL-PUNCH 项目状态\n';assert prior.startswith(header)
 new=header+'\n## 当前状态 — run_051（2026-10-26，Asia/Shanghai）\n\n**WARNING / READY_TO_REQUEST_TWO_EXPLORATORY_SOLVES。** 高应变硬化包络H01/H02已冻结，真实CAE完成两份INP，MAIN独立字节/材料核验与公开API2/2预览通过。功统计口径、探索幅度及未来比较规则见[run_051私有报告](../run/run_051/artifacts/private/REPORT.md)。无新Solver、Datacheck、入队、参数拟合或优化；原冻结与正式NOT_EVALUABLE保留。当前只具备申请两次新求解的工程准备条件，执行授权0，完成后停止。\n\n'+prior[len(header):]
 tmp=sp.with_suffix('.md.run051.tmp');tmp.write_text(new,encoding='utf-8');os.replace(tmp,sp)
 save(P/'git_final.json',{'at':now(),'branch':subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'working_tree':subprocess.check_output(['git','status','--short'],cwd=R,text=True),'preexisting_changes_retained':True})
 files=[{'path':rel(p),'sha256':sha(p),'visibility':'PRIVATE_GIT_IGNORED' if P in p.parents else 'MODEL_PREPARATION_CODE_OR_METADATA'} for p in sorted(RUN.rglob('*')) if p.is_file() and p.name!='run.json' and p!=A/'manifest.json']
 save(A/'manifest.json',{'version':'run051-final-evidence-index-v1','at':now(),'files':files,'excludes':'self/run.json and later completion receipt/checkpoint avoid cycles'})
 result={'run':'run_051','status':'READY_TO_REQUEST_TWO_EXPLORATORY_SOLVES','report_path':rel(P/'REPORT.md'),'report_sha256':sha(P/'REPORT.md'),'prepared_manifest_path':rel(A/'prepared_batch.json'),'prepared_manifest_sha256':sha(A/'prepared_batch.json'),'cae_task_id':cae['task_id'],'points':[{'job_name':p['job_name'],'inp_sha256':p['inp_sha256'],'inp_path':p['inp_path'],'working_dir':p['working_dir']} for p in prepared['points']],'tests_passed':18,'preflight_passed':2,'dry_run_passed':2,'queue_changed':False,'solver_attempts':0,'future_solver_authorization':0,'science_state':'WARNING','formal_independent_validation':'NOT_EVALUABLE_UNCHANGED','engineering_envelopes_not_physical_bounds':True}
 save(P/'main_handoff.json',result)
 hub.message(cae['task_id'],session['identity']['agent_id'],'CAE',{'MAIN_review':'byte/material identity and public previews independently passed','run':'run_051','report_path':result['report_path'],'report_sha256':result['report_sha256'],'no_new_solve_authorization':True},'run051-main-cae-ack-v1')
 registered=[]
 for p in [P/'REPORT.md',A/'design_intent.json',A/'material_contract.json',A/'comparison_contract.json',A/'prepared_batch.json',P/'energy_basis_audit.json',P/'unit_test_run.json',P/'exported_tangent_checks.json',P/'material_validation_summary.json',P/'main_preflight_dry_run.json',P/'material_envelope_comparison.png',P/'main_handoff.json',A/'manifest.json']:
  v=hub.artifact(session['main_task_id'],session['identity']['agent_id'],p,{'run':'run_051','source_CAE_task':cae['task_id'],'scope':'offline material/INP preparation and public previews only','no_new_FE':True,'no_tensile_based_parameter_fit':True},version='run051-v1');registered.append({'artifact_id':v['artifact_id'],'path':v['path'],'sha256':v['sha256']})
 msg=hub.message(session['main_task_id'],session['identity']['agent_id'],'MAIN',result,'run051-final-main-v1');hub.finish(session['lease'],result,evidence_state='RECORDED',science_state='WARNING');assert hub.task(session['main_task_id'])['execution_state']=='COMPLETED'
 save(P/'hub_completion.json',{'at':now(),'main_task_id':session['main_task_id'],'CAE_task_id':cae['task_id'],'message_id':msg['message_id'],'registered':registered,'execution':'COMPLETED','science':'WARNING','does_not_automatically_wake_other_sessions':True})
 run=read(RUN/'run.json');save(RUN/'checkpoints/before_final.json',run)
 run.update(status='WARNING',end_time=now(),inputs=[{'path':rel(A/'material_contract.json'),'role':'immutable baseline and engineered material contract','sha256':sha(A/'material_contract.json')},{'path':rel(P/'energy_basis_audit.json'),'role':'existing work attribution identity audit','sha256':sha(P/'energy_basis_audit.json')}],outputs=[{'path':rel(RUN/'summary.md'),'role':'public scope summary'},{'path':rel(P/'REPORT.md'),'role':'private scientific/engineering report','sha256':sha(P/'REPORT.md')},{'path':rel(A/'prepared_batch.json'),'role':'two frozen candidate identities','sha256':sha(A/'prepared_batch.json')},{'path':rel(A/'manifest.json'),'role':'artifact index','sha256':sha(A/'manifest.json')},{'path':rel(P/'hub_completion.json'),'role':'Hub evidence receipt','sha256':sha(P/'hub_completion.json')}],validation=[{'check':'material math and failure-path tests','status':'PASS','evidence':rel(P/'unit_test_run.json'),'scope':'18 tests, no FE'},{'check':'exported material secants and interpolation','status':'PASS','evidence':rel(P/'exported_tangent_checks.json'),'scope':'positive slopes, unchanged low curve, engineered target error only'},{'check':'real CAE and MAIN byte review/public preflight dry-run','status':'PASS','evidence':rel(P/'main_preflight_dry_run.json'),'scope':'2 candidates, outside Plastic bytes identical; no solver syntax or convergence check'},{'check':'original integrity','status':'PASS','evidence':rel(P/'final_integrity.json'),'scope':'explicit original hashes/frozen package/history'},{'check':'physical sensitivity conclusion','status':'WARNING','evidence':rel(P/'REPORT.md'),'scope':'future response unknown; no physical bounds/validation'}],errors=[{'code':'TEST_LOADER_ENCODING_RESOLVED','severity':'INFO','message':'First test import used Windows default GBK and stopped; fixed to explicit UTF-8 and18 tests passed','evidence':rel(P/'test_attempt1_error.json'),'resolution':'local loader only; no original/environment changes'}])
 atomic(RUN/'run.json',run);save(RUN/'checkpoints/completed.json',{'at':now(),'run_json_sha256':sha(RUN/'run.json'),'report_sha256':sha(P/'REPORT.md'),'hub_receipt_sha256':sha(P/'hub_completion.json'),'new_solver_attempts':0,'new_queue_items':0,'stop_after_current_Run':True})
 print(json.dumps({'run':'run_051','status':run['status'],'jobs':[{'job':p['job_name'],'sha256':p['inp_sha256']} for p in prepared['points']],'tests':18,'preflight':2,'dry_run':2,'solver_attempts':0,'main_task_id':session['main_task_id']}))
if __name__=='__main__':main()
