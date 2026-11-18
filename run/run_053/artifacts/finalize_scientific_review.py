"""Finalize existing results only. No solver, queue writer, or optimizer imported."""
from pathlib import Path
import json,csv,sys,hashlib,subprocess
from datetime import datetime
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_053';A=RUN/'artifacts';P=A/'private';M=P/'main'
sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,obj):
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def write(p,s):
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
def rel(p):return p.relative_to(R).as_posix()
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def main():
 now=datetime.now().astimezone().isoformat();metrics=read(M/'response_metrics.json');audit=read(P/'execution_audit.json');ids=read(P/'task_ids.json')
 with (M/'spatial_energy_summary.csv').open(encoding='utf-8-sig',newline='') as f:energy=list(csv.DictReader(f))
 terminal={r['candidate_id']:r for r in energy if float(r['target_mm'])==1.2}
 records=metrics['records'];assert len(records)==3 and all(r['scoreability']=='SCOREABLE_EXPLORATORY' for r in records)
 assert audit['software_completed_count']==2 and audit['consumed_started_attempts']==2 and audit['extra_batch_jobs']==0
 tests=read(P/'synthetic_tests.json');assert tests['returncode']==0
 protected=read(P/'protected_before.json');assert all(sha(R/name)==s for name,s in protected.items())
 sourcechecks=[]
 for r in audit['records']:
  assert sha(R/r['inp_path'])==r['inp_sha256']
  for kind,source in r['files'].items():
   actual=sha(R/source['path']);assert actual==source['sha256'];sourcechecks.append({'candidate':r['candidate_id'],'kind':kind,'path':source['path'],'sha256':actual,'unchanged':True})
 project=R/'agenthub_sp_invopt/abqjobpilot_project'
 assert all(sha(project/name)==s for name,s in audit['protected_before'].items())
 table=[]
 for r in records:
  e=terminal[r['candidate_id']]
  table.append({'candidate':r['candidate_id'],'job':r['job_name'],'software_status':'COMPLETED_WITH_WARNINGS','numerical_quality':'EXPLORATORY_REVIEWED_WITH_WARNINGS','scoreability':r['scoreability'],'loss':r['loss'],'RMSE_to_experiment_N':r['RMSE_to_experiment_N'],'NRMSE_to_experiment':r['NRMSE_to_experiment'],'FD_RMSE_vs_D01_N':r['RMSE_vs_D01_N'],'max_force_difference_vs_D01_N':r['max_abs_force_difference_N'],'max_regularized_relative_difference':r['max_regularized_relative_difference'],'deltaLoss_vs_D01':r['loss']-metrics['baseline_loss'],'PEEQ_max':r['max_saved_peeq'],'ALLPD_J':float(e['ALLPD_J']),'cutbacks':r['cutback'],'runtime_s':r['runtime_s']})
 with (M/'comparison_table.csv').open('x',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 decision={'version':'run053-scientific-review-v1','at':now,'status':'WARNING','completed_existing_jobs':2,'exploratory_scoreable_jobs':2,'qualification':'reviewed for intentional material sensitivity; not asymptotic convergence or physical validation','model_loss_contract':'run017-exploratory-fd-v1','reference':'refined D01, run045, maximum increment .00125','main_scientific_conclusion':'High-plastic-strain hardening continuation strongly affects computed SPT response within the fixed low-strain model; both artificial endpoints worsen experimental Loss. This is not a material calibration or proof of unique error source.','confounding':'Evidence supports investigating high-strain continuation versus low-strain parameter compensation; does not establish a continuous nonunique valley.','numerical_limitations':['H01 accepted-frame force step 8.131714N near1.154738mm coincides with node23 pressure build; no local cutback or serious accepted warning; COPEN sentinel prevents closure proof','D01 historical Runner process evidence remains previously unconfirmed; frozen ODB/INP/FD and prior qualification are verified, not retrospectively upgraded','D01 adjacent increment differences are not H01/H02 numerical-error bounds','all estimated local plastic work uses saved frames and reference IP volume; no RF2 contribution decomposition'],'next_priority':'Traceable high-strain material constraints and model-form/identifiability design before further fitting; obtain fixture geometry and clamping evidence in parallel','immediate_new_FE_budget':0,'conditional_future_FE_budget':'At most2 fixed-material boundary contrasts only after measured fixture/clamping inputs and separate preparation and explicit authorization; no invented preload/friction/compliance','new_attempts_this_run':0,'authorized_attempts_previous_batch':2,'started_attempts_consumed':2,'remaining_batch_attempts':0,'retries':0,'new_queue_records':0,'preserved_history':['run025 BLOCKED','run046 frozen predictions','run047/run048 formal NOT_EVALUABLE','run015 historical information exposure'],'no_new_tensile_reading_or_fitting':True,'source_files_unchanged':sourcechecks,'protected_history_unchanged':protected,'table':table}
 save(P/'scientific_decision.json',decision)
 lines=['# run_053 — 高应变硬化敏感性：真实求解后分析','',f'完成时间：{now}。状态：**WARNING / TWO_EXISTING_RESULTS_ANALYSED**。','',
 '## 结论与适用范围','',
 '两项均单次 Datacheck 成功后单次 Full 成功，软件终态 COMPLETED_WITH_WARNINGS；真实 ODB Agent 已完成只读提取，MAIN 独立复核后两项可按冻结探索性目标评分。只改高应变延续即产生约48 N的全窗响应RMSE、约121 N最大差；中后段影响明显。两种人工包络均使SPT Loss增大。结果支持高应变硬化外推是重要敏感因素，也支持研究它与原sigma_y/n反演的混淆，但不证明唯一误差来源、连续非唯一谷地或材料真实上下界。','',
 '## 执行与证据身份','',
 f'Project ID：{audit["project_id"]}。冻结输入 run051；run052授权已消耗2/2，本分析新增求解、入队、重试均0。14 CPU、0 GPU；现行 AbqJobPilot公开API读取 Queue/History/status/outputs。Runner CLEAN、owner ABSENT、无活动Solver；原Queue/Settings/Project DB字节哈希在本轮读操作前后相同。',
 'H01：q_02e7827a5c2d41aba1781ec0f36e78a4；258s（DC日志35s、Full222s）。H02：q_5a027a0d764148c08f4d7be36049439f；254s（DC30s、Full224s）。总队列耗时512s，按14核分配约1.991核小时，不代表实测CPU利用率。两项launcher/lineage/solver_candidate身份均为VERIFIED，单次记录、返回码0、STA成功终态、ODB诊断完成一致，无额外本批Job。',
 'H01 INP SHA-256：da074a4591c429a572cf8f5844bef844674f464fc13a52014fe5977250c33cf8。H02：f0cebe1bc9242c9d26991a91671f797933e66d052376846f21f7ed0894fd053f。各ODB及STA/MSG/DAT/LOG完整哈希见 execution_audit.json 与 evidence_manifest.json。',
 '真实角色交接沿用run052创建的依赖任务，正式MAIN消息只将新产物输出根定为run053；真实ODB会话领取并完成两项，未模拟worker。任务ID及消息引用见task_ids.json、Hub收据。科学复核任务01081db2-509a-42bc-856e-d0f1cbd52962。数据库写消息不等同自动唤醒或对方已读。','',
 '## 独立复核与冻结评分','',
 'RP为ASM_SPT节点1、SET_PUNCH_RP，Step_Punch_Displacement。三模型各805个History/保存帧，位移网格逐点完全一致；u=-U2、F=-RF2，m/N。两新模型逐点Field/History误差0，终态1.200000057mm，完整覆盖0–1.2mm。241实验位移点、F_ref1428.9N、等权归一化MSE、线性插值，无平滑、删点、外推、零点移动或窗口改变。手算、冻结实现与真实ODB Agent结果一致。',
 '只使用run045精化D01；其805点FD哈希0b971b61dacff22d162ea111828edbc7020689e17bc83d4c0a07518ceded2d24、ODB哈希f857629c1f4d06e30e2019fca91cb0c96fc91f1ebc8f68a2740ca7bdcd239472，重新计算Loss为0.0005020002745645833。该参考此前的HISTORICAL_RUNNER_PROCESS_EVIDENCE_UNCONFIRMED提示仍保留，不追溯升级其旧过程证据。',
 '软件完成、可读、已数值审核与科学可评分分别记录；本次为探索性可评分，不宣告H01/H02独立增量收敛、网格收敛、夹具等效或物理验证。','',
 '|模型|Loss|对实验RMSE/N|对D01 RMSE/N|最大载荷差/N|最大正则相对差|最大PEEQ|ALLPD/J|耗时/s|',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in table:lines.append(f'|{r["candidate"]}|{r["loss"]:.12g}|{r["RMSE_to_experiment_N"]:.6f}|{r["FD_RMSE_vs_D01_N"]:.6f}|{r["max_force_difference_vs_D01_N"]:.6f}|{100*r["max_regularized_relative_difference"]:.4f}%|{r["PEEQ_max"]:.7f}|{r["ALLPD_J"]:.8f}|{r["runtime_s"]}|')
 lines += ['', 'H01 ΔLoss=+0.001939496620687（+386.35%）；H02=+0.000271701183678（+54.12%）。最大差位置分别1.200、1.175mm。Loss不是平均百分比误差。D01仅是此三组最低者，不代表真实本构。','',
 '## 分段与对称性','',
 '|位移/mm|H01对D01 RMSE/N|H02对D01 RMSE/N|','|---|---:|---:|']
 for b,c in zip(records[1]['bands'],records[2]['bands']):lines.append(f'|{b["range_mm"][0]:g}–{b["range_mm"][1]:g}|{b["RMSE_vs_D01_N"]:.6f}|{c["RMSE_vs_D01_N"]:.6f}|')
 lines += ['',
 '分段不重复端点：前三段各60点、末段61点，分段Loss贡献相加等于全窗Loss，详见band_sensitivity.csv。局部IP最早约0.04924mm超过p_switch，但宏观差初期很小；固定7.1445N工程变化标记分别在0.390/0.405mm首次超过，不能将其当统计显著性检验。',
 '中后段通常H01<D01<H02；早期0.05–0.295mm存在14个很小的H02<H01网格点，最大反序0.799N，不能声称全程严格排序。每条实际曲线本身均单调，无负向载荷回退。两扰动大体反向，但并非严格对称：中点响应RMSE5.81483N，反对称性缺陷范数比0.121428。',
 '相对于D01已有相邻时间增量细化，响应RMSE约143/140倍，最大差约67/67倍。它们是已观察量级比较，不是显著性证明，也不是H模型误差上界。','',
 '## 数值与接触诊断','',
 '每项804个接受增量、1次被拒试算/1个cutback，集中初始增量。接受/拒绝各见一次ZERO MOMENT提示；无接受状态负特征值、畸变或大应变增量警告。DAT共同提示：解析刚面不适用PATH BASED TRACKING，实际改用STATE BASED TRACKING；这是原模型共同设置诊断，不能因此声称接触已物理验证。',
 'H01在1.1547375mm出现8.131714N原始接受帧载荷增量，与节点23CPRESS从约72.36→173.76→264.30MPa建立过程相邻；这些帧已接受、无该处cutback或严重警告。节点23首次正CPRESS位置：D01约1.17874mm、H01约1.15324mm，H02至1.2mm未出现。H01局部42/43个正压节点变化，最大增量附近已为43；不能将最大跃变简单归为同一帧新增节点。COPEN无效哨兵保留缺失，不能据此证明间隙闭合、穿透或唯一机制。',
 '这给出非线性接触压力演化的相关证据；宽段差在0.6–0.9mm已达34–36N，因此响应不只来自末段单个突跳。H模型未单独完成进一步增量细化，精细排序与校准仍有数值不确定性。','',
 '## 空间与塑性功：两种定义分开','',
 '三模型按相同594个CAX4、2376积分点和四阶段最近接受帧分析；MAIN从实际INP坐标、四Gauss点映射重算2πr detJ参考体积，核对36项阈值体积统计。全试样参考体积分母约3.92699e-8m³，绝非二维面积；高应变IP集中在参考半径2mm以内。各阶段数值、实际帧位移及空间CSV见下列证据。','',
 '|模型|V(PEEQ>.1)|V(>.3)|V(>.5)|超过.1后增量功占比|超过.5后增量功占比|终态>.1区域累计功占比|',
 '|---|---:|---:|---:|---:|---:|---:|']
 for r in table:
  e=terminal[r['candidate']];lines.append('|'+r['candidate']+'|'+ '|'.join(f'{100*float(e[k]):.4f}%' for k in ['volume_ref_fraction_gt_0.1','volume_ref_fraction_gt_0.3','volume_ref_fraction_gt_0.5','estimated_work_after_p0p1_fraction','estimated_work_after_p0p5_fraction','terminal_region_work_fraction_gt_0.1'])+'|')
 lines += ['',
 '低硬化使极高应变更集中（>.5体积1.472% vs1.173%），高硬化扩大>.1体积却减小>.5体积；不同阈值不是同方向变化。全部最大PEEQ低于材料表上限.9。ALLPD随H01/D01/H02为.78131/.81821/.85421J。',
 '“超过阈值以后发生的增量功”按每IP相邻保存帧PEEQ区间切分、S.Mises对PEEQ线性变化的梯形积分×参考体积估计；“终态高PEEQ区域累计功”是该终态区域之前所有功的另一分类。H的actual-switch额外bin合并成共同0–.1/.1–.3/.3–.5/>.5再比较；D01的70.98%属于前一定义，不是终态区域累计95.84%。',
 '重构总功与直接ALLPD差约−.102%至−.129%，可作一致性支持，不能当精确局部能量误差界。依赖保存帧、区间内线性及参考体积近似，未将当前体积或局部PENER补造成精确积分。RP∫Fdu与ALLWK基本一致，但不能由选取的能量项宣告全量平衡闭合。两种塑性功口径都不是Punch RF2贡献比例。','',
 '## 后续科研决定','',
 '优先补足可追溯的高塑性应变硬化约束并研究模型形式/参数补偿，暂停为原两参数模型继续盲目优化。需要大应变局部测量及适当颈缩处理；常规工程应力应变转真值不能无条件延至颈缩后。低段保持而SPT响应改变，已充分支持这项机制值得研究；仍不能排除夹具、摩擦、模型形式或其他测量误差。',
 '最小即时新增FE预算：0。先冻结本次包络敏感性证据并补材料/夹具记录。实测夹具尺寸、预紧或接触方式及合理摩擦资料具备后，可另行准备最多2个固定材料的物理可解释夹具对照；缺资料时不虚构预紧/摩擦/顺应性。若未来要对H模型做精细Loss排名，应另外提出点级数值验证与授权，不能把D01细化误差直接搬作其误差界。',
 'run046预测、run025 BLOCKED及run047/run048正式NOT_EVALUABLE历史均保留；本轮未读取拉伸原始数据或按其重拟合。run015历史信息暴露事实保留，不能称完全无泄漏盲测。未来若用已解盲数据开发材料模型，应计为开发/校准数据，不能再次作为新独立验证集。','',
 '## 图件与结构化证据','',
 '- main/material_three_models.png：冻结材料表；main/three_model_FD.png：真实FE与固定目标。',
 '- main/force_difference_vs_D01.png；experimental_residuals.png；loss_comparison.png。',
 '- main/reference_volume_fraction_comparison.png；plastic_work_comparison.png。',
 '- main/comparison_table.csv；response_metrics.json；aligned_241_three_models.csv；band_sensitivity.csv。',
 '- execution_audit.json：公开API、单次阶段及源文件哈希；main_numeric_event_audit.json：MAIN自己的接受/拒绝事件解析。',
 '- odb/manifest.json、每项result.json/raw_history.csv/force_displacement.csv/odb_extraction.json及空间、接触、功CSV：真实ODB会话产物。',
 '- main/independent_fd_checks.json、spatial_energy_independent_review.json、contact_and_ordering_context.json、H01_contact_pressure_build_review.json：MAIN独立数值复核。',
 '- scientific_decision.json、evidence_manifest.json、AgentHub收据：结论、哈希、正式交接。',
 '- 5项合成记账测试通过，覆盖零差、常偏差与分段积分、拒绝评分NULL、对称扰动及零扰动不可定义情况；未将合成数据作真实结果。','',
 '所有可恢复实验数据/曲线/科学明细保存在Git忽略私有目录。完成本次只读分析后停止，无新入队、Solver、Datacheck、重试、拟合、优化或Git提交。','']
 report=P/'scientific_report.md';write(report,'\n'.join(lines))
 evidence=[]
 for path in sorted(P.rglob('*')):
  if path.is_file() and path.name not in ['audit_lease.json','science_lease.json','task_ids.json']:
   evidence.append({'path':rel(path),'bytes':path.stat().st_size,'sha256':sha(path),'visibility':'GIT_IGNORED_PRIVATE'})
 em=P/'evidence_manifest.json';save(em,{'version':'run053-pre-handoff-evidence-v1','at':now,'files':evidence,'excluded':'self; private identity/leases; later Hub receipts and closeout checkpoint'})
 hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=ids['identity'];tid=ids['science_task_id']
 for oid in ids['odb_task_ids'].values():assert hub.task(oid)['execution_state']=='COMPLETED'
 assert hub.task(tid)['execution_state']=='PENDING';lease=hub.claim(tid,actor,'run053-main-scientific-review-v1');save(P/'science_lease.json',lease)
 artifacts=[]
 for path in [report,P/'scientific_decision.json',em,M/'comparison_table.csv',M/'response_metrics.json',M/'independent_fd_checks.json',M/'spatial_energy_independent_review.json',M/'H01_contact_pressure_build_review.json',M/'three_model_FD.png',M/'force_difference_vs_D01.png',M/'plastic_work_comparison.png']:
  artifacts.append(hub.artifact(tid,actor['agent_id'],path,{'run':'run_053','scope':'MAIN independent review of real ODB-session outputs; no new FE','ODB_tasks':ids['odb_task_ids']},version='run053-v1'))
 result={'output_run':'run_053','report_path':rel(report),'report_sha256':sha(report),'evidence_manifest':rel(em),'evidence_sha256':sha(em),'scientific_state':'WARNING','software_completed':2,'scoreable':2,'new_attempts':0,'started_budget_consumed':2,'remaining':0,'loss':{r['candidate']:r['loss'] for r in table},'priority':decision['next_priority'],'immediate_new_FE_budget':0,'limits':decision['numerical_limitations']}
 hub.message(tid,actor['agent_id'],'MAIN',result,'run053-complete-science-main-handoff-v1');hub.finish(lease,result,evidence_state='RECORDED',science_state='WARNING')
 for cid,oid in ids['odb_task_ids'].items():hub.message(oid,actor['agent_id'],'ODB',{'status':'MAIN_REVIEW_COMPLETE','report_path':rel(report),'report_sha256':sha(report),'scope':'exploratory scoreable with local contact and historical-process limitations; no new solve'},f'run053-main-review-ack-{cid}-v1')
 save(P/'agenthub_completion_receipt.json',{'at':now,'artifact_receipts':artifacts,'science_task':hub.task(tid),'ODB_execution_states':{k:hub.task(v)['execution_state'] for k,v in ids['odb_task_ids'].items()},'message_delivery_note':'persistent messages recorded; no assertion MAIN/ODB automatically woke or read them'})
 write(RUN/'summary.md','# run_053 — H01/H02真实结果与高应变硬化敏感性\n\n**WARNING / TWO_EXISTING_RESULTS_ANALYSED。** 两项既有授权计算的软件终态、真实ODB提取及MAIN独立复核完成，可按冻结探索性Loss评分；完整数字、实验曲线、空间/能量及局部接触限制见[私有科学报告](artifacts/private/scientific_report.md)，哈希见[证据清单](artifacts/private/evidence_manifest.json)。\n\n高应变延续是当前模型的重要敏感因素；不据此证明真实材料、唯一误差来源或全域收敛。优先补高应变材料与夹具输入证据；当前不新增计算预算。run046预测及独立验证历史保持不变，run015历史信息暴露保留。\n\n真实ODB任务经AgentHub完成，MAIN科学审核已登记WARNING。原两次授权已消耗；本轮新增Solver、Datacheck、入队、重试、拟合、优化及Git提交均0。完成后停止。\n')
 idx=R/'run/README.md';s=idx.read_text(encoding='utf-8-sig');assert '## run_053' not in s;idx.write_text(s+'\n\n## run_053 — H01/H02求解后高应变硬化敏感性\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_053 | 两项真实执行审计、ODB提取、MAIN独立Loss/空间能量复核 | WARNING / TWO_EXISTING_RESULTS_ANALYSED | [summary](run_053/summary.md) |\n\n科学明细留私有区，原两次尝试已消耗，本轮无新求解、入队、拟合或优化，完成后停止。\n',encoding='utf-8')
 status=R/'status/PROJECT_STATUS.md';s=status.read_text(encoding='utf-8-sig');assert 'run_053' not in s
 prefix='# SMALL-PUNCH 项目状态\n';assert s.startswith(prefix)
 block='\n## 当前状态 — run_053（'+now[:10]+'，Asia/Shanghai）\n\n**WARNING / TWO_EXISTING_RESULTS_ANALYSED。** 两项既有授权计算经公开API确认单次完成，真实ODB会话已提取，MAIN独立完成冻结Loss、空间体积/塑性功与局部接触复核。结论及数值限制见[run_053私有科学报告](../run/run_053/artifacts/private/scientific_report.md)。原两次预算已消耗；本轮无新增求解、Datacheck、入队、重试或优化。保留run046冻结、正式NOT_EVALUABLE及信息暴露历史，当前停止等待科研决策。\n\n'
 status.write_text(prefix+block+s[len(prefix):],encoding='utf-8')
 outmanifest=A/'manifest.json';save(outmanifest,{'run':'run_053','report_path':rel(report),'report_sha256':sha(report),'private_evidence_manifest':rel(em),'private_evidence_sha256':sha(em),'analysis_code':[{'path':rel(f),'sha256':sha(f)} for f in sorted(A.glob('*.py'))],'no_large_source_models_copied':True})
 rr=read(RUN/'run.json');rr.update(status='WARNING',end_time=datetime.now().astimezone().isoformat(),outcome='TWO_EXISTING_RESULTS_ANALYSED',inputs=[{'path':'run/run_051/artifacts/prepared_batch.json','sha256':sha(R/'run/run_051/artifacts/prepared_batch.json')},{'path':'run/run_051/artifacts/comparison_contract.json','sha256':sha(R/'run/run_051/artifacts/comparison_contract.json')}],outputs=[{'path':rel(report),'sha256':sha(report),'visibility':'PRIVATE'},{'path':rel(em),'sha256':sha(em),'visibility':'PRIVATE'},{'path':rel(outmanifest),'sha256':sha(outmanifest)}],validation=['2 actual completed single attempts; public API identity and phase/STA/ODB checks','real ODB session completed2 formal tasks; MAIN independent signs/units/RP/history/field/PEEQ/hash and Loss review','77 ODB evidence hashes and36 independent axisymmetric threshold volume checks','5 synthetic comparison-bookkeeping tests passed','original inputs/results/project files/protected historical evidence unchanged'],limitations=decision['numerical_limitations'],agenthub={'science_task_id':tid,'ODB_task_ids':ids['odb_task_ids']},new_FE_attempts=0,new_queue_records=0,retries=0)
 (RUN/'run.json').write_text(json.dumps(rr,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 privatefiles=[str(f) for f in P.rglob('*') if f.is_file()]
 for f in privatefiles:assert subprocess.run(['git','check-ignore','--quiet','--',f],cwd=R).returncode==0,f
 assert not list(RUN.rglob('*.inp')) and not list(RUN.rglob('*.odb'))
 assert all(sha(R/name)==s for name,s in protected.items())
 save(RUN/'checkpoints/completed.json',{'at':datetime.now().astimezone().isoformat(),'git_branch':git('branch','--show-current'),'git_head':git('rev-parse','HEAD'),'git_working_tree':git('status','--short'),'report_sha256':sha(report),'private_files_ignored':len(privatefiles),'protected_history_unchanged':True,'source_files_unchanged':True,'AgentHub_science':hub.task(tid)['execution_state'],'stop':'no additional work or new FE authorized'})
 print(json.dumps({'report_path':str(report),'report_sha256':sha(report),'Hub_science':hub.task(tid)['execution_state'],'private_files_ignored':len(privatefiles),'status':'WARNING_COMPLETE'}))
if __name__=='__main__':main()
