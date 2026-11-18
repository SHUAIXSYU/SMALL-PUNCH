"""Record offline scientific findings using existing Hub public interface."""
from pathlib import Path
import json,sys,hashlib,subprocess,os
from datetime import datetime
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_054';A=RUN/'artifacts';P=A/'private';sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,o):
 if p.exists():
  assert read(p)==o,'Existing finalization artifact differs: '+str(p)
  return
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def write(p,s):
 if p.exists():
  assert p.read_text(encoding='utf-8')==s,'Existing text differs: '+str(p)
  return
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
def rel(p):return p.relative_to(R).as_posix()
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def main():
 now=read(P/'scientific_decision.json')['at'] if (P/'scientific_decision.json').exists() else datetime.now().astimezone().isoformat();d=read(P/'direction_results.json');a=read(P/'input_compatibility_audit.json');sources=read(P/'source_hash_manifest.json')['sources'];tests=read(P/'synthetic_tests.json');assert tests['returncode']==0
 for s in sources:assert sha(R/s['path'])==s['sha256'],s['path']
 assert not a['cross_study_same_basepoint'] and not a['cross_study_same_numerical_controls']
 assert d['formal_joint_identifiability']=='NOT_EVALUABLE' and d['formal_joint_Jacobian'] is None and d['formal_joint_Fisher_information'] is None
 ids=read(P/'hub_identity_and_lease.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);hub.heartbeat(ids['lease']);assert hub.verify_chain()
 future={'status':'DESIGN_ONLY_NOT_AUTHORISED','immediate_new_FE_budget':0,'purpose':'test same-point constitutive direction confounding, not minimize Loss','existing_center':'refined D01,152.3086335396325MPa,n=.23066241424320405,alpha1','all_future_numerical_settings':'same as D01/H01/H02: initial.001,max.00125,min1e-12,time1,inc999999,14CPU0GPU; unchanged geometry,mesh,contact,BC,outputs,loss','minimum_to_fill_missing_sigma_n_columns':4,'suggested_stencil':{'sigma_x':'two feasible one-sided positive offsets from x_D (illustratively +.02,+.04); second-order forward stencil (-3F0+4Fh-F2h)/(2h)','n_y':'two symmetric offsets from y_D (illustratively +/-.025); central stencil','normalization':'x=ln(sigma_y/150)/ln(1000/150),y=(n-.02)/.48','boundary_reason':'D01 only2.3086MPa above150MPa lower search bound; do not transplant old +/- .05x or expand boundary based on tensile data'},'prerequisites':['Before any input preparation freeze the three-parameter material-family definition; alpha1 must recover original Hollomon exactly','If alpha acts off-center, freeze p_switch=.09774053167903649 and transition width.05, anchor to each candidate own unchanged lower branch; do not retune after response','Select/freeze finite-difference step using boundary and numerical-signal criteria, not whichever improves Loss; proposed offsets are a design illustration, not a frozen batch','All actual source/hashes, windows, material coverage, process identity and accepted numerical warnings must pass','Do not combine different maximal increments as equal-accuracy observations'], 'additional_alpha_step_check_if_local_J_required':{'new_FE':2,'design':'a smaller symmetric alpha pair around1, predeclared step after offline table validation; current +/-.5 secant shows12.23% even/odd component and is not an infinitesimal derivative','total_planned_if_needed':6},'stop_conditions':['identity/attempt uncertainty, solver failure, incomplete241point window, PEEQ outside table, unexplained accepted-state serious anomaly -> stop, null score, no retries','response contrasts comparable to observed numerical change -> direction UNRESOLVED, no Fisher/condition claim','large step asymmetry or cross-step change -> no local-linear interpretation','same-point directions remain nearly dependent -> do not add blind optimization budget; prioritize independent measurement/second loading channel'], 'formal_Fisher_requires':'defined observation/model-error covariance and applicable local linearization; no such covariance assumed now','new_input_generation':False,'no_solver_authorisation':True}
 save(P/'future_minimum_identification_design.json',future)
 evidence_levels={'A_actual_FE_contrast':'VERIFIED_EXISTING_RESPONSE: D01/H01/H02 same low branch and numerical settings; alpha contrasts trustworthy for bounded exploratory response, with per-model numerical caveats','B_historical_sigma_n':'RECOMPUTED_WITHIN_STUDY_SECANTS: 200MPa,.1; same historical static settings;37-47cutbacks and historical process gaps persist','C_cross_direction':'EXPLORATORY_ONLY: different center and timestep; cosine/span comparisons describe shapes, not common parameter derivatives','D_joint_identifiability':'NOT_EVALUABLE: missing same-D01 sigma/n responses; no joint Jacobian,FIM,rank,condition number or confidence interval','E_single_curve_insufficiency':'SUPPORTED_RESEARCH_HYPOTHESIS_NOT_PROVEN: partial overlap plus displacement-dependent differences warrant targeted test; no strict global non-identifiability claim'}
 decision={'at':now,'run_id':'run_054','status':'WARNING','outcome':'OFFLINE_CONFOUNDING_ASSESSMENT_COMPLETE','formal_joint_identifiability':'NOT_EVALUABLE','evidence_levels':evidence_levels,'cosines':d['cosines'],'key_residual_fact':'54.218% of D01 residual squared lies0-.3mm;86.263% of alpha response squared lies.9-1.2mm; amplitude diagnostics, not Fisher information','recommendation':'retain alpha as a diagnostic axis, do not start three-parameter inversion; preserve early/mid response and seek independent material/fixture evidence; optional same-point4contrast design only after separate research decision','immediate_new_FE_budget':0,'conditional_future_minimum_FE':4,'if_alpha_step_check_required_total':6,'new_FE':0,'new_queue_records':0,'tensile_data_or_leak_analysis_read':False,'material_refit':False,'original_predictions_modified':False}
 save(P/'scientific_decision.json',decision)
 lines=['# run_054 — 离线本构敏感性与参数混淆评估','',f'完成时间：{now}。**WARNING / OFFLINE_CONFOUNDING_ASSESSMENT_COMPLETE**。','',
 '## 明确结论','',
 '高应变硬化α的真实响应与旧σy/n响应形状存在部分相似，但并不重合。现有证据足以提出联合混淆研究假设，不足以建立同一D01点的三参数Jacobian或正式Fisher信息矩阵。正式联合可识别性、联合条件数与置信区间均为NOT_EVALUABLE。不能将跨基准、跨时间控制的数据拼接后宣称已识别第三个参数。','',
 '本轮仅重新计算已有曲线，没有新ODB调用、求解、Datacheck、入队、INP生成、重拟合或优化。全部实验网格、Loss、材料预测及历史证据保持不变。','',
 '## A. 数据身份、材料与数值契约','',
 '在新的合法run054中核对81份指定源文件，包括冻结INP/参数、原ODB/STA/MSG/DAT/LOG哈希、真实ODB会话先前提取的CSV与来源记录、Hollomon及包络源码。输入身份明细见input_compatibility_audit.json、source_hash_manifest.json。没有扫描整个私有资料区，也没有读取封存拉伸文件或其泄漏分析。',
 '对七份INP扣除塑性表数据与Static数值行、忽略注释后，物理模型文本哈希完全一致：几何/网格/接触/摩擦/BC/加载/输出没有变化，E、ν也保留在比较骨架中。原Hollomon源码SHA为d937664f7fc7f845a9ed7a75a004275bf38d11a1b3f68975a05961adb9b16363，高应变包络实现为93e8cb95b3c17cb90552a56a891e77fe16451371a4e7dd32fbdb245c0a40f43d。',
 '但响应基点及数值契约不同，不能因此称它们同点、同精度：','',
 '|研究|基点(σy MPa,n)|初始增量|最大增量|完整FD点数|切回|','|---|---|---:|---:|---|---|',
 '|run020/022 σy/n|200,0.1|0.01|0.1|L01–04:174/182/189/149|47/44/47/37|',
 '|run045精化D01|152.3086335396325,0.23066241424320405|0.001|0.00125|805|1|',
 '|run053 H01/H02|同D01，α=.5/1.5|0.001|0.00125|805/805|1/1|','',
 '两组总时间1、最小增量1e-12、最大增量次数999999一致。表中最大步长是允许上限，不能说所有实际接受步都相差80倍。旧模型最大PEEQ依次.69265/.69702/.72192/.67389，均在塑性表.9内；但数值警告与L01/L03/L04历史过程身份缺口仍保留，不追溯升级。',
 'D01已有相邻时间增量细化PASS，但仅点级检查；其历史Runner过程身份提示仍保留。H01/H02为探索性可评分，不具备各自额外细化误差界。H01约1.15474mm接受帧8.13N变化与节点23接触压力建立相关，无该处cutback或严重警告；COPEN哨兵缺失不能补成间隙闭合证明。',
 'RP均为ASM_SPT节点1，u=-U2、F=-RF2，m/N，无额外2π力因子。七条FD均完整覆盖0–1.2mm；统一重新插值至同一241个实验点，逐点对照run022/run053保存的对齐结果。各原始采样密度保留，没有抹平粗采样误差。',
 'Loss严格为run017-exploratory-fd-v1、F_ref1428.9N、等权MSE、线性插值、无外推/移动零点/平滑/删点。既有实验及代码SHA重新核对，未改变单位、窗口或归一化。','',
 '## B. α方向：同D01有限幅响应','',
 '固定σy、n和低应变材料表；p_switch=.09774053167903649，过渡宽度.05。这里α指平滑过渡后的硬化速率倍率，不是整条应力曲线相乘，不是真实材料置信界。',
 '定义δF−=F(.5)−F(1)，δF+=F(1.5)−F(1)；中心割线Sα=[F(1.5)−F(.5)]/1，单位N/单位α。偶分量E=[F(1.5)+F(.5)]/2−F(1)，奇分量O=[F(1.5)−F(.5)]/2。','',
 f'- Sα全窗RMS={d["alpha"]["secant_RMS_N_per_alpha"]:.6f} N/单位α，范数={d["alpha"]["secant_norm_N_per_alpha"]:.6f} N/单位α；这是幅度±.5割线，不是已验证微分导数。',
 '- δF−/δF+的RMSE为48.247981/47.526008N，最大绝对差120.602019/121.155141N；与run053一致。',
 f'- 两侧反向对齐余弦{d["alpha"]["side_cosine_after_sign_alignment"]:.6f}；偶分量RMS{d["alpha"]["even_RMS_N"]:.6f}N、奇分量{d["alpha"]["odd_RMS_N"]:.6f}N，偶/奇={100*d["alpha"]["even_over_odd_RMS"]:.3f}%，存在有限幅非线性和接触路径差。',
 '- 早期14点Sα为负、216点为正，其余零。不能声称提高硬化必然全程提高载荷；早期很小反序不等于同一曲线出现载荷回退。',
 '- 两侧有限响应RMSE约为D01已观察相邻时间增量差.338306N的142.6/140.5倍；最大差约为1.802858N参考的66.9/67.2倍。参考不是H模型数值误差上界，也不构成统计显著性检验。不要将单位α导数的范数直接与数值载荷差当作自然参数重要性比较。','',
 '## C. 跨实验方向比较：只作EXPLORATORY','',
 '旧归一化：x=ln(σy/150)/ln(1000/150)，y=(n−.02)/.48。Sx=(L02−L01)/.1，Sy=(L04−L03)/.1；原半步h=.05。L01/L02 σy=181.9007788573887/219.9001029641563MPa、n=.1；L03/L04 σy200MPa、n=.076/.124。',
 'Sx/Sy单位分别为N/单位x、N/单位y；Sα为N/单位α。量纲/选定坐标幅度不同，不能用原始列范数排名“哪个参数更重要”。以下余弦先按各自全窗欧氏范数归一，只比较形状，不把归一后的列视为同点Jacobian。','',
 '|方向|余弦|夹角|证据范围|','|---|---:|---:|---|']
 for key,x in d['cosines'].items():lines.append(f'|{key}|{x["cosine"]:.9f}|{x["angle_degrees"]:.4f}°|'+('旧同批两参数割线' if key=='sigma_x_old__n_y_old' else '跨基点/数值控制探索性')+'|')
 lines += ['',
 '旧两列SVD复算为22753.983675、1504.133375 N/归一化坐标，条件数15.127637，重现run022。它只属于旧200MPa/.1点和旧步长设置；不是D01点的条件数，更不是三参数条件数。',
 f'将单位α响应形状投影到旧两列形状张成空间，仅为辅助图形比较：平方范数表示比例{100*d["alpha_projection_onto_old_parameter_shape_span"]["represented_squared_norm_fraction"]:.3f}%，未被表示的范数比例{100*d["alpha_projection_onto_old_parameter_shape_span"]["relative_unrepresented_norm"]:.3f}%。二者一个平方、一个未平方，不能互相作补数。投影系数约−1.976和2.869包含旧列近共线下的抵消，不是可执行的σy/n更新，也不是拟合了新本构。',
 '因此：有重叠响应形状的证据，也有约30.4%范数的非重合部分。不能由90.8%表示比例宣称三参数线性依赖，不能消除基点/时间控制/步长影响。本轮没有计算三列SVD、联合秩或正式FIM。','',
 '## D. 分段信息与实验残差','',
 '残差方向取r=F_exp−F_D01，正向响应与r同向只说明线性项可能减小；有限幅变化仍可过补偿。保持同一冻结网格，前三段各60点、末段61点，不重复端点。','',
 '|位移/mm|Sα RMS/(N/α)|α响应平方占比|D01残差RMSE/N|D01残差平方占比|cos(σ,α)*|cos(n,α)*|','|---|---:|---:|---:|---:|---:|---:|']
 for b in d['bands']:lines.append(f'|{b["lower_mm"]:g}–{b["upper_mm"]:g}|{b["alpha_sensitivity_RMS_N_per_alpha"]:.4f}|{100*b["alpha_squared_response_fraction"]:.4f}%|{b["D01_residual_RMSE_N"]:.4f}|{100*b["D01_loss_contribution_fraction"]:.3f}%|{b["cos_sigma_alpha"]:.6f}|{b["cos_n_alpha"]:.6f}|')
 lines += ['',
 '*为跨实验方向比较。响应平方份额是离散向量幅度分布，不是能量、RF2贡献或Fisher信息。',
 '0–.3mm占D01残差平方54.218%，但α响应平方仅.00693%；.9–1.2mm占α响应平方86.263%，却只占D01残差平方23.242%。α并没有针对主要的早段残差来源。中段.6–.9mm原D01残差RMSE最低约19.69N，α响应已经很强；末段仍有实际残差，不能把整个后段称作“已无误差”。',
 '早段α很弱、旧σ/n形状有更早响应；这使早段—过渡段对区分低段与高段作用具有潜在价值，但初始接触、测量零点/柔度、夹持及有限采样不确定性也会影响它，不能只凭低余弦认定可靠识别。末段虽α幅度最大，和旧σ/n余弦却都约.984，延长或加权末段不自动增加独立信息。本轮不据此改变Loss权重或窗口。',
 f'全窗cos(Sα,r)={d["residual"]["alpha_cosine_to_needed_correction"]:.6f}；cos(δF−,r)={d["residual"]["finite_loss_decomposition"]["H01"]["cosine_to_needed_correction"]:.6f}，cos(δF+,r)={d["residual"]["finite_loss_decomposition"]["H02"]["cosine_to_needed_correction"]:.6f}。',
 '精确恒等式ΔL=[||δF||²−2r·δF]/(241F_ref²)，不用二次模型推断新最优α：','',
 '|模型|响应平方惩罚|残差对齐项|实际ΔLoss|','|---|---:|---:|---:|']
 for name,x in d['residual']['finite_loss_decomposition'].items():lines.append(f'|{name}|{x["response_squared_penalty"]:.12g}|{x["residual_alignment_term"]:.12g}|{x["delta_loss"]:.12g}|')
 lines += ['',
 'H02与修正方向同向但幅度过大，尤其末段ΔLoss贡献+0.000317981压过前三段合计约−0.000046280。因此方向接近不保证Loss下降，更不能据三个点推荐α新最优值。D01/H01/H02既有Loss仍为.000502000275/.002441496895/.000773701458。','',
 '## E. 高应变空间证据的边界','',
 'run050/run053真实空间和能量记录支持D01确实涉及高塑性应变：最大PEEQ约.61146，终态PEEQ>.1参考体积约13.249%；超过PEEQ=.1以后发生的增量塑性功估计约70.98%。这与“终态>.1区域累计功约95.84%”是不同分类，均不能当作Punch RF2贡献。轴对称参考体积为2πr detJ积分，未把截面积当体积。',
 'p_switch由冻结模型真总应变.10映射得.09774053；不能把单轴真总应变.10、PEEQ=.1和独立实验验证界限无条件等同。本轮没有读取拉伸数据，也没有据此改H包络。','',
 '## F. 证据等级与科研决策','']
 for name,text in evidence_levels.items():lines.append('- **'+name+'**：'+text)
 lines += ['',
 '1. 高段硬化与σy/n是否相似？部分相似，尤其末段；不是全窗重合，α的滞后增强特征更明显。',
 '2. 是否已证明联合混淆？没有。同点同数值σy/n响应缺失；当前仅为有数据支持的混淆假设。',
 '3. 单条SPT是否可能不足？可能，特别当仅观察高度共线的后段并同时释放低段与高段自由度；但未证明严格全局不可识别。',
 '4. 哪些段提供相对独立信息？早段与.3–.6mm过渡相对后段具有更不同的响应形状；应保留并核查其测量/夹持可信度，而非为了降Loss更改目标。单独末段的强响应并不保证参数分离。',
 '5. 是否增加参数？不建议立即把α加入优化；将它保留为模型误差诊断轴。先补高应变材料与夹具证据、明确观察噪声/模型误差，再决定是否可校准更多自由度。',
 '6. 最小未来FE如何专门检验识别？即时0。若另行决定补齐同点方向，最低4项：同D01、同最大.00125，补σy两个方向样本和n两个方向样本，复用既有α两侧与中心，不以降Loss为选点目标。D01距150MPa下界仅2.3086MPa，不能照搬旧±.05x；可预注册域内σ的单边二阶两点、n的对称两点。具体设计示例和停止条件见future_minimum_identification_design.json，不是当前冻结候选或计算授权。',
 '该4项仅补齐同基准有限幅响应列，仍不保证线性Jacobian适用；当前α半步.5的偶/奇12.23%提示步长效应。若需要可信局部线性定量，另需预注册较小α对称对2项，规划合计6项；不能自动执行或机械不断缩步。任何正式FIM还需明确观测/模型误差协方差，不能将I权矩阵随意冒充实验噪声。',
 '停止规则：身份不明、失败、不覆盖固定窗口、PEEQ超表、未解释严重接受态异常时停；响应与观察数值差同量级时标UNRESOLVED；差分非对称/步长依赖大则不作局部线性结论；若方向继续近相关，优先第二观测/独立试验而非追加低Loss点。所有未来方案需单独授权，本轮未生成候选。','',
 '## 产物、验证与研究保护','',
 '- input_compatibility_audit.json/source_hash_manifest.json：81项真实源哈希和契约差异；七条曲线均全窗。',
 '- direction_results.json/aligned_response_vectors.csv/band_results.csv：全部数值、符号、分母、对齐向量及分区。',
 '- unit_direction_shapes.png、alpha_contrasts_and_asymmetry.png、band_direction_cosines.png、residual_vs_alpha_regions.png：静态科学图；前者及残差分区图已目视检查。',
 '- scientific_decision.json、future_minimum_identification_design.json、AgentHub收据与evidence_manifest.json：结论等级、无授权计划与交接。',
 '- 9项合成测试实际通过：割线、偶分量、单位缩放余弦、零向量、未表示方向、退化span秩、正对齐过冲Loss恒等式、241点分区、非法步长。真实数组另核对旧Sx/Sy、旧SVD、run053对齐及Loss差恒等式。',
 'run046冻结预测、run025 BLOCKED及run047/run048正式NOT_EVALUABLE不改变。run015历史信息暴露保留，研究不称完全无泄漏盲测。未来如使用已解盲拉伸数据开发模型，须计为开发/校准资料，不能再称未经使用的独立验证集。本轮不读取或使用其内容。',
 '私有实验/响应曲线和科学明细均留Git忽略区；完成后停止，不自动进入新Run或新增计算。','']
 report=P/'confounding_report.md';write(report,'\n'.join(lines));assert 'NOT_EVALUABLE' in report.read_text(encoding='utf-8')
 em=P/'evidence_manifest.json';save(em,{'run':'run_054','at':now,'files':[{'path':rel(f),'sha256':sha(f),'bytes':f.stat().st_size,'visibility':'PRIVATE'} for f in sorted(P.rglob('*')) if f.is_file() and f.name!='hub_identity_and_lease.json'],'exclusions':'self,private live identity/lease,laterHubreceipt and finalcheckpoint'})
 tid=ids['task_id'];registered=[]
 for path in [report,P/'input_compatibility_audit.json',P/'direction_results.json',P/'scientific_decision.json',P/'future_minimum_identification_design.json',P/'source_hash_manifest.json',P/'band_results.csv',P/'unit_direction_shapes.png',P/'residual_vs_alpha_regions.png',em]:
  registered.append(hub.artifact(tid,ids['identity']['agent_id'],path,{'run':'run_054','type':'existing FE offline response assessment','scope':'no common joint Jacobian or Fisher information'},version='run054-v1'))
 result={'run_id':'run_054','report_path':rel(report),'report_sha256':sha(report),'evidence_manifest':rel(em),'evidence_manifest_sha256':sha(em),'status':'WARNING','formal_joint_identifiability':'NOT_EVALUABLE','direction_cosines':d['cosines'],'recommendation':decision['recommendation'],'new_FE':0,'immediate_new_budget':0,'conditional_future_minimum':4,'source_hashes_verified':len(sources)}
 hub.message(tid,ids['identity']['agent_id'],'MAIN',result,'run054-main-scientific-handoff-v1');hub.finish(ids['lease'],result,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain()
 save(P/'agenthub_completion_receipt.json',{'task_id':tid,'task':hub.task(tid),'artifacts':registered,'audit_chain_verified':True,'no_automatic_chat_wakeup_or_read_claim':True})
 write(RUN/'summary.md','# run_054 — 离线本构敏感性与参数混淆\n\n**WARNING / OFFLINE_CONFOUNDING_ASSESSMENT_COMPLETE。** 已核验指定响应源与契约、重算同D01高应变割线/非对称、旧两参数方向及跨实验形状、冻结实验残差和分段指标。基点与最大时间增量不同，正式三参数Jacobian/Fisher信息和联合可识别性均NOT_EVALUABLE；跨批方向结论仅EXPLORATORY。\n\n完整[私有科研报告](artifacts/private/confounding_report.md)、[数据与证据身份](artifacts/private/evidence_manifest.json)、[条件性最小识别设计](artifacts/private/future_minimum_identification_design.json)。当前不增加可拟合自由度或计算预算；若未来补齐同D01方向，最低四项仅属计划并需另行授权。\n\n9项合成测试与真实数组交叉校验通过，AgentHub正式科学任务已完成WARNING。历史曲线/预测/Loss与数值门槛保持原样；无新求解、Datacheck、INP、入队、拟合、BO/DE/RL或Git提交，无拉伸内容访问。保留信息暴露及历史NOT_EVALUABLE/BLOCKED，完成后停止。\n')
 index=R/'run/README.md';s=index.read_text(encoding='utf-8-sig');assert '## run_054' not in s;index.write_text(s+'\n\n## run_054 — 离线参数方向与高应变混淆\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_054 | 核对跨基点/数值契约，量化方向、残差及识别证据等级 | WARNING / OFFLINE_CONFOUNDING_ASSESSMENT_COMPLETE | [summary](run_054/summary.md) |\n\n正式联合指标NOT_EVALUABLE，科学明细留私有区，无新计算/入队/拟合，完成后停止。\n',encoding='utf-8')
 status=R/'status/PROJECT_STATUS.md';s=status.read_text(encoding='utf-8-sig');assert 'run_054' not in s;prefix='# SMALL-PUNCH 项目状态\n';assert s.startswith(prefix)
 status.write_text(prefix+'\n## 当前状态 — run_054（'+now[:10]+'，Asia/Shanghai）\n\n**WARNING / OFFLINE_CONFOUNDING_ASSESSMENT_COMPLETE。** 指定真实FE数据与哈希已核验，MAIN完成高应变割线、旧参数方向与冻结残差的离线比较。跨实验基点/时间控制不同，正式联合Jacobian/Fisher信息/可识别性NOT_EVALUABLE；仅支持探索性混淆假设。见[私有报告](../run/run_054/artifacts/private/confounding_report.md)。当前新增预算0；未来同点识别最小设计仅属未授权建议，无新FE、输入、入队、拟合或优化，完成后停止。历史冻结及独立验证边界保留。\n\n'+s[len(prefix):],encoding='utf-8')
 manifest=A/'manifest.json';save(manifest,{'run_id':'run_054','files':[{'path':rel(f),'role':'analysis code','sha256':sha(f),'visibility':'PUBLIC_CODE'} for f in sorted(A.glob('*.py'))]+[{'path':rel(report),'role':'independent scientific assessment','sha256':sha(report),'visibility':'PRIVATE'},{'path':rel(em),'role':'private evidence hash list','sha256':sha(em),'visibility':'PRIVATE'}]})
 old=(RUN/'run.json').read_bytes();write(RUN/'checkpoints/run_before_complete.json',old.decode());j=json.loads(old);j.update(status='WARNING',end_time=datetime.now().astimezone().isoformat(),outcome='OFFLINE_CONFOUNDING_ASSESSMENT_COMPLETE',inputs=[{'path':'run/run_020/artifacts/prepared_batch.json','role':'historical local sensitivity design','sha256':sha(R/'run/run_020/artifacts/prepared_batch.json')},{'path':'run/run_051/artifacts/comparison_contract.json','role':'frozen response and Loss binding','sha256':sha(R/'run/run_051/artifacts/comparison_contract.json')},{'path':rel(P/'source_hash_manifest.json'),'role':'private source identities','sha256':sha(P/'source_hash_manifest.json')}],outputs=[{'path':rel(report),'role':'scientific report','sha256':sha(report)},{'path':rel(em),'role':'evidence list','sha256':sha(em)},{'path':rel(manifest),'role':'artifact index','sha256':sha(manifest)}],validation=[{'check':'existing source identity','status':'PASS','evidence':rel(P/'source_hash_manifest.json'),'scope':f'{len(sources)} bounded existing files, no original changed'},{'check':'math tests','status':'PASS','evidence':rel(P/'synthetic_tests.json'),'scope':'9 synthetic vector tests plus actual source-array and Loss-identity crosschecks'},{'check':'formal joint identifiability gate','status':'NOT_EVALUABLE','evidence':rel(P/'input_compatibility_audit.json'),'scope':'no common-D01 sigma_y/n perturbations with same numerical contract'},{'check':'Hub audit chain','status':'PASS','evidence':rel(P/'agenthub_completion_receipt.json'),'scope':'public API task/artifact/message/completion'}],new_FE=0,new_queue=0,material_refit=False,agenthub_task_id=tid)
 tmp=RUN/'run.json.tmp';tmp.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');json.loads(tmp.read_text(encoding='utf-8'));os.replace(tmp,RUN/'run.json')
 for src in sources:assert sha(R/src['path'])==src['sha256']
 private=[f for f in P.rglob('*') if f.is_file()]
 for f in private:assert subprocess.run(['git','check-ignore','--quiet','--',str(f)],cwd=R).returncode==0,str(f)
 assert not list(RUN.rglob('*.inp')) and not list(RUN.rglob('*.odb'))
 save(RUN/'checkpoints/completed.json',{'at':datetime.now().astimezone().isoformat(),'git_branch':git('branch','--show-current'),'git_head':git('rev-parse','HEAD'),'git_working_tree':git('status','--short'),'report_sha256':sha(report),'protected_sources_verified_unchanged':len(sources),'private_files_ignored':len(private),'Hub_task_id':tid,'Hub_state':hub.task(tid)['execution_state'],'stopped':True,'new_FE':0,'new_queue':0})
 print(json.dumps({'run_id':'run_054','status':'WARNING','report':str(report),'sha256':sha(report),'formal_joint':'NOT_EVALUABLE','Hub_task':tid,'verified_sources':len(sources),'private_files':len(private),'newFE':0}))
if __name__=='__main__':main()
