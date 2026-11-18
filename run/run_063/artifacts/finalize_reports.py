"""Scientific reports, bounded preservation checks, and formal AgentHub closeout."""
from common63 import *
import numpy as np,math
from agenthub_sp_invopt.hub import Hub

def main():
 direction=read(P/'direction_analysis.json');view=read(P/'view_SVD_comparison.json')['views'];bands=read(P/'band_SVD_analysis.json')['bands'];features=rows(P/'feature_direction_responses.csv');scenarios=rows(P/'scenario_parameter_sensitivity.csv');data=read(P/'verified_local_data.json');source=read(P/'source_manifest.json');start=read(RUN/'checkpoints/start.json');tests=read(P/'unit_tests.json')
 assert tests['success'] and tests['tests_run']==6
 inventory=read(R/'run/run_055/artifacts/private/sample_inventory.json');D01=next(r for r in inventory['records'] if r['sample_id']=='D01');Dxy=np.array([math.log(D01['sigma_y_mpa']/150)/math.log(1000/150),(D01['n']-.02)/.48]);distance=float(np.linalg.norm(Dxy-[.24,.16]));weak=np.array(direction['weak_xy']);strong=np.array(direction['strong_xy'])
 # Additional audit fields from already hash-verified exact ODB result envelopes.
 quality=[]
 for r in data['records']:
  name=r['sample_id'];path=Path(r['FD_path']).parent/'result.json';result=read(R/path)
  quality.append({'sample_id':name,'cutback_increments':result.get('cutback_increments'),'accepted_increments':result.get('accepted_increments'),'rejected_attempts':result.get('rejected_attempts'),'software_phase':result['full_status'].get('phase'),'warning_counts':r['warning_counts'],'quality':r['quality'],'initial_increment':r['initial_increment'],'maximum_increment':r['maximum_increment'],'max_PEEQ':r['max_PEEQ'],'material_p_upper':.9,'time_increment_convergence':'NOT_EVALUABLE for four arms','identity_verified':True})
 save(P/'retained_quality_and_scope.json',{'records':quality,'I06_center_refinement':'SUPPORTED only adjacent settings at I06','arms_not_refined':True,'D01_full_precision_source':{'path':'run/run_055/artifacts/private/sample_inventory.json','sha256':sha(R/'run/run_055/artifacts/private/sample_inventory.json'),'sigma_MPa':D01['sigma_y_mpa'],'n':D01['n'],'normalized_xy':Dxy.tolist(),'distance_from_I06':distance,'distance_divided_by_old_axis_halfstep':distance/.025},'no_D01_local_J_created':True})
 design={'status':'PROPOSAL_ONLY_NOT_PREPARED_OR_AUTHORIZED','objective':'directly test whether opposite sigma/n changes cancel in actual mixed-direction FE response near I06; not minimize Loss','minimum_new_FE_proposal':2,'center_reference':'existing refined I06 from run062, max increment .00125','normalized_radius':.025,'direction':weak.tolist(),'points':direction['physical_coordinate_mapped_halfstep_locations'],'numerics':{'initial':.001,'max_increment':.00125,'min_increment':1e-12,'step_time':1,'max_increments':999999,'CPUs':14,'GPUs':0},'other_physics':'same I06 material contract/generator, geometry,mesh,BC/contact/output; parameters only change by the proposed mixed offsets','compare':'actual plus/minus FD and features versus existing refined center; odd/even response, RMS, per-band behavior, projected strong/weak components; old coarse-axis prediction is EXPLORATORY and not same-precision ground truth','stops':['identity or contract mismatch','Datacheck/Full failure or unknown attempt','incomplete0-1.2mm coverage','PEEQ reaches/exceeds .9 table','unexplained serious accepted warning or contact/force anomaly','mixed response not distinguishable from available numerical evidence: UNRESOLVED, no automatic re-run'], 'failure_cost':'each started attempt consumes one, zero automatic retry','cannot_prove':['global inverse uniqueness','a converged two-column Jacobian','formal parameter CI','SA508 material truth'],'separate_full_axis_precision_option':{'new_FE':4,'scope':'only if numerically qualifying the original P01-P04 Jacobian is the next objective; center alone is insufficient; not currently requested'},'no_INP_or_job_or_queue_created':True,'if_goal_is_D01':'new D01-centered boundary-aware design required; I06 direction cannot be transplanted; sigma_y lower bound forbids unchanged symmetric h=.025'}
 save(P/'minimal_future_FE_proposal.json',design)
 status={'VERIFIED_FE_RESPONSE':'PASS_WITH_RETAINED_WARNINGS; five old actual FE responses and one actual center refinement source verified','EXPLORATORY_LOCAL_LINEAR_ANALYSIS':'COMPLETED_LIMITED; finite secants and deterministic scenarios only','NUMERICAL_RESOLUTION_LIMITED':True,'LOCAL_IDENTIFIABILITY':'LIMITED_UNCHANGED','PROSPECTIVE_PARAMETER_PREDICTION':'PARTIAL_UNCHANGED_RUN059','REAL_MATERIAL_VALIDATION':'NOT_EVALUABLE','NOT_EVALUABLE':['strict differential/time-step-converged Jacobian','formal Fisher information/covariance/parameter confidence intervals','global compensation curve or global uniqueness','D01 local Jacobian or extension of I06 slope to D01','reliable direct material inversion formula','statistical information-loss percentage without measured noise/error model'],'new_FE_budget':0,'no_new_inverse_material_estimate':True}
 save(P/'scientific_status.json',status)
 btable='\n'.join(f"|{b['lower_mm']:.1f}–{b['upper_mm']:.1f}|{b['points']}|{b['cosine']:.6f}|{b['singular_values'][0]:.7f}, {b['singular_values'][1]:.7f}|{b['condition_number']:.4f}|{b['interval_own_weak_halfstep_RMS_N']:.4f}|{b['same_global_weak_halfstep_RMS_N']:.4f}|{b['center_change_over_own_weak']:.4f}|" for b in bands)
 vtable='\n'.join(f"|{name}|{view[name]['cosine']:.6f}|{view[name]['condition_number']:.4f}|{view[name]['half_step_weak_physical_equivalent_RMS_N']:.6f}|{view[name]['global_full_weak_equivalent_RMS_N']:.6f}|" for name in ['two_loads','five_features','full241'])
 select=[r for r in scenarios if r['view']=='full241' and float(r['input_RMS_factor'])==1 and float(r['sign'])==1]
 stable='\n'.join(f"|{r['shape']}|{float(r['delta_sigma_tangent_MPa']):+.6f}|{float(r['delta_n_tangent']):+.9f}|{float(r['normalized_offset_norm_over_h']):.6f}|{float(r['unexplained_scaled_response_fraction']):.6f}|" for r in select)
 points=direction['physical_coordinate_mapped_halfstep_locations'];physical='；'.join(f"σy={p['sigma_y_MPa']:.14g}MPa，n={p['n']:.14g}" for p in points)
 write(P/'local_directions_report.md',f'''# 局部强弱方向与证据边界

I06中心σy236.49902622197678MPa、n.0968，归一化x=ln(σy/150)/ln(1000/150)，y=(n−.02)/.48，中心(.24,.16)。P01/P02沿x±.025，P03/P04沿y±.025；全部max increment .0025。J的每行按物理尺度与sqrt行数缩放，不是噪声白化。

full241强方向={strong.tolist()}，弱方向={weak.tolist()}，正负号约定强x正、弱x负；整体翻转同一向量不改变结论。奇异值{view['full241']['singular_values']}，条件数13.3474576254、列余弦.9876212714。6项解析/数值检查通过，5组历史SVD/J重建一致，原文件未改。

弱方向说明σy下降与n升高会部分抵消；单位归一化长度的物理切向偏移见direction_analysis.json。范数.025的弱方向切向约Δσy=−9.098525MPa、Δn=+.007017882；反方向相反。坐标非线性精确映射的两个概念位置为{physical}。这些不是已经求解的新点，更不是拟合或更新的材料参数。

原四臂提供轴向有限割线，不能验证混合方向二阶项。范数.025弱向量落在轴向坐标框内，但不在四轴点的菱形凸包内（L1/h={direction['weak_radial_h_to_axis_sample_L1_h_ratio']:.6f}）；菱形内最大弱向半径约{direction['max_weak_radial_step_within_axis_cross_convex_hull']:.9f}。所以3.092632613N是线性化预测，不是实际混合参数FE响应。不能把这条局部向量积分成已验证的全局非唯一曲线。

归一化弱斜率折算dn/dlnσy约{direction['slope_dn_per_dln_sigma']:.9f}，I06处dn/dσy约{direction['slope_dn_per_dsigma_MPa_at_I06']:.9f}/MPa；仅为当前局部有限差分解释。

D01在既有标准数据中的完整参数σy={D01['sigma_y_mpa']}MPa、n={D01['n']}，归一化位置{Dxy.tolist()}，距I06为{distance:.9f}、约14.51个原半步。I06导数、数值差和局部弱斜率不能直接推广到D01；其σy靠近150MPa下界，原h=.025的负向屈服扰动会越界，需独立设计，不可擅自扩域。D01正式局部Jacobian=NOT_EVALUABLE。
''')
 write(P/'band_resolution_report.md',f'''# 分位移段SVD与分辨率

J_band=A_band/(1428.9 sqrt(N_band))。A为N/单位归一化参数，半步强/弱响应=h*1428.9*s。分段左闭右开、末段含1.2mm，不重叠共241点；full单列。所有分区样本足、代数秩2、真实曲线可追溯，谱可探索计算；各区严格数值已分辨/导数收敛资格仍NOT_EVALUABLE。

|区间mm|N|列余弦|奇异值s1,s2|条件数|该区自身弱半步N|同一全局弱半步N|中心差/该区自身弱|
|---|---:|---:|---|---:|---:|---:|---:|
{btable}

早段条件数10.83最小，但自身弱响应仅1.251N，中心细化差.4977N、比值.398；末段载荷大但条件数30.76、列方向更接近平行，不能据“大载荷”认定高区分力。对统一full弱方向，早段响应3.701N，中段3.173N，.6–.9mm为2.234N，末段3.082N；这与“每段自己找最弱方向”是不同问题。整曲线弱3.093N超过每个子段自身最弱响应，说明跨阶段的参数敏感性比值变化提供互补约束。

不能仅保留条件数最低的0–.3mm，也不能仅取末段。弱方向响应在早段/中段偏负、后段偏正，应保留跨阶段的形状差异。中心分段细化差只作参考，不能当作该区P01–P04误差上界。条件数依赖归一化与所选响应度量；这里不是Fisher信息，更不假定241点彼此独立。
''')
 write(P/'feature_information_report.md',f'''# 少量特征与全曲线：局部信息比较

两载荷严格沿用F(.15)、F(.90)；五特征为F(.15)、F(.30)、F(.60)、F(.90)、W(0–1.2)。17项完整特征均从原生折线重复提取，与run059缓存一致；斜率单位N/mm、面积N*m，不等同单轴模量/ALLPD。没有新回归训练或特征筛选后独立泛化宣称。

|输入|参数列余弦|条件数|各自弱半步N等效|同一full弱方向N等效|
|---|---:|---:|---:|---:|
{vtable}

对同一full弱方向，F(.15)约−3.573N、F(.30)−2.770N、F(.45)−5.538N、F(.60)−.782N、F(.75)+.545N、F(.90)+1.511N、F(1.20)+4.298N。F(.45)的绝对弱响应大，但其梯度方向与早段载荷相近，并不自动提供独立参数信息。晚段多项载荷方向相近，局部冗余高；例如F(.90)与F(1.20)的两分量梯度夹角仅约1.99度。这里的梯度余弦不是多样本Pearson，也不是参数两列余弦。

总面积的全局弱响应约−.00147845N*m，折算平均力约−1.232N；早负晚正部分抵消。五特征增加的若干行接近共同强方向，并受sqrt行数和面积尺度影响，故条件数反而较两载荷更高，不能把“更多”当作“更独立”。完整曲线保留.45mm、末段及接触变化邻域的形状，既有前瞻预测也较好；但两参数局部响应最多秩2，不能声称full增加第三个参数维度。

次级/探索组合F(.15),F(.30),K(.60–.90)条件数约10.499、弱半步4.163N等效；这一组合使用不同物理行权重，斜率可能放大局部接触/插值误差，不能称信息量胜过全曲线或已经提升独立预测。F(.15),F(.30),F(.90)本轮仅作预先声明的探索组合，条件数约12.804。后续如使用须独立预注册评价；不能在这四个前瞻点上重选后再宣传验证通过。

保留run059冻结预测结果：常数I06的σ/n MAE约5.610MPa/.006；两载荷31.281MPa/.06702；五特征22.570MPa/.03866；full4.545MPa/.004429。full优于常数但半步目标未全通过。当前不能给可靠直接反演公式，也不能把这些FE自洽误差当真实SA508参数精度。

少量特征相对full的“统计信息损失百分比”=NOT_EVALUABLE：没有真实观测误差协方差，不同特征单位/权重及误差相关性不同。可以报告上述局部弱响应与条件数、冻结前瞻误差，不将幅度比伪装成严格信息比例。
''')
 write(P/'scenario_report.md',f'''# 确定性响应扰动情景（SCENARIO ANALYSIS）

参考a=.4326779144080392N只是run062中心相邻增量差RMS。情景幅度为.25a/.5a/a/2a，两种正负号；形状为旧局部强/弱左奇异模式、位移线性ramp、.98mm处宽度.01mm的局部平滑凸起，另保留实际中心差模式。凸起具有Gaussian函数形状，不代表高斯随机噪声。每条情景内部形状完全相干，没有独立样本/高斯方差/实验精度假设。共102个“形状×幅度×符号×输入视图”局部计算，零新FE。

δq=J^+ e_scaled仅用于映射假设响应变化的切向灵敏度；不读SPT实验值去估计材料、不校准参数、不输出修正材料本构。物理切向δσy=σy ln(1000/150)δx、δn=.48δy。它们不是本次实际材料参数误差、数值偏差估计、四臂误差界或置信区间。

以下统一full241、正号、RMS=a：

|形状|切向Δσy MPa|切向Δn|归一化偏移范数/h|响应投影剩余比例|
|---|---:|---:|---:|---:|
{stable}

同RMS弱对齐模式的参数位移范数放大约为强对齐模式的13.347倍；a水平可产生约−1.273MPa/+0.000982的假设切向偏移。实际中心差形状的映射约+.485MPa/−.000342，且90.64%的响应范数位于此两列局部响应子空间外。该结果说明“幅度相同”不足以决定参数影响；不证明真实误差更小，也不把实际中心差当全域误差上界。局部凸起对固定两载荷可几乎不可见，而full仍能检测形状异常，这也是质量诊断信息，不能直接解释成更准确材料识别。

R=.139906仍是主参考，未用情景投影追溯降低其风险等级。没有噪声协方差，不生成Fisher置信区间；无重复求解与四臂精度数据，不宣称已排除数值分辨率限制。
''')
 report=f'''# run_063 — Parameter Coupling & Resolution Analysis

完成：{now()}，Asia/Shanghai。**WARNING / OFFLINE_LOCAL_COUPLING_ANALYSIS_COMPLETE**。本轮没有新FE、INP、入队、Solver/Datacheck、重试、材料反演、BO/DE/RL或预测器训练。全部分析来自有界真实FE提取及冻结有限差分，历史研究不变。

## 证据等级

**VERIFIED_FE_RESPONSE**：I06及P01–P04真实输入/ODB/FD、单位符号/完整0–1.2mm和run059评价来源复核，5点均为同物理模型、同max .0025控制。新细化中心max .00125仅作独立数值参考，未替换旧中心或旧Jacobian。参数、塑性表及来源hash、冻结预测器及既有评价保持。保留全部数值警告、接受/拒绝试算区分和I06 QUALIFIED_WITH_LIMITATIONS；这不是宣称全域FE模型已验证。

**EXPLORATORY_LOCAL_LINEAR_ANALYSIS**：本轮SVD/分段/特征/确定性情景均为有限幅局部解释，弱混合方向尚没有真实直接FE。

**NUMERICAL_RESOLUTION_LIMITED**：中心变化.432678N相对full弱半步3.092633N为.139906；不是独立高斯σ、Jacobian误差界或实测噪声。P01–P04未细化，分区数值分辨资格不能自动升级。

**NOT_EVALUABLE**：严格已收敛微分Jacobian、Fisher协方差/正式参数置信区间、全局唯一或非唯一曲线、D01局部导数、可靠直接材料反演公式、真实材料验证。run059 LOCAL_IDENTIFIABILITY LIMITED / PREDICTION PARTIAL，正式真实材料验证NOT_EVALUABLE均保留。

## 核心发现与问题回答

1. **最难识别的联合变化**是归一化弱方向(−.8111605651,+.5848235099)：降低σy、增加n部分补偿，反方向同理。半步范数.025对应切向约−9.099MPa/+ .007018。full奇异值1.155540143与.0865738012、条件数13.34746；强半步载荷RMS约{view['full241']['half_step_strong_physical_equivalent_RMS_N']:.6f}N，对比弱3.092633N。不是已证实的全局非唯一曲线。

2. **位移信息互补**：早段自身条件较好但弱绝对信号小，晚段载荷大但更耦合。对同一个full弱向量，0–.3/.3–.6/.6–.9/.9–1.2mm响应分别3.701/3.173/2.234/3.082N RMS；各段自身弱方向则仅1.251/1.751/2.151/2.004N。推荐保留早中晚形状对照，不能只按条件数或单段载荷选窗。分区数值证据限制见band_resolution_report.md。

3. **少量特征损失的是形状与跨阶段约束**：两载荷/五特征/full条件数14.8847/16.6193/13.3475，参数方向仍高度相关。总面积会抵消弱方向早负晚正响应；部分额外载荷/面积行高度冗余，五特征未稳定改善独立性。full是目前主反演和数值质量基线，少量特征作为可解释诊断/辅助更合理，尚不支持独立可靠直接公式。没有噪声模型，不给“损失xx%信息”的伪定量结论。

4. **局限的证据排序**：相近参数响应方向是实际FE有限割线的强证据；特征压缩和冻结逆模型在稀疏25点训练支持下的恢复不足有直接前瞻证据；中心数值差小于但不可忽略于弱信号，四臂精度未评估。它们共同作用，不能定量分摊因果，不能把R=.14直接当参数误差14%。

5. **不能推广至D01**：其完整参数152.3086335396325MPa/.23066241424320405，归一化距I06约{distance:.6f}、14.51个轴向半步；更靠近σy下界。局部抵消机制可作为科学假设，但方向、条件数和数值误差都需D01本地数据验证，不能拼接或外推为D01正式Jacobian。

6. **暂不申请P01–P04额外细化**与当前用户决定一致。若未来目的专门是资格认证旧Jacobian，完整四臂各一次细化仍是最小完整对应方案；本轮不申请或执行，也不能用中心结果替代。

7. **下一项更直接的机制检验**建议为I06附近沿弱联合方向的正负两个真实混合参数点，max .00125、复用已细化中心，最少2个新FE。概念参数为{physical}。它们不是本轮新反演结果，只是现有局部SVD映射的研究设计。四轴样本不直接覆盖此混合响应，真实两点能检验σ/n抵消是否按线性预测存在、正负是否对称、接触/非线性是否破坏该方向。旧轴向预测来自.0025，必须明确其精度差异；新两点与新中心使用统一.00125，不能把比较称作已收敛原Jacobian。若需要强/弱真实响应对照，可另议强方向±两点，但不是最小2点设计的一部分。失败/不全/超表或接受态异常时停止、不重试；若混合响应与数值证据无法分开则UNRESOLVED，不自动加点或减半。

8. **研究路线**：继续以full F–D为主要输入，优先用实际混合扰动检验参数混淆，而非盲目增加训练特征、复杂回归或优化预算。现阶段少量特征路线值得作为诊断和研究假设继续，不能以其输出数字宣称材料唯一识别。若目标转为D01最佳区，应先另定边界感知本地设计；若目标转为真实材料预测，还需独立观测和模型形式证据，I06数值分析不能解决真实材料有效性。

## 产物与保护

完整局部方向、分段SVD、特征响应/冗余、102条确定性情景、2点最小未来方案以及6张科学图见本私有目录。6项解析与数值测试通过；所有历史主/次5组J及奇异值从原生响应重建一致，Gram谱独立复核；分区RMS归一化加权关系与情景符号/幅度检验通过。图中的等响应椭圆是线性模型预测，不是置信域，概念混合点以空心标识区分真实轴点。

未访问拉伸或封存分析；保留run015历史信息暴露声明，未将任何条件性拉伸比较升级为正式验证。run046/047/048及run055–062冻结资料不改，未重新训练/估计材料参数；不改.gitignore、Git索引或本地CAE，不commit/push。所有敏感响应、报告和推导保留Git忽略私有区，通过正式Hub登记。完成后停止，本轮新增FE预算0；未来2点/4点建议都必须另行批准，不生成Job或INP。
'''
 write(P/'scientific_report.md',report)
 for s in source['sources']:assert sha(R/s['path'])==s['sha256'],s['path']
 assert git('rev-parse','HEAD')==start['git']['head'] and git('diff','--cached','--name-status')==start['git']['staged']
 # Explicitly verify private evidence protection rather than assuming ignored status.
 ignored=git('check-ignore','--',str(P/'scientific_report.md'));assert ignored
 save(P/'preservation_final.json',{'at':now(),'protected_sources_verified':len(source['sources']),'all_original_hashes_unchanged':True,'git_head':git('rev-parse','HEAD'),'staged':git('diff','--cached','--name-status'),'gitignore_sha256':sha(R/'.gitignore'),'private_report_ignored':True,'local_CAE_present_and_hash_verified_in_source_manifest':True,'new_FE':0,'new_INP':0,'queue_or_solver_interface_called':False,'no_new_material_inversion_or_training':True})
 files=[p for p in sorted(A.rglob('*')) if p.is_file() and p.name not in ['evidence_manifest.json','agenthub_completion_receipt.json','hub_identity_lease.json'] and '__pycache__' not in p.parts]
 save(P/'evidence_manifest.json',{'version':'run063-static-evidence-v1','at':now(),'files':[{'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],'exclusions':['self','Hub session/lease token','later Hub completion receipt','live run/index/status']})
 identity=read(P/'hub_identity_lease.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=identity['identity'];tid=identity['task_id'];lease=identity['lease'];hub.heartbeat(lease)
 registered=[]
 for p in files+[P/'evidence_manifest.json']:
  r=hub.artifact(tid,actor['agent_id'],p,{'run':'run_063','scope':'offline local finite-secant/scenario analysis; no FE, no new material parameter inversion'},version='run063-v1');registered.append({'path':rel(p),'sha256':r['sha256']})
 body={'run':'run_063','status':status,'weak_direction_xy':weak.tolist(),'primary_conditions':{k:view[k]['condition_number'] for k in ['two_loads','five_features','full241']},'report_path':rel(P/'scientific_report.md'),'report_sha256':sha(P/'scientific_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'new_FE':0,'future_minimum_proposed_only':2,'decision':'full curve baseline; no reliable direct feature formula; future actual mixed weak pair tests local compensation, not global uniqueness'}
 msg=hub.message(tid,actor['agent_id'],'MAIN',body,'run063-completion-main-v1');hub.finish(lease,body,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain()
 save(P/'agenthub_completion_receipt.json',{'at':now(),'task_id':tid,'task':hub.task(tid),'registered_artifacts':registered,'message_id':msg['message_id'],'audit_chain_verified':True,'cross_chat_automatic_wakeup_claimed':False})
 important=[P/'scientific_report.md',P/'direction_analysis.json',P/'band_SVD_analysis.json',P/'view_SVD_comparison.json',P/'scenario_parameter_sensitivity.csv',P/'minimal_future_FE_proposal.json',P/'scientific_status.json',P/'source_manifest.json',P/'evidence_manifest.json',P/'agenthub_completion_receipt.json']
 save(A/'manifest.json',{'version':'run063-final-artifacts-v1','files':[{'path':rel(p),'role':'offline analysis evidence','private':True,'sha256':sha(p)} for p in important]})
 write(RUN/'summary.md','''# run_063 — Parameter Coupling & Resolution Analysis

**WARNING / OFFLINE_LOCAL_COUPLING_ANALYSIS_COMPLETE。** 复核5个旧真实FE点、中心细化参考及冻结预测器；重建5组历史J/SVD一致。完整曲线弱方向约(−.81116,+.58482)，σy下降/n升高部分抵消。早段条件较好但绝对弱信号小，保留跨阶段形状信息；少量特征尚不能给可靠直接公式。

真实响应VERIFIED_FE_RESPONSE；有限割线/确定性情景为EXPLORATORY_LOCAL_LINEAR_ANALYSIS；NUMERICAL_RESOLUTION_LIMITED保持。严格收敛Jacobian、Fisher区间、全局唯一性、D01本地识别和真实材料验证仍NOT_EVALUABLE。未修改run059的Jacobian/预测评价。

见[科研报告](artifacts/private/scientific_report.md)、[分段分析](artifacts/private/band_resolution_report.md)、[方向报告](artifacts/private/local_directions_report.md)、[特征信息](artifacts/private/feature_information_report.md)、[情景](artifacts/private/scenario_report.md)、[证据清单](artifacts/private/evidence_manifest.json)、[AgentHub](artifacts/private/agenthub_completion_receipt.json)。6项数学测试及6张图已完成。

不申请当前四臂细化；未来最小机制测试建议弱方向正负混合参数2点，须另行授权且不能替代四臂数值认证。当前新增FE/INP/入队/训练/材料反演0，Git保护与历史冻结不变。完成后停止。
''')
 j=read(RUN/'run.json');save(RUN/'checkpoints/run_before_close.json',j)
 j.update(status='WARNING',end_time=now(),outcome='OFFLINE_LOCAL_COUPLING_ANALYSIS_COMPLETE',inputs=[{'path':rel(P/'source_manifest.json'),'role':'bounded source identities','sha256':sha(P/'source_manifest.json')}],outputs=[{'path':rel(p),'role':'offline coupling and resolution evidence','sha256':sha(p)} for p in important],validation=[{'check':'source and actual-response consistency','status':'PASS','evidence':rel(P/'verified_local_data.json'),'scope':'five real FE responses, same coarse controls; refined center reference separate'},{'check':'SVD reconstruction and analytic tests','status':'PASS','evidence':rel(P/'unit_tests.json'),'scope':'six tests, five historical matrices reconstructed; no claim of converged differential J'},{'check':'scientific scope','status':'WARNING','evidence':rel(P/'scientific_status.json'),'scope':'finite local secants and deterministic scenarios; no noise/Fisher/global material inference'}],scientific_status=status,agenthub_task_id=tid,new_FE=0,new_INP=0,queue_mutation=False,solver_datacheck_started=False,new_material_inversion=False,tensile_access=False)
 temp=RUN/'run.json.tmp';write(temp,json.dumps(j,ensure_ascii=False,indent=2)+'\n');read(temp);temp.replace(RUN/'run.json')
 index=R/'run/README.md';old=index.read_bytes();assert b'run_063' not in old
 index.write_bytes(old+('\n\n## 离线科研 Run — run_063\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_063 | 局部参数耦合、分段/特征SVD、确定性响应扰动情景 | WARNING / LIMITED | [summary](run_063/summary.md) |\n\n真实旧FE核验，弱方向σy↓/n↑；完整曲线保留为主基线，不生成直接材料公式。当前新FE/训练/入队0；未来弱方向混合±2点仅建议，完成后停止。\n').encode())
 statuspath=R/'status/PROJECT_STATUS.md';old=statuspath.read_bytes();first=old.find(b'\n')+1
 note=f'\n## 当前状态 — run_063（{now()[:10]}，Asia/Shanghai）\n\n**WARNING / OFFLINE_LOCAL_COUPLING_ANALYSIS_COMPLETE。** 真实响应与旧Jacobian核验，弱方向约(−.81116,+.58482)；分段绝对信号/条件对比、特征信息与确定性情景完成。LOCAL_IDENTIFIABILITY LIMITED、数值分辨受限、正式材料验证NOT_EVALUABLE保持。详见[run_063](../run/run_063/summary.md)。继续full曲线基线；当前新FE/输入/入队/训练0，未来弱方向混合2点仅为需另行授权的建议，完成后停止。\n'
 statuspath.write_bytes(old[:first]+note.encode()+old[first:])
 save(RUN/'checkpoints/completed.json',{'at':now(),'report_sha256':sha(P/'scientific_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'AgentHub_task':tid,'new_FE':0,'stop':True})
 print(json.dumps({'status':'WARNING','report_path':rel(P/'scientific_report.md'),'report_sha256':sha(P/'scientific_report.md'),'evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'AgentHub_task':tid,'proposed_future_minimum_FE_only':2,'actual_new_FE':0}))
if __name__=='__main__':main()
