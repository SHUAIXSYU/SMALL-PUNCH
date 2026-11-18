"""MAIN review of real ODB-agent results, spatial/energy evidence and next-study decision."""
from pathlib import Path
from datetime import datetime
import csv,json,hashlib,sys,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_050/artifacts/private';O=P/'odb';sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
session=read(P/'hub_session.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);task=hub.task(session['odb_task_id'])
assert task['execution_state']=='COMPLETED' and task['lease_agent']=='ODB:ODB-real-run050'
save(P/'odb_task_received_by_main.json',{'at':datetime.now().astimezone().isoformat(),'task':task,'transport':'formal Hub.task structured result plus real ODB Codex completion; no unrestricted inbox polling','independent_MAIN_rechecks':'reference coordinates/IP weights, volume thresholds, global RP work, direct energy and frozen-law work consistency'})
manifest=read(O/'manifest.json')
for v in manifest['files']:assert sha(R/v['path'])==v['sha256']
result=read(O/'spatial_energy_result.json');independent=read(P/'main_spatial_independent_check.json');energy=read(P/'main_global_energy_check.json');potential=read(P/'main_hardening_work_consistency.json')
checks=[];comparisons=[]
for point in result['points']:
 pid=point['point_id'];ip=next(v for v in independent['records'] if v['candidate_id']==pid);en=next(v for v in energy['records'] if v['candidate_id']==pid);po=next(v for v in potential['records'] if v['candidate_id']==pid)
 v2=read(O/pid/'energy_strain_stage_v2.json');assert v2['odb_sha256']==point['odb_sha256'] and v2['negative_delta_peeq_count']==0
 for stage in point['stages']:
  mm=stage['target_displacement_mm'];s=next(v for v in ip['stages'] if v['target_mm']==mm);e=next(v for v in en['stages'] if v['requested_displacement_mm']==mm);v=next(v for v in v2['stages'] if v['target_displacement_mm']==mm);p=next(v for v in po['stages'] if v['target_mm']==mm)
  assert abs(e['actual_displacement_mm']-stage['actual_displacement_mm'])<1e-12
  assert e['ALLPD_J']==v['ALLPD_direct_history_j']==stage['global_energy_history']['ALLPD']
  for th in s['thresholds']:
   q=stage['above_peeq_thresholds'][str(th['threshold'])]
   assert abs(q['reference_fraction']-th['whole_specimen_ref_fraction'])<1e-13 and abs(q['current_fraction']-th['whole_specimen_current_fraction'])<1e-13
  assert abs(math.fsum(v['strain_interval_cumulative_work_j'].values())-v['sum_intervals_j'])<1e-12
  assert abs(math.fsum(v['fraction_by_strain_interval'].values())-1)<1e-12
  assert abs(v['sum_intervals_j']-v['v1_reconstructed_reference_volume_j'])<1e-12
  comparisons.append({'candidate_id':pid,'target_mm':mm,'direct_ALLPD_J':v['ALLPD_direct_history_j'],'saved_frame_S_dPEEQ_estimate_J':v['sum_intervals_j'],'estimate_relative_difference_to_ALLPD':v['relative_difference_to_ALLPD'],'frozen_table_reference_work_index_J':p['model_implied_reference_work_J'],'model_index_relative_difference_to_saved_frame_estimate':p['model_implied_reference_work_J']/v['sum_intervals_j']-1,'post_p0p1_work_fraction_estimate':1-v['fraction_by_strain_interval']['p_0_to_0p1'],'post_p0p5_work_fraction_estimate':v['fraction_by_strain_interval']['p_above_0p5']})
  checks.append({'candidate_id':pid,'target_mm':mm,'threshold_volume_checks':3,'direct_global_energy_identity':'PASS','energy_interval_sum':'PASS','v1_v2_total_identity':'PASS'})
save(P/'main_review_checks.json',{'status':'PASS_SOFTWARE_AND_EVIDENCE_CHECKS_ONLY','ODB_manifest_hashes_verified':len(manifest['files']),'stage_checks':checks,'threshold_pairs_checked':24,'independent_quadrature_tests':read(P/'main_quadrature_verification.json')['checks'],'scientific_scope':'discrete spatial and reconstructed work evidence only; no physical/material/RF2-contribution validation'})
save(P/'main_energy_comparison.json',{'records':comparisons,'not_exact_local_dissipation':True,'not_RF2_contribution':True})
# Saved-IP visualizations only: no field smoothing or extrapolation.
fig,axes=plt.subplots(2,4,figsize=(16,6),sharex=True,sharey=True,layout='constrained')
for j,pid in enumerate(['D01','I08']):
 d=rows(O/pid/'spatial_ips.csv')
 for k,target in enumerate([.3,.6,.9,1.2]):
  a=[v for v in d if float(v['target_displacement_mm'])==target];ax=axes[j,k]
  sc=ax.scatter([float(v['r_ref_m'])*1000 for v in a],[float(v['z_ref_m'])*1000 for v in a],c=[float(v['PEEQ']) for v in a],s=7,vmin=0,vmax=.7,cmap='viridis')
  ax.axvspan(2,2.2,color='grey',alpha=.13);ax.axvline(2,color='grey',ls='--',lw=.7);ax.set(xlim=(0,2.2),ylim=(0,.5),title=f'{pid}, nearest saved {target:g} mm')
  if j==1:ax.set_xlabel('Reference radius (mm)')
  if k==0:ax.set_ylabel('Reference thickness (mm)')
fig.colorbar(sc,ax=axes.ravel().tolist(),label='Saved IP PEEQ; reference coordinates');fig.savefig(P/'peeq_four_stage_comparison.png',dpi=175);plt.close(fig)
decision={'version':'run050-post-spatial-research-decision-v1','current_new_FE_authorization':0,'immediate_priority':'traceable high-strain hardening/strain-processing evidence; no fitting or model change now','mechanism_priority':'high-plastic-strain constitutive continuation is worth a controlled sensitivity test, based on substantial spatial/work involvement; causal dominance not established','minimum_next_FE_proposal':{'jobs':2,'type':'one frozen D01 baseline, two independently frozen upper/lower high-p continuation scenarios','status':'DESIGN_ONLY_NOT_READY_NO_NEW_INP','purpose':'test high-p continuation influence with geometry/mesh/clamp/contact/low-p table unchanged; old D01 baseline reused','requirements':['separate user authorization and unique model/numerical contract','transition p0 and envelope amplitude fixed before FE based on traceable high-strain evidence or explicitly labeled engineering scenario assumptions, not tuned to SPT Loss or released tensile fit','p0~.1 may serve as diagnostic design coordinate only, not a universal validated cutoff','monotone nonnegative hardening, transition continuity and sufficient p coverage; identical displacement/output/Loss contracts','do not replace original D01/I08 or claim the new envelope is a physical confidence bound'],'expected_outcome':'diagnostic response change only; not a newly identified material law'},'boundary_alternative':{'jobs':2,'readiness':'NOT_READY_WITHOUT_MEASURED_FIXTURE_INPUTS','design_reference':'run/run_050/artifacts/private/boundary_research_design.json','priority':'later or parallel records acquisition; no evidence yet to select preload/friction/compliance; high-p not localized in fixed ring does not prove clamp irrelevant'},'parameter_identification_points':'defer; unchanged model-error mechanisms cannot be resolved by merely adding lower-Loss samples','not_automatic_total_budget':'two material scenarios and two boundary scenarios are alternatives/stages, not an authorized four-job batch','stops':['do not generate concrete inputs until transition/envelope or fixture inputs are traceable and predeclared','datacheck/full failure or uncertain input/output identity','fixed FD window noncoverage or actual table coverage exceeded','unexplained accepted-state contact/strain instability or unstable preload','new-model numerical variation not separable from response changes','no automatic retry, extra sample, parameter fit, or continuation to BO/DE'],'data_role':'any released tensile evidence informing model development is development information, not a fresh independent holdout; formal run048 status and historical exposure remain unchanged'}
save(P/'next_step_decision.json',decision)
lines=['# run_050 — 高塑性应变空间、能量与本构外推定向研究','\n**WARNING / EXISTING_ODB_SPATIAL_ENERGY_REVIEW_COMPLETE。** 真实ODB会话经AgentHub领取任务，MAIN独立复核。仅只读已有精化D01/I08，不生成新INP、不求解/Datacheck/入队、不拟合或优化；run046预测及run047/048历史不改，正式独立验证仍为NOT_EVALUABLE。',
'\n## 来源与方法','\n使用run043精化D01/I08的真实完成ODB，队列ID与INP/ODB完整hash见odb/admission.json和spatial_energy_result.json。每项594个CAX4、2376积分点，四个目标位移取最近已保存接受帧，无场插值；实际目标误差小于0.001mm。',
'\nCAX4全积分2×2、实际IP编号1(-,-)、2(+,-)、3(-,+)、4(+,+)。参考权重V0=2πr0 detJ0 wξwη，当前权重V=2πr detJ wξwη，由X+U重建。没有IVOL，均标为几何重建。MAIN以实际INP独立校验IP位置、参考权重和解析圆片体积；参考总体积约3.9269908e-8 m³。分数由IP处阈值分类加权，属于积分近似，不是精确等值面或截面积。主分母含整片固定外环，r<2mm另报，不能混用。',
'\n## 四阶段空间变化','\n| 候选 | 目标mm | 实际mm | max PEEQ | >.1整片参考体积% | >.3% | >.5% |', '|---|---:|---:|---:|---:|---:|---:|']
for point in result['points']:
 for s in point['stages']:
  fs=s['above_peeq_thresholds'];lines.append(f"| {point['point_id']} | {s['target_displacement_mm']:.1f} | {s['actual_displacement_mm']:.7f} | {s['max_peeq']['value']:.6f} | {100*fs['0.1']['reference_fraction']:.4f} | {100*fs['0.3']['reference_fraction']:.4f} | {100*fs['0.5']['reference_fraction']:.4f} |")
lines += ['\n终态>.1整片参考分数D01/I08为13.2493%/12.6274%，对应当前体积分数13.2653%/12.6426%。支撑孔内r<2mm的条件分数则为82.8082%/78.9212%；该区域只占整片初始体积16%，不能把13%称为全试样广泛，也不能把它称为单点异常。',
'\n高于.1的积分点均在参考r<2mm。>.3约81.5%–81.6%的高值体积落在球头半径1.25mm的几何投影内；>.5约89.6%/92.0%在该投影内，且65.2%/52.8%位于参考厚度下四分之一。另有靠近r≈1.92mm的高值，显示支撑孔边邻域也参与。这里是几何分区，不等同于已分解膜拉伸/弯曲/接触力学机制；球头几何投影也不等于实际活动接触面。固定外环本身未出现>.1，不足以排除其对整个解的边界影响。',
'\n## 接触证据','\n0.3mm附近两项正CPRESS均为9节点，活动压力近似环带，参考半径约.345–.593mm；随压入向中心及外侧扩展，终态均43个正压节点、参考最大半径约1.251mm。终态最大CPRESS为D01 642.326MPa、I08 825.090MPa，近似足迹相似不代表接触压力分布相同。COPEN有哨兵缺失值，保留为缺失，不解释为巨大穿透；压力正值只是活动接触代理。现有场只能给空间相关证据，不能确定唯一接触成因。',
'\n## 能量：直接历史、重构估计和区间归属','\n直接保存的终态ALLPD为D01 .81820744J、I08 .88187772J；ALLWK为.83997852/.90539038J。MAIN以原始RP反力–位移梯形积分独立复核，外功相对差约6.2e-8/1.05e-7。塑性耗散约占外功97.4%，不等同RF2的空间份额。保存ETOTAL很小，但已选ALLIE+ALLFD−ALLWK并不等于完整ETOTAL，不能遗漏其他项后宣称完整平衡。',
'\nODB未保存PENER/局部耗散。ODB Agent用全保存帧实际S.Mises、ΔPEEQ和固定参考IP权重作离散J2塑性功估计。终态.81725712/.88089091J，较直接ALLPD低.1161%/.1119%。这是带参考体积/时间离散假设的近似，不是直接局部能量；总体吻合也不证明任意空间分区完全准确。MAIN另以冻结材料表∫σy(p)dp V0作模型内一致性指标，对比已记录在main_energy_comparison.json，不替代实际S历史。',
'\n两种归属分别保存：v1按某帧PEEQ区域汇总该材料点的全部累计功；v2将保存帧间跨阈值的Δp按q(p)线性假设拆分，汇总功实际发生时所处p区间。后者不是终态区域的全部既往耗散。',
'\n| 候选 | p≤.1功份额% | .1–.3% | .3–.5% | >.5% | 与直接ALLPD差% |','|---|---:|---:|---:|---:|---:|']
for point in result['points']:
 v=point['energy_strain_stage_v2']['stages'][-1];f=v['fraction_by_strain_interval'];lines.append(f"| {point['point_id']} | {100*f['p_0_to_0p1']:.4f} | {100*f['p_0p1_to_0p3']:.4f} | {100*f['p_0p3_to_0p5']:.4f} | {100*f['p_above_0p5']:.4f} | {100*v['relative_difference_to_ALLPD']:.4f} |")
lines += ['\n约70.98%/69.26%的重构塑性功发生在p>.1；极端p>.5部分只有约1.74%/2.72%。因此应重点考察广泛的.1–.5硬化区，而不是只追逐maxPEEQ≈.6的少数位置。**这些是耗散估计份额，不是Punch RF2贡献，也不是冻结Loss对该区材料参数的导数。** 没有虚功或受控材料敏感性计算，不能定量分解载荷贡献。',
'\n## 外推风险与冻结材料比较','\n拉伸来源方仅确认真总应变≤.10均匀，精确对数总应变转换等门控仍未独立核实。PEEQ是多轴累积等效塑性历史，不能把ε_true,total=.10无条件等同PEEQ=.10。在特定单轴/E210与应力定义假设下，.10−σ/E≈.09719仅为条件性参考标记，不是全材料、全加载路径的实验有效边界。',
'\n冻结两份材料表到p=.9，真实maxPEEQ=.61146/.65374均在表内，数学表覆盖与物理可信度分开判定。冻结表在p=.1时D01/I08应力为476.63/522.35MPa，在p=.3为612.62/617.33MPa，在p=.5反向为688.28/667.66MPa。曲线在高耗散区接近并换序，支持研究应变加权的参数补偿，但不能证明连续谷地或唯一成因。不得据此重新拟合参数或替换冻结预测。',
'\n## 边界对照的可行性','\n实际理想模型在r≈2–5mm上下环带固定U1/U2，与来源方4mm支撑孔和外圈压紧的大体几何描述相容；并未验证与真实预紧力夹具接触等效。最小边界方案仍是D01/I08各一个同名义有限夹紧接触的固定材料对照，复用旧两项作为控制，仅新增两项。但当前缺上下夹具实际表面/圆角、预紧力或扭矩–力校准、夹具界面摩擦/润滑及顺应性/零点记录，故**尚不具备具体输入生成/求解授权条件**。不得凭冲头μ=.1推定夹具μ，也不为改善Loss选夹紧力。',
'\n## 科研优先级与最小未来预算','\n新空间/耗散证据使“高塑性应变延拓的受控敏感性”比单纯追加识别点更有直接依据，但尚不能判定它是单轴偏差的主因。先零FE补齐原始应变处理和较大塑性区的独立材料依据；不把普通颈缩后工程转真曲线当均匀本构。',
'\n若下一步单独申请FE，建议最多2项：以同一冻结D01解为控制，只改变高p延拓的上下工程/物理包络，保持几何/网格/夹持/接触、低p表、数值和Loss不变。转接点与幅度须在生成输入前由可追溯依据或明确声明的工程假设冻结，不能按Loss调节，也不把工程包络当物理置信区间；本轮不选新数值、不给新材料参数、不生成输入。若不能合理定义包络，先补实验而非任意改表。该提案是未来模型误差敏感性，不是当前修改材料或优化。',
'\n边界资料齐备后，前述2项边界对照可作为另一阶段/替代方案；不能自动视为已授权4项批次。原4识别点和BO/DE继续暂停。新接触/新延拓的数值资格须逐案检查，旧点级通过不能平移成整个模型域PASS。',
'\n停止条件：包络/夹具资料未冻结不生成输入；身份不明、Datacheck/Full失败、窗口不覆盖、实际材料表越界、未解释接受态严重应变/接触异常或数值变化无法与目标效应分离时停止。不得自动重试、补点或消耗额外预算。未来科学比较仍用同一固定窗口/单位/符号，不根据效果修改评分。',
'\n## 历史、隐私与结论边界','\nrun039/042稀疏评价和数值不评分记录、run045两个点的相邻增量资格、run048正式NOT_EVALUABLE、run049假设分类均保留。历史run015信息暴露不抹除；本Run没有重读原始拉伸OPJU或封存旧分析。已解盲信息对未来模型开发的作用必须披露，并需另留未使用资料验证新模型。',
'\n真实空间/数值事实：IP字段、加权体积、直接全局历史；近似证据：参考体积离散塑性功及其分区；待检机制：高p外推、夹持与材料补偿；未来计划：两项延拓或条件式两项边界对照。四类不得混称。',
'\n完整来源：odb/manifest.json、odb/provenance.json；MAIN复核：main_review_checks.json、main_spatial_independent_check.json、main_global_energy_check.json、main_energy_comparison.json；图：peeq_four_stage_comparison.png及odb/peeq_maps_1p2mm.png。',
'\n变量定义参考[SIMULIA积分点输出](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEOUTRefMap/simaout-c-std-elementintegrationpointvariables.htm)和[全模型能量](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEOUTRefMap/simaout-c-std-wholeandpartialmodelvariables.htm)。公开文档为2025版，仅作定义参考；实际文件、单元和字段以本机2024 ODB为准。']
with (P/'scientific_report.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
print(json.dumps({'ODB_manifest_files_checked':len(manifest['files']),'stages_checked':len(checks),'threshold_pairs_checked':24,'report_sha256':sha(P/'scientific_report.md'),'recommended_next_new_FE':2,'authorized_new_FE':0}))
