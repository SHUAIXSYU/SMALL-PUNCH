"""Finalize feature-identification evidence; no solver or material optimization."""
from pathlib import Path
import csv,json,hashlib,sys,subprocess,os
from datetime import datetime,timezone,timedelta
import numpy as np
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_055';A=RUN/'artifacts';P=A/'private';sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
from feature_core import NAMES
def now():return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def write(p,s):
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
def rel(p):return p.relative_to(R).as_posix()
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def main():
 at=now();inv=read(P/'sample_inventory.json');desc=read(P/'descriptive_summary.json');checks=read(P/'independent_analysis_checks.json');metrics=rows(P/'inverse_cv_metrics.csv');mm={x['model']:x for x in metrics};strict={x['model']:x for x in rows(P/'strict24_cv_metrics.csv')};application=rows(P/'experimental_feature_application.csv');sources=read(P/'inventory_metadata_addendum.json')['source_manifest'];tests=read(P/'synthetic_tests.json');assert tests['returncode']==0 and checks['OOF_group_leakage_check']=='PASS'
 for s in sources:assert sha(R/s['path'])==s['sha256'],s['path']
 completion=read(P/'cv_completion.json');assert sha(P/'frozen_FE_only_inverse_models.json')==completion['frozen_model_sha256'] and sha(P/'inverse_cv_results.csv')==completion['inverse_cv_sha256']
 session=read(P/'hub_session.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);hub.heartbeat(session['lease']);assert hub.verify_chain()
 # Complete the variant CSV with the same inventory-only corrections, preserving pre-CV input identities.
 original=P/'execution_variant_inventory.csv';(P/'checkpoints/execution_variant_inventory_initial.csv').write_bytes(original.read_bytes());rr=rows(original);updated={x['sample_id']:x for x in rows(P/'fe_sample_inventory.csv')}
 for x in rr:
  if x['sample_id'] in ['L01','L02','L03','L04']:
   x['loss']=updated[x['sample_id']]['loss'];x['odb_sha256']=updated[x['sample_id']]['odb_sha256'];x['loss_version']='run017-exploratory-fd-v1'
 temp=P/'execution_variant_inventory.csv.tmp'
 with temp.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in rr for k in row)));w.writeheader();w.writerows(rr)
 os.replace(temp,original)
 future={'status':'PROPOSED_ONLY_NO_INPUT_OR_AUTHORIZATION','current_new_FE_budget':0,'recommended_minimum_targeted_FE':4,'purpose':'prospective same-model feature-map discrimination and held-out recovery, not minimize SPT Loss','anchor':'existing I06: sigma236.49902622197678MPa,n.0968,initial.001,max.0025,time1,min1e-12,inc999999','normalization':'x=ln(sigma/150)/ln(1000/150);y=(n-.02)/.48','illustrative_design':[{'axis':'x','offset':-.025},{'axis':'x','offset':.025},{'axis':'y','offset':-.025},{'axis':'y','offset':.025}],'new_center_needed':False,'why_anchor':'interior legal parameters, existing comparable center, one endpoint of the empirical D11/I06 ambiguity pair; avoids D01 lower-bound crossing','freeze_before_future_FE':['allrun055 inverse model files and metrics','exact future parameters/material tables,step controls and identities','fixed feature and full241grid definitions','same-target normalized finite-difference columns and prospective prediction scores','feature residual/angle/conditioning analysis with explicit scaling and no noise-FIM claim'],'evaluation':'Use frozen run055 models to predict all4 before retraining; compare known FE labels, feature secants, symmetry and ambiguity. New points are a genuinely prospective local test of these frozen models, not proof of global inverse validity.','stopping':['any identity,failed/incomplete-window,material-coverage or unexplained accepted-state numerical anomaly -> stop, no retry','new feature separation comparable to numerical-setting changes -> UNRESOLVED, not unique-identification claim','strong secant asymmetry or near-dependent directions -> retain ambiguity, do not consume optimization budget','if low-n numerical block persists, do not infer n<.08 performance from successful high-n samples'],'limits':['algebraically two one-sided points can form columns, but four symmetric points are the minimum recommended scientifically interpretable check here','does not construct a D01 Jacobian','does not solve high-strain material form or clamping uncertainty','four local points are insufficient to validate a global formula; broader independent coverage needs a separate design and budget'],'no_new_candidate_generation':True}
 save(P/'future_targeted_FE_design.json',future)
 summary={'at':at,'status':'PARTIAL','sample_counts':{'historical30':30,'historical_scoreable':24,'historical_unscoreable':6,'additional_unique_standard_points':6,'audited_unique_standard_points':36,'primary_comparable':25,'primary_addition':'C200 fromrun029','coarse_exclusions':5,'refined_duplicates':2,'nonstandard_envelopes':2},'primary_numeric':'run030-standard-m0025-hollomon-v1;initial.001,max.0025','loss_contract':'run017-exploratory-fd-v1','CV':'outer unique-parameter LOO25;innerLOO training-only standardization/feature/lambda selection;strict24fixed-ridge check','metrics':metrics,'explicit_decisions':{'A':'supports an FE-self-consistency prototype, not a reliable material identification formula','B':'two fixed loads not stable enough across sparse domain; sigmaMAE47.39MPa,nMAE.0526 and extrapolation failure','C':'fixed5 improves ridge relative tofixed2, but NN and nested4 sigma performance do not improve monotonically','D':'fullcurve ridge outperforms small-feature ridge on same heldout groups; this is empirical recovery-error difference, not quantified mutual/Fisher information','E':'early loads carry relatively stronger sigma association; later force/work relatively stronger n, but both remain mixed; nested pair F.15/F.30 selected in25/25trainingfolds','F':'D11/I06 meet predeclared approximate-force ambiguity rule; no strict nonuniqueness proof; D01/I08 remain competing low-Loss points but do NOT meet this pairwise force threshold','G':'no experimentally validated/stable quantitative material formula','H':'coverage gap especially n<.08, nonrandom failure filtering, numerical sensitivity and feature redundancy plus material/BC uncertainty','I':'current0FE; conditional4prospective local points aroundI06, no input preparation now','J':'continue as interpretable feature/identification research and compact emulator, not replace fullcurve or claim unique material recovery'},'formal_D01_Jacobian':'NOT_EVALUABLE','formal_Fisher_information':'NOT_EVALUABLE','formal_parameter_CI':'NOT_EVALUABLE','experimental_application':application,'new_FE':0,'new_queue':0,'new_material_parameters_optimized':False,'tensile_data_accessed':False,'original_frozen_predictions_modified':False}
 save(P/'scientific_decision.json',summary)
 ratio=lambda a,b,key:float(mm[a][key])/float(mm[b][key])
 comparison=['# 特征反演与全曲线基线：真正的留出FE参数恢复','',
 '同25个唯一参数组、同外层留一、同训练折内标准化；Ridge超参数和嵌套特征均由各训练折的内层LOO确定。以下不是训练R²，也不是独立SA508材料误差。完整曲线基线是241点逆回归/最近邻，不是重新运行FE最小Loss优化。','',
 '|模型|σ MAE/MPa|σ RMSE/MPa|n MAE|n RMSE|σ MAPE|n MAPE|越参数边界次数|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for name in ['mean','median','two_nn','two_ridge','five_nn','five_ridge','nested_two_ridge','nested_four_ridge','full_nn','full_ridge']:
  m=mm[name];comparison.append(f'|{name}|{float(m["sigma_MAE_MPa"]):.4f}|{float(m["sigma_RMSE_MPa"]):.4f}|{float(m["n_MAE"]):.6f}|{float(m["n_RMSE"]):.6f}|{float(m["sigma_MAPE_percent"]):.2f}%|{float(m["n_MAPE_percent"]):.2f}%|{m["parameter_bounds_violations"]}|')
 comparison += ['',
 '固定2=F(.15),F(.90)；固定5=F(.15),F(.30),F(.60),F(.90),W(0–1.2)。Nested2在每个训练折从28个载荷对选择，Nested4只在该折内再加两项。两个nested程序的测试点均未参与筛选。',
 f'固定2相对全曲线Ridge的σ/n MAE分别为{ratio("two_ridge","full_ridge","sigma_MAE_MPa"):.3f}/{ratio("two_ridge","full_ridge","n_MAE"):.3f}倍；固定5为{ratio("five_ridge","full_ridge","sigma_MAE_MPa"):.3f}/{ratio("five_ridge","full_ridge","n_MAE"):.3f}倍。固定2的σ/n RMSE为全曲线{ratio("two_ridge","full_ridge","sigma_RMSE_MPa"):.3f}/{ratio("two_ridge","full_ridge","n_RMSE"):.3f}倍；固定5为{ratio("five_ridge","full_ridge","sigma_RMSE_MPa"):.3f}/{ratio("five_ridge","full_ridge","n_RMSE"):.3f}倍。这是此模型/样本上的经验预测损失，不是丢失了多少bit或正式Fisher信息。',
 '最近邻中五特征反而比两特征差，完整曲线NN也未接近Ridge表现；“更多特征必定更好”未获支持。Nested4相对Nested2虽改善n，但σ误差上升。不能按外层测试结果反复增加复杂度或挑一条“完美公式”。',
 '全曲线Ridge的原始输入241维大于样本数，依靠正则化的有限秩实现；最终全部FE拟合有效自由度约15.61，固定5约3.05，固定2约1.88。它是合理但复杂度更高的基线，不是纯粹的信息论比较。最终full/five/nested的lambda触及预设下限1e-4，保留边界风险，本轮不看分数后扩大调参网格。',
 '严格历史24点子集复算：','',
 '|模型|σ MAE/MPa|n MAE|σ RMSE/MPa|n RMSE|','|---|---:|---:|---:|---:|']
 for name in ['two_ridge','five_ridge','full_ridge']:
  m=strict[name];comparison.append(f'|{name}|{float(m["sigma_MAE_MPa"]):.4f}|{float(m["n_MAE"]):.6f}|{float(m["sigma_RMSE_MPa"]):.4f}|{float(m["n_RMSE"]):.6f}|')
 comparison += ['',
 '剔除额外中心后结论方向保持；不能把这24点子集重算当作新的独立试验。',
 '最差情形：D05真值σ817.023544MPa,n.430998143，固定2预测σ580.2412MPa,n.6710303；固定5预测664.3178MPa,.5984607。保留原始越界预测，没有裁剪。完整曲线预测608.6958MPa,.4200675，σ仍偏低208.3278MPa。全曲线n最大绝对误差.0360786发生DE03。样本边界/缺邻点对σ恢复仍不稳。',
 '数值控制审查：将D01/I08细化曲线送入其参数组完全留出的同一模型，全曲线Ridge预测σ变化−.348/−1.579MPa，n变化+.005971/+.007341。后者已是全曲线平均n MAE的约49%/60%；小载荷数值差也可能放大到逆预测。固定2/5变化较小，但仅两个重复点，不能作为全域数值误差上界。',
 'FE设计不是随机样本，6个不评分点均n<.043；可比成功样本没有n<.08，排除并非随机。模型与评估仅条件于这批成功样本，不能覆盖原探索域。LOO折训练集重叠，未提供形式统计置信区间或总体算法优越性结论。','']
 write(P/'feature_vs_full_curve_comparison.md','\n'.join(comparison))
 redundancy=['# 特征冗余与关联限制','',
 '17个预设特征包括8载荷、4割线、5面积。割线是既有载荷端点的精确线性组合，总面积等于4段面积之和（实测最大绝对差8.88e-16J）。标准化特征矩阵只有12个非零数值奇异方向，不能将17项叫17个独立观测；这个样本矩阵线性秩也不是材料参数维数。',
 '136对中90对|Pearson|>.98。高冗余反映共同幅值和曲线形状，不能由此说所有弱方向无用，也不能由单个高相关系数证明参数可识别。',
 'F(.15)与σ/n的Pearson约.7868/.5211，F(1.2)约.4634/.7824，总功约.5327/.7469；有早段相对偏σ、后段偏n的趋势，但控制另一参数后的早段相关也同时很高，材料响应并不分离。设计x/y的Pearson为−.1366，仍存在非均匀覆盖、交互和低n失败选择偏差。散点、Spearman、部分相关及xy项系数均为描述性，不作因果或泛化结论。',
 'Nested2在25/25个外层训练折选择F(.15),F(.30)，给出队列内稳定选点线索，而非跨材料验证。Nested4在23折选择K(.15–.30)，它与F(.15),F(.30)精确线性相关；加上中段K(.60–.90)才引入不同响应组合。其最终4项只有3个独立线性测量，正则化几何也会随冗余列变化，不能将改善归于“四份独立信息”。',
 '曲率和弹塑转变位置只保留未平滑的割线变化诊断，标UNSTABLE，不进入反演。当前采样/接触压力建立造成的波动没有独立判据可区分成单轴屈服点。原曲线没有被平滑、修剪或移动零点。','']
 write(P/'feature_redundancy_report.md','\n'.join(redundancy))
 ident=['# 特征可识别性证据等级','',
 '**PARTIAL：可进行FE自洽参数恢复实验，未建立稳定材料定量公式。**','',
 '真实证据：25组同几何/物理骨架、同初始.001/最大.0025的唯一两参数点；24项来自run039/042，另1项来自run029中心。6个原null保留，不填惩罚。不把D01/I08精化重复作为新材料样本，不把H01/H02当普通(σ,n)样本。',
 '局部探索证据：旧run020/022的四扰动围绕200MPa,.1，初始.01/最大.1。固定F(.15),F(.90)的归一化2×2割线矩阵条件数13.5706；28个预设载荷对中最低为F(.15),F(.60)的11.7552。它们只是同旧基点的探索性割线，没有转移为D01处正式Jacobian，更没有根据它们在全数据筛最优后冒充独立CV。不同取点/权重改变条件数，数值更小不证明比完整曲线信息更多。',
 'D01正式局部Jacobian、正式Fisher信息、正式参数置信区间均NOT_EVALUABLE。还缺同D01基点、同数值控制下的σ/n扰动，以及用于正式Fisher解释的测量/模型误差定义。',
 '经验歧义：预先定义“两载荷或全曲线RMS差/F_ref<=.02且归一化参数距离>=.15”为描述性旗标，并非实验噪声。D11(156.474255MPa,.164096737)与I06(236.499026MPa,.0968)满足：参数距离.258962，两载荷差RMS27.11879N，全曲线26.48343N。不是精确同曲线或严格全局非唯一性证明。',
 'D01/I08虽各自低SPT Loss，但两载荷差62.36158N、全曲线差57.70788N，不满足上述阈值。低Loss相近不等于两FE曲线彼此几乎相同，不能预设这对一定是最歧义样本。所有300个样本对及阈值结果均保留。',
 '高应变包络仅作模型形式扰动诊断，冻结逆模型给出的表观参数随H01/H02改变，证明在普通两参数输入假设外有混淆风险；不能把该输出拿来评分原σ/n的“恢复错误”或拟合新材料。详见high_strain_nuisance_predictions.csv。',
 '本轮没有噪声扰动仿真，没有假设噪声数据充当实验测量精度；没有正式置信区间、唯一性或全域可识别性声明。下一轮最小建议为4个围绕既有I06、同控制的对称轴向点，专门测试特征映射/前瞻预测，见future_targeted_FE_design.json；当前预算仍0，未准备输入。','']
 write(P/'feature_identifiability_report.md','\n'.join(ident))
 report=['# run_055 — Feature-Based Hollomon Parameter Identification','',f'完成时间：{at}，Asia/Shanghai。总体：**WARNING / PARTIAL_FE_PARAMETER_RECOVERY_ONLY**。','',
 '## 科研结论','',
 '现有数据支持轻量特征反演原型，但不支持“两个载荷点即可稳定、唯一识别SA508本构”的定量经验公式。固定五特征的Ridge优于固定两特征，但完整241点Ridge保留了显著更好的FE参数恢复能力；最近邻没有随特征增加而稳定改善。数据覆盖、数值稳健性和独立材料信息均仍不足，继续增加模型复杂度不是本轮结论。','',
 '## A. 实际样本集合与质量','',
 '逐个核对run039的22点与run042的8点，而非照抄摘要：二者构成30个不同的物理参数组合，24个Loss非null、6个null，且与run049的24表/6排除表集合精确一致。null为D07,D09,D10,BO01,BO02,DE02。源INP/ODB/STA/MSG/DAT/LOG、参数/提取文件及哈希均做限定路径核验。D09沿用run038可读但数值不可评分的替代记录；run033原始中断保留在单独CSV，不把历史替代Job当第二个材料样本，也不声称重建了全部旧重提历史。',
 '完整指定样本盘点共36个唯一标准两参数组合：上述30＋run029中心C200＋旧L01–L04＋P01。C200是已通过相邻增量检查的200MPa,.1点，与主批初始.001/最大.0025一致，故主评估25点；旧四扰动与P01初始.01/最大.1，仅盘点和历史局部诊断，不进入同精度训练。另两份run045的D01/I08最大.00125是重复精化，不增材料样本数；H01/H02为非标准高段包络，只作材料形式扰动。',
 '主25组总时间1、最小增量1e-12、最大增量次数999999，非塑性/Static字段模型骨架完全相同，保留E210GPa、ν.3、几何/网格/接触/BC/加载与输出。每项完整FD均有身份可追溯的既有只读提取，不因“有ODB”便准入。软件完成、有警告、数值审核、可评分与物理有效分开；主组仍属WARNING/PROVISIONAL质量，不是整个参数域数值收敛认证。',
 '本轮实际观察σ范围150.41106–817.02354MPa、n范围.08–.46129871。原探索域150–1000MPa/.02–.50没有完整覆盖，6个不评分点全在n<.043，形成明显非随机过滤。结果不能外推到低n或高σ未覆盖角落。',
 'fe_sample_inventory.csv为最终完整字段清单；sample_inventory.json保留CV前固定队列与身份；inventory_metadata_addendum.json只补旧粗模型的已知Loss/ODB元数据，主训练IDs/矩阵和CV冻结哈希未变。不同版本保存在私有checkpoints，未改历史Run。','',
 '## B. 特征与评价协议','',
 '先写feature_protocol.md，随后才计算特征/CV。8固定位移载荷、4端点割线、5原始折线面积按用户指定范围提取。u=-U2、F=-RF2，m/N；坡度N/mm，面积J。积分在原始折线插入精确区间边界再梯形积分，是冲头外部功相关特征，不等于ALLPD。无外推、平滑、零点平移或删点。完整曲线241点为同一线性曲线在0–1.2mm上的固定采样。源339点SPT曲线和run017 Loss不变。',
 '10个预设模型分别使用均值/中位数、固定2/固定5/全曲线NN与Ridge、真正嵌套的2/4特征Ridge。归一化参数为固定物理域x(logσ),y(n)；每层训练折自己拟合输入标准化和截距。Ridge objective=sum误差²/N+lambda||B||²，候选lambda为1e-4/.01/1/100，内层按x/y等权MSE选。没有神经网络、高阶曲面或看失败后扩模型。',
 '25个唯一参数组逐一外层留出；每次24组训练，内部再LOO选择特征与lambda。保留250条外层预测、全部训练/测试ID和选择记录；重复精化从不跨训练/测试。没有训练R²充当预测精度。独立SVD公式重新核对全部250条预测，与生产实现最大物理预测差约2.57e-9。',
 '这是固定设计样本上的out-of-fold恢复，不是新的前瞻独立FE测试集。样本获取本身含DOE和SPT引导先导，非随机抽样；LOO训练集重叠，未给形式置信区间，也不声称单种子方法总体优越。','',
 '## C–G. 关联、冗余、恢复与信息差异','',
 '完整表与逐项解释见feature_parameter_correlations.csv、feature_partial_associations.csv、feature_redundancy_report.md、feature_identifiability_report.md及feature_vs_full_curve_comparison.md。主要结果：','',
 '|固定输入＋Ridge|σ MAE/MPa|σ RMSE/MPa|n MAE|n RMSE|','|---|---:|---:|---:|---:|']
 for name,label in [('two_ridge','F(.15),F(.90)'),('five_ridge','4载荷＋总面积'),('full_ridge','完整241点')]:
  x=mm[name];report.append(f'|{label}|{float(x["sigma_MAE_MPa"]):.4f}|{float(x["sigma_RMSE_MPa"]):.4f}|{float(x["n_MAE"]):.6f}|{float(x["n_RMSE"]):.6f}|')
 report += ['',
 '前期载荷对σ的关联相对较强、后期载荷/面积对n更强，但两者均参与所有响应。Nested2在所有25折内选F(.15),F(.30)，其σ/n MAE43.8935MPa/.044992；Nested4为45.2865MPa/.032343，σ并未随更多特征改善。四特征多数含一个与两载荷精确相关的斜率，因此不能把名义数量当独立信息。',
 '固定2/5相对全曲线Ridge的n MAE分别约4.33/2.76倍、σ MAE约1.87/1.66倍。这定量描述有限样本上的参数恢复误差差距，不是信息论损失。完整曲线的更多自由度可能使用接触/数值纹理，精化重复导致其n预测变化约.006/.0073，不能把较小CV误差直接等同更可靠材料信息。',
 'D11/I06是预设工程阈值下的一对经验歧义：差异80.0248MPa/.0672967，固定两载荷RMS差27.1188N，全曲线26.4834N。D01/I08并非此阈值下的同响应对；其全曲线差57.7079N，虽各自SPT Loss相近，不能先验当作曲线相同。正式D01局部Jacobian、Fisher信息、参数置信区间保持NOT_EVALUABLE。','',
 '## H. 冻结后实验SPT应用','',
 'CV完成和最终FE-only模型文件/hash冻结后，才提取已经用于反演的SPT特征。未按实验调整特征、模型、lambda或参数，不读取拉伸数据。以下是冻结模型的探索性输出，不是材料真值：','',
 '|模型|σ估计/MPa|n估计|适用域|','|---|---:|---:|---|']
 for name in ['two_ridge','five_ridge','full_ridge','nested_two_ridge','nested_four_ridge']:
  x=next(z for z in application if z['model']==name);report.append(f'|{name}|{float(x["sigma_y_estimate_MPa"]):.4f}|{float(x["n_estimate"]):.7f}|{x["applicability"]}|')
 report += ['',
 '输入特征的最近邻距离均不大、边际范围也未超出，并不保证联合逆预测有样本支持。固定5/全曲线/nested4的预测落出训练参数凸包，其中全曲线n约.0605低于训练最小.08，明确OUT_OF_DOMAIN；其他模型最多UNRESOLVED_NO_MATERIAL_VALIDATION。最近邻多数返回I08，只代表相应标准化距离，不能同D01的最小SPT Loss排序混为一谈。',
 'D01/I08既有候选参数及run046预测没有变化；本轮没有真实材料σ/n标签，不能计算实验参数误差，也不能将实验输入的回归输出叫独立验证成功。算法和样本获取已经涉及同一SPT研究目标，当前应用只能探索，不能充当新的验证集。','',
 '## A–J最终科研判定','']
 for key,val in summary['explicit_decisions'].items():report.append(f'- **{key}**：{val}')
 report += ['',
 '最小后续可解释设计建议为4个I06附近对称轴向点（归一化x/y各±.025），复用既有中心、保持同最大.0025和冻结物理/材料族。新点先只作为run055模型的前瞻外部测试，不重新训练后再宣称验证。它专门检查特征映射是否退化及对称性，不追求实验Loss下降；4个局部点并不足建立全域经验公式，也不生成D01处Jacobian。本轮只保存设计，无输入、预检、Queue或Solver。',
 '若目标是现实材料识别，优先补齐低n数值失效、高应变本构/夹具边界与测量不确定性的证据；不能将低维特征回归绕过这些问题。继续Feature-Based路线有价值，但应定位为可解释特征诊断与压缩代理，不宣称替代完整曲线、唯一反演或正式材料标定。','',
 '## 产物与审计','',
 '所需10项文档/CSV均在本目录：fe_sample_inventory.csv、feature_protocol.md、feature_matrix.csv、feature_parameter_correlations.csv、feature_redundancy_report.md、inverse_cv_results.csv、feature_identifiability_report.md、feature_vs_full_curve_comparison.md、scientific_report.md、evidence_manifest.json和AgentHub收据。',
 '图件：feature_locations.png；feature_scatter_sigma.png/feature_scatter_n.png；feature_redundancy_heatmap.png；inverse_cv_errors.png；true_vs_heldout_parameters.png；parameter_ambiguity_D01_I08.png。歧义阈值及真正满足的D11/I06另见parameter_ambiguity_pairs.csv，不能由所画D01/I08案例取代全部比较。',
 '10项合成特征/单位/积分/折内标准化/Ridge/NN测试通过；250项真实预测独立公式复核通过；25折参数组无泄漏，严格24点复算与主结论方向一致。419项指定源记录前后hash一致，私有结果均Git忽略。初次盘点脚本遇旧/新记录字段差异，按真实参数/结果来源核验修复，诊断保留，不是FE重试。',
 'run046冻结预测、run025历史BLOCKED及run047/run048正式NOT_EVALUABLE均不变。保留run015历史信息暴露，不能称从未解盲。本轮未读拉伸数据或旧泄漏分析，不用它们选择特征/调参；未来若用于模型开发则必须归作开发/校准资料，不得再次标作未用验证集。',
 'MAIN通过正式AgentHub登记独立任务、证据、结果和科学WARNING。写入消息不表示其他会话自动收到或已读。当前工作完成后停止，新增FE、Datacheck、入队、优化、材料拟合、共享环境变更和Git提交均0。','']
 reportpath=P/'scientific_report.md';write(reportpath,'\n'.join(report))
 save(P/'resolved_schema_diagnostic.json',{'recorded_at':now(),'initial_command':'build_inventory.py','initial_returncode':1,'error':'KeyError inp_sha256 on pilot main-analysis row (row schema differs from DOE); no scientific source inconsistency','resolution':'Use hash-bound result/diagnostic/parameter files as actual source; optional duplicated row hashes checked only when present; inventory passed415 original source checks and4 coarse ODB addenda','FE_attempts_or_input_changes':0})
 em=P/'evidence_manifest.json';save(em,{'run_id':'run_055','at':now(),'files':[{'path':rel(f),'sha256':sha(f),'bytes':f.stat().st_size,'visibility':'PRIVATE'} for f in sorted(P.rglob('*')) if f.is_file() and f.name!='hub_session.json'],'exclusions':'self,live identity/lease,laterHubreceipt and closeout checkpoint'})
 artifacts=[];tid=session['task_id']
 for file in [reportpath,P/'fe_sample_inventory.csv',P/'feature_protocol.md',P/'feature_matrix.csv',P/'feature_parameter_correlations.csv',P/'feature_redundancy_report.md',P/'inverse_cv_results.csv',P/'feature_identifiability_report.md',P/'feature_vs_full_curve_comparison.md',P/'independent_analysis_checks.json',P/'scientific_decision.json',em]:artifacts.append(hub.artifact(tid,session['identity']['agent_id'],file,{'run':'run_055','scope':'FE-only grouped nested CV and post-freeze exploratory SPT input; no tensile/materialtruth','primary_count':25,'no_FE':True},version='run055-v1'))
 result={'run_id':'run_055','status':'WARNING/PARTIAL','report_path':rel(reportpath),'report_sha256':sha(reportpath),'evidence_manifest':rel(em),'evidence_manifest_sha256':sha(em),'primary_unique_count':25,'historical_counts':'24 scoreable plus6 null =30','OOF_predictions':250,'local_D01_Jacobian_FIM_CI':'NOT_EVALUABLE','best_full_curve_MAE':{'sigma_MPa':float(mm['full_ridge']['sigma_MAE_MPa']),'n':float(mm['full_ridge']['n_MAE'])},'current_FE_budget':0,'future_proposal_FE':4,'recommendation':'Continue interpretation/identifiability research; no validated two-feature material formula or automatic new computation'}
 hub.message(tid,session['identity']['agent_id'],'MAIN',result,'run055-feature-identification-main-result-v1');hub.finish(session['lease'],result,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain();save(P/'agenthub_completion_receipt.json',{'at':now(),'task_id':tid,'task':hub.task(tid),'artifacts':artifacts,'audit_chain_verified':True,'message_is_not_automatic_chat_wakeup':True})
 write(RUN/'summary.md','# run_055 — Feature-Based Hollomon Parameter Identification\n\n**WARNING / PARTIAL_FE_PARAMETER_RECOVERY_ONLY。** 实际核对历史24可评分＋6null集合；追加已完成同控制中心后，以25个唯一标准两参数点进行统一特征、分组嵌套留一和全曲线基线比较。H01/H02、重复精化与粗增量另列，不混入训练。\n\n完整[私有科研报告](artifacts/private/scientific_report.md)、[特征与全曲线比较](artifacts/private/feature_vs_full_curve_comparison.md)、[可识别性](artifacts/private/feature_identifiability_report.md)、[证据清单](artifacts/private/evidence_manifest.json)。仅支持FE自洽恢复原型，尚无稳定材料定量公式；正式D01局部Jacobian/FIM/置信区间NOT_EVALUABLE。\n\n实际完成250条外层留出预测、严格24点复核、10项合成测试和独立数学检查；SPT只在模型冻结后探索性应用，未用拉伸数据。AgentHub任务完成WARNING。无新FE、输入、入队、材料拟合、BO/DE/RL或Git提交；历史预测/验证边界保留，当前计算预算0，完成后停止。\n')
 index=R/'run/README.md';s=index.read_text(encoding='utf-8-sig');assert '## run_055' not in s;index.write_text(s+'\n\n## run_055 — 特征反演与全曲线留出对照\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_055 | 唯一样本盘点、固定特征、嵌套CV及识别歧义 | WARNING / PARTIAL_FE_PARAMETER_RECOVERY_ONLY | [summary](run_055/summary.md) |\n\n只支持有限样本FE自洽恢复，不构成可靠材料公式；当前新FE预算0，无输入/入队/优化，完成后停止。\n',encoding='utf-8')
 sp=R/'status/PROJECT_STATUS.md';s=sp.read_text(encoding='utf-8-sig');prefix='# SMALL-PUNCH 项目状态\n';assert s.startswith(prefix) and 'run_055' not in s
 sp.write_text(prefix+'\n## 当前状态 — run_055（'+at[:10]+'，Asia/Shanghai）\n\n**WARNING / PARTIAL_FE_PARAMETER_RECOVERY_ONLY。** 唯一样本与历史24/6集合已核对，25组同数值控制FE完成固定/嵌套特征与全曲线留出比较，真实预测/泛化限制见[私有科研报告](../run/run_055/artifacts/private/scientific_report.md)。少量特征未保留全曲线恢复能力，正式局部指标NOT_EVALUABLE；SPT冻结后应用仅探索性。无新FE、INP、入队、材料拟合或优化，当前预算0，完成后停止。保留历史冻结及独立验证边界。\n\n'+s[len(prefix):],encoding='utf-8')
 manifest=A/'manifest.json';save(manifest,{'run_id':'run_055','files':[{'path':rel(f),'role':'offline analysis code','sha256':sha(f),'visibility':'PUBLIC_CODE'} for f in sorted(A.glob('*.py'))]+[{'path':rel(reportpath),'role':'complete private scientific report','sha256':sha(reportpath),'visibility':'PRIVATE'},{'path':rel(em),'role':'private evidence list','sha256':sha(em),'visibility':'PRIVATE'}]})
 j=read(RUN/'run.json');(RUN/'checkpoints/run_before_complete.json').write_bytes((RUN/'run.json').read_bytes());j.update(status='WARNING',end_time=now(),outcome='PARTIAL_FE_PARAMETER_RECOVERY_ONLY',inputs=[{'path':rel(P/'sample_inventory.json'),'role':'CV-frozen sample inventory','sha256':sha(P/'sample_inventory.json')},{'path':rel(P/'feature_protocol.md'),'role':'pre-CV protocol','sha256':sha(P/'feature_protocol.md')},{'path':rel(P/'inventory_metadata_addendum.json'),'role':'source hashes and metadata-only addenda','sha256':sha(P/'inventory_metadata_addendum.json')}],outputs=[{'path':rel(reportpath),'role':'scientific report','sha256':sha(reportpath)},{'path':rel(em),'role':'evidence hash list','sha256':sha(em)},{'path':rel(manifest),'role':'artifact index','sha256':sha(manifest)}],validation=[{'check':'sample_source_audit','status':'PASS','evidence':rel(P/'independent_analysis_checks.json'),'scope':'24/6 disjoint sets,25 comparable unique groups,419 source records'},{'check':'nested_CV_integrity','status':'PASS','evidence':rel(P/'outer_fold_details.json'),'scope':'training-only transforms/selection,250 independent SVD-checked predictions'},{'check':'synthetic_math','status':'PASS','evidence':rel(P/'synthetic_tests.json'),'scope':'10 feature/unit/inverse/CV tests'},{'check':'real_material_identification','status':'PARTIAL','evidence':rel(P/'scientific_decision.json'),'scope':'FE self-consistency only; no validated material formula'},{'check':'local_Jacobian_FIM_CI_D01','status':'NOT_EVALUABLE','evidence':rel(P/'feature_identifiability_report.md'),'scope':'no matched local sigma/n perturbations at D01'}],errors=[{'code':'HISTORICAL_ROW_SCHEMA_VARIATION','severity':'RESOLVED','message':'Initial inventory parser expected redundant hash fields in pilot row; actual hash-bound result/parameter provenance verified instead. No source changed.','evidence':rel(P/'resolved_schema_diagnostic.json')}],agenthub_task_id=tid,new_FE=0,new_queue=0,new_INP=0,material_refit=False,tensile_content_read=False)
 tmp=RUN/'run.json.tmp';tmp.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');read(tmp);os.replace(tmp,RUN/'run.json')
 for src in sources:assert sha(R/src['path'])==src['sha256']
 private=[f for f in P.rglob('*') if f.is_file()]
 for f in private:assert subprocess.run(['git','check-ignore','--quiet','--',str(f)],cwd=R).returncode==0,str(f)
 assert not list(RUN.rglob('*.inp')) and not list(RUN.rglob('*.odb'))
 save(RUN/'checkpoints/completed.json',{'at':now(),'git_branch':git('branch','--show-current'),'git_head':git('rev-parse','HEAD'),'working_tree':git('status','--short'),'report_sha256':sha(reportpath),'private_files_ignored':len(private),'protected_sources_verified':len(sources),'Hub_task_state':hub.task(tid)['execution_state'],'Hub_task_id':tid,'stop':'No next-stage or FE action authorised','new_FE':0,'new_queue':0})
 print(json.dumps({'run':'run_055','status':'WARNING/PARTIAL','report':str(reportpath),'report_sha256':sha(reportpath),'Hub_task':tid,'samples':25,'OOF':250,'private_files':len(private),'new_FE':0}))
if __name__=='__main__':main()
