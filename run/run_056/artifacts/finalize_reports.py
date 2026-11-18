"""Final Git and prospective-science reports; no FE/input generation."""
from pathlib import Path
import json,hashlib,csv,subprocess,os,sys
from datetime import datetime,timezone,timedelta
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_056';A=RUN/'artifacts';P=A/'private';sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=R,text=True).strip()
def save(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def write(p,s):
 with p.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
def rel(p):return p.relative_to(R).as_posix()
def main():
 at=now();gb=read(P/'git_before.json');gv=read(P/'git_hygiene_verified.json');rev=read(P/'run055_recheck.json');aud=read(P/'low_n_and_I06_audit.json');contract=read(P/'prospective_design_contract.json');signals=read(P/'signal_size_estimates.json');sources=read(P/'source_manifest.json')['sources'];base=aud['I06'];assert read(P/'design_tests.json')['returncode']==0
 for src in sources:assert sha(R/src['path'])==src['sha256'],src['path']
 for model in gb['target_CAE_models']:assert (R/model['path']).is_file() and sha(R/model['path'])==model['sha256']
 assert sha(R/'.gitignore')==gv['gitignore_sha256'] and git('rev-parse','HEAD')==read(RUN/'checkpoints/start.json')['git']['head']
 assert set(git('diff','--cached','--name-status').splitlines())=={'D\t'+m['path'] for m in gb['target_CAE_models']}
 assert not git('ls-files','--','*.cae','*.cae.*','*.odb','*.sim','*.lck')
 assert subprocess.run(['git','diff','--check','--','.gitignore'],cwd=R).returncode==0
 assert subprocess.run(['git','diff','--cached','--check'],cwd=R).returncode==0
 ss=read(P/'hub_session.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);hub.heartbeat(ss['lease']);assert hub.verify_chain()
 gitreport=['# run056 Git治理报告','',f'记录时间：{at}。**PASS：仅声明当前忽略规则与索引治理范围。**','',
 'Task A在科研复核之前完成。修改的是根.gitignore，未手工编辑.git内部数据库。原工作树已有project.db、Run索引和项目状态改动，均保留；开始时暂存为空、无冲突索引，两份目标CAE的工作树/index/HEAD一致。','',
 '追加大小写兼容的CAE与自动备份规则：*.[cC][aA][eE]、*.[cC][aA][eE].*；追加结果/索引文件.fil、.sel、.odb_f；增强原.prt/.res/.stt/.mdl/.pac/.abq/.simdir规则的大小写保护。ODB、SIM、LCK原有规则保留，私有资料、materials/Materials、私有证据、Solver工作目录和缓存的原规则逐行保持。',
 '没有全局忽略.inp/.py/.jnl/.md/.json，也未全局忽略.dat/.log/.sta/.msg：审计发现这些扩展名中存在已追踪的Sanity诊断和run009证据，不能误伤。新.fil/.sel/.odb_f在审计时无已追踪文件。','',
 '通过git rm --cached -- <exact paths>仅解除以下2项索引追踪，本地未删除：','']
 for m in gb['target_CAE_models']:gitreport.append(f'- {m["path"]}：{m["bytes"]} bytes；SHA-256 {m["sha256"]}，操作前后完全一致。')
 gitreport += ['',
 'Git显示暂存D仅表示下一次提交将不再追踪，并非本地模型被删。当前暂存只有这2个获准删除条目，.gitignore修改尚未提交；没有commit/push/reset/clean或历史重写。历史提交里的CAE旧版本仍在，当前未做历史清洗。',
 '26项路径规则探针通过：新CAE、备份、二进制、私有文件被排除；普通源码、输入、协议、配置和通用诊断日志仍可纳入版本管理。探针没有创建CAE或其他测试模型。当前tracked集合等于原HEAD文件集合精确减去2个CAE；其余索引条目完整。git diff --check及暂存检查通过。',
 '最终本轮新增修改为.gitignore、Run056及Run索引/项目状态；原有project.db等用户改动没有清理、覆盖或暂存。证据见git_before.json、gitignore_before.txt、git_hygiene_verified.json与最终Git检查点。','']
 write(P/'git_hygiene_report.md','\n'.join(gitreport))
 protocol=['# I06四点前瞻性检验协议 — v2，未来FE输出前冻结','',f'冻结时间：{contract["frozen_at"]}；权威机器契约：prospective_design_contract.json，SHA-256 {sha(P/"prospective_design_contract.json")}。当前FE授权0，候选均无Job/INP/hash/工作目录，不是已准备批次。','',
 '## 基准资格与边界','',
 'I06：σy236.49902622197678MPa、n.0968、x=.24、y=.16。源INP、ODB与参数完整hash绑定于契约。单次两阶段成功，439接受增量/18拒绝/18cutback，完整440点FD到1.2mm；PEEQ .7027503848<.85复核线<.9表末。接受trial仅一条ZERO MOMENT，无接受态严重警告/反力回退，原run030门控无阻塞项。',
 '因此仅判定条件性探索锚点合适，不宣告I06自身时间步精度已验证。其历史Runner进程证明缺口、DAT tracking提示和接触压力转变仍保留。若要求已经独立精化验证的严格精度基准，则I06不具备；可考虑已有run045精化I08，必须另议基点与最大.00125合同，不能擅自替换。本轮不生成或执行任何模型。','',
 '## 参数与材料/数值固定','',
 'x=ln(σy/150)/ln(1000/150)，y=(n−.02)/.48，hx=hy=.025。对数σ坐标对称不等于MPa算术对称。四个参数完整精度见CSV/JSON；均在150–1000MPa和.02–.50内，不与旧点重复。n负臂.0848低于局部I06、略超当前联合训练凸包，但仍高于成功样本n最小.08；其他三臂在凸包内。','',
 '|设计ID|σy/MPa|n|x|y|','|---|---:|---:|---:|---:|']
 for p in contract['points']:protocol.append(f'|{p["design_id"]}|{p["sigma_y_mpa"]:.16g}|{p["n"]:.16g}|{p["x"]:.6f}|{p["y"]:.6f}|')
 protocol += ['',
 '保留I06物理骨架、E210GPa、ν.3、run007候选真总应变Hollomon定义和塑性表0–.9；relative_tolerance=.001，行数按既有生成器自适应，不能强制等于I06的34行。未来只允许对应σy/n材料行变化，几何/网格/接触/摩擦/BC/加载/输出不变。生成器与源参数/INP SHA已绑定。',
 'Abaqus/Standard2024，初始.001、最大.0025、最小1e-12、time1、inc999999、14CPU0GPU。不能悄悄采用.00125然后与旧I06拼接。若研究决定另换数值设置，必须另冻结合同和同精度基准，不能默认追加计算。','',
 '## 评价A：局部响应可区分性','',
 '取固定241点0–1.2mm，u=-U2、F=-RF2，无外推/平滑/零点移动/删点。沿用run055的8载荷/4割线/5原始折线面积及单位。主比较固定2[F.15,F.90]、固定5[F.15,F.30,F.60,F.90,Wtotal]、全241曲线；次级早期2[F.15,F.30]和独立3[F.15,F.30,K.60-.90]事先列入，不能看结果后选择最有利者。',
 '定义Jx=(φSY+−φSY−)/.05，Jy=(φN+−φN−)/.05。参数列用上述固定x/y；载荷除Fref1428.9N，割线除Fref/1.2mm，面积除Fref×.0012m，各view行再除sqrt(m)。不得把标准化当真实噪声协方差。SVD取2范数条件数smax/smin；数值秩容差需记录（例如max(shape)×机器epsilon×smax），代数满秩不等于实际可识别。',
 '保留两列范数、余弦/夹角、奇异值、条件数、各位移分段和相对数值变化量级。每轴计算正/负单边割线及E=(φ++φ−)/2−φ0、O=(φ+−φ−)/2、η=||E||/||O||。η>.20、|cos|≥.98、κ≥20或弱方向响应RMS≤2N只触发工程警示，不是实验噪声界或识别定理。',
 '只有一个hx/hy，正式步长收敛性NOT_EVALUABLE；两侧不对称可检验有限幅风险，但不能替代h/2检验。不得自动加点或缩步。D01/I08观察到的细化变化只能作为带来源参考，不能当I06/新点数值误差上界。没有可靠观测/模型误差协方差，不形成正式Fisher置信区间。','',
 '## 评价B：冻结逆模型的前瞻性参数恢复','',
 f'直接使用run055冻结模型文件 SHA-256 {contract["frozen_models"]["frozen_inverse_models_sha256"]}，训练数据产生于run055之前。主模型two_ridge/five_ridge/full_ridge，次模型为其余原已冻结模型。所有均使用原均值、尺度、系数、特征和lambda；四点B评价全部完成前，禁止重训、重标准化、筛特征或调参。',
 '每点原始未裁剪预测、MPa/n绝对与相对误差、x/y误差、四点MAE/RMSE/最大误差、适用域旗标均输出。预测输入是实际未来FD，不将本轮响应量级估计冒充FE结果。',
 '加入常数I06基线。E_local=sqrt(mean(((qhat−qtrue)/h_q)^2))，平均覆盖4点×2坐标；常数I06的E_local=sqrt(.5)。本轮预注册的局部分辨工程目标：四点每坐标误差≤.0125（半个设计步长）、活动轴变化方向正确，且E_local严格优于常数I06。它不是用户材料验收指标/统计显著性。原草案10%σ/.02n过宽，会让常数I06全部通过，已在任何未来输出出现之前经sanity检查替换，保留草案检查点。',
 '另报model(newFD)−model(I06FD)相对真实参数扰动的增量预测误差，用于区分基准偏差与变化分辨能力；绝不据此重新居中、校准或替换原始预测。A的矩阵分离与B的预测精度分别给结论：A较好不能自动证明B好，B局部误差低也不证明唯一性。四点都近I06，只能检验局部，不代表全域泛化。','',
 '## 准入、停止和授权','',
 '未来完整输入/产物/尝试身份、DC成功后Full成功、完整窗口、PEEQ<.9等是硬门控。PEEQ≥.85、拒绝>50或拒绝/接受>10%、墙钟>20min触发复核；已接受trial严重警告或未解释接触/反力异常保留不可评分。被拒试算警告单独记录。任何反力回退保留精确幅值与接触/输出精度背景，不把极小负步自动解释成物理失稳；本轮不更改过去六点的null结论。',
 '缺点只报部分结果；失败、不完整或身份不明时停、保留证据、零自动重试。若弱信号不能相对数值不确定性分辨，结论UNRESOLVED，不以低Loss或回归能输出数字为通过理由。',
 '当前预算0。未来建议4个唯一Job、各一次DC+Full、零自动重试，复用I06不重算中心。按每项4–20min规划共16–80min、14核分配约3.73–18.67核小时，非实测利用率或保证。先另行授权CAE准备/预览并冻结4个完整INP/hash/Job/独立工作目录，再明确授权具体4项入队与计算；Solver只由用户GUI启动，AUTO_STOP_UNAVAILABLE风险必须按当时安装核验并明确执行方式。当前没有这些输入或执行授权，不能直接启动。','']
 write(P/'prospective_evaluation_protocol.md','\n'.join(protocol))
 science=['# run056 — run055复核与前瞻性识别设计','',f'完成时间：{at}。**WARNING / CONDITIONAL_PROSPECTIVE_DESIGN_ONLY**。','',
 '## 1. 旧结论复核与覆盖','',
 'run055的24个历史可评分点＋6个不评分点=30个不同参数组合，来自run039的22点与run042的8点。追加已完成且同初始.001/最大.0025合同的C200后主评估25点。H01/H02、重复精化和旧粗增量没有进入训练。重新核对25个外层折的训练/测试组互斥、模型/源代码/协议hash及250条预测文件，并直接复算以下指标。','',
 '|模型|σ MAE/MPa|σ RMSE/MPa|n MAE|n RMSE|','|---|---:|---:|---:|---:|']
 for m in rev['metrics_independently_recomputed']:science.append(f'|{m["model"]}|{m["sigma_MAE_MPa"]:.5f}|{m["sigma_RMSE_MPa"]:.5f}|{m["n_MAE"]:.7f}|{m["n_RMSE"]:.7f}|')
 science += ['',
 '筛选与超参数均位于训练折内，折内标准化逻辑及原独立SVD复核的源码/结果hash未变。没有用新增点或拉伸信息改变模型。结果仍是小样本FE自洽恢复PARTIAL，不是材料定量经验公式。',
 '成功样本σ范围150.411–817.024MPa、n .08–.461299，缺少σ>817附近和n<.08覆盖；原150–1000/.02–.50探索域不能由25点充分代表。4×4归一化网格统计（行x、列y）为：','',str(rev['coverage']['four_by_four_counts_x_then_y']),'',
 '其中3格没有样本，多格仅1点，左侧x<.25集中11点。即使有凸包，也不意味着内部所有参数有均匀数值质量或回归精度。全部六个null位于n<.043，是明显非随机过滤，但不能将其位置当成因果解释。','',
 '## 2. 六个低n点实际为何不评分','',
 '独立读取原STA/MSG并把警告按增量/attempt映射到接受或拒绝试算，再核对原始FD。六个目前用于代表各参数点的可读Job都DC/Full成功、完整覆盖1.2mm、PEEQ低于.9；不是六次Solver失败，不是缺窗口，也不是材料表覆盖不足。旧null全部保留。','',
 '|点|n|cutback|接受trial大应变警告|负载荷步数|最负ΔF/N|原不评分门控|','|---|---:|---:|---:|---:|---:|---|']
 for x in aud['records']:
  if x['sample_id']=='I06':continue
  nw=x['warning_counts']['ACCEPTED_TRIAL'].get('LARGE_STRAIN_INCREMENT',0);science.append(f'|{x["sample_id"]}|{x["n"]:.9f}|{x["cutbacks"]}|{nw}|{x["negative_force_count"]}|{x["min_force_step_N"]:.9f}|'+','.join(x['frozen_blockers'])+'|')
 science += ['',
 'D07、BO01没有接受trial严重警告，其null主要来自反力回退复核门控；最大回退分别约0.000305N、0.050659N，不能据此称为严重数值失稳或材料失效。D09、D10、BO02、DE02存在接受trial内的大应变标题，D10没有反力回退；其余三项兼有很小回退。警告发生于最终被接受的试算内部，不保证它就是该帧最终平衡状态的物理含义；原合同对其保守阻塞仍成立，不追溯改分数。',
 '各项负特征值/畸变标题主要位于被拒试算；不能移作已接受物理状态。小负步与单精度输出、非线性接触/平衡路径等关系仍未分离，本轮不宣称唯一成因。D09原run033曾中断，另行run038替代后来完成但null；该中断与当前材料参数的因果关系也未证实。',
 '合理分类是“软件完成但原数值/评分审核合同未满足”，外加D09旧中断历史，而不是“低n必然让Abaqus失败”。未来可另立离线证据复核协议区分数值分辨率与实际异常，不能悄悄把旧null填成训练标签。','',
 '## 3. 两固定特征预测差的候选原因','',
 'F(.15),F(.90)压缩掉曲线转变/中段形状；原17特征又有90/136对|r|>.98，σ/n都影响共同幅值，存在补偿与冗余。中高σ稀疏/边界样本D05等产生大误差，低n成功样本缺失。简单线性回归存在全域映射偏差，最近邻又受采样稀疏限制；不能将全部误差归因于“两个特征信息不足”或“算法不好”。',
 '全曲线Ridge在同折恢复较好，但使用更多自由度与可能的接触/数值纹理；D01/I08轻微细化就使其n预测变化约.006/.0073，提示数值灵敏性。少量特征宜做解释性诊断、廉价检索与局部筛查；全曲线保留作性能/残差基线和质量审计。不能将任一回归输出直接认作真实SA508参数。','',
 '## 4. I06资格','',
 f'源Job {base["job_name"]}；queue_id {base["queue_id"]}。σy={base["sigma_y_mpa"]}MPa、n={base["n"]}；INP SHA-256 {base["inp_sha256"]}，ODB SHA-256 {base["odb_sha256"]}。',
 '输入与完整材料数字、源文件/提取hash、RP方向和控制均绑定原manifest。原门控无阻塞项，439接受增量/18cutback、PEEQ .70275，无接受态严重警告或反力回退，因此适合本次条件性探索锚点。历史进程证据缺口保留；其自身未做进一步增量细化，不升级为可靠数值误差界或严格精度基准。',
 '若未来要求无条件的点级精度资格，需暂停使用I06并另议已精化的I08等替代锚点（最大.00125、不同中心），不能拿替代曲线混入本I06矩阵。本轮没有发现原门控硬失败，因此保留I06条件设计，不擅自更换或运行。','',
 '## 5. 四点设计与预期信息','',
 '最终数字、模型绑定和两个独立评价见prospective_design_contract.json(v2)、prospective_parameter_points.csv和prospective_evaluation_protocol.md。hx=hy=.025：','',
 '|设计|σy/MPa|n|','|---|---:|---:|']
 for point in contract['points']:science.append(f'|{point["design_id"]}|{point["sigma_y_mpa"]:.16g}|{point["n"]:.16g}|')
 science += ['',
 '最近旧异参数点为C200，归一化距离.088610；半步.025约为其28.2%，新点距既有I06都是.025，且与所有旧参数不重复。n负臂.0848仍高于成功样本n下限.08；若照搬±.05则n负臂.0728已越出成功覆盖，风险更大。σ扰动在对数坐标对称，MPa增减分别约10.955/11.487；n绝对扰动.012。',
 '从同控制旧FE的5/8/12邻居做锚定响应趋势，仅用于设计功效估计：σ半步响应RMS约25.81–28.87N、n半步约40.22–44.85N；两估计方向余弦约.9904–.9922，弱方向半步RMS仅约2.97–3.17N。它不是已计算的新FE、同点真实Jacobian或可信误差区间，不能据此保证四点能提供独立信息。强信号不等于弱方向可分辨，四点研究正是为了检验此事，而不是让SPT Loss变小。',
 'n负臂为一次小的联合参数凸包外推，必须显式报告，不能称四点全是插值。合法边界与最近邻距离不能保证其Solver稳定性。',
 '评价A构建同中心同控制的两列有限差分、奇异值/条件数/方向和对称性；单步长不证明步长独立性，无噪声模型不做正式Fisher置信区间。评价B完全冻结run055模型，使用未来FE输入作原始参数预测，完成四点B之前禁止新增点参与重训、特征筛选或调参。半步分辨目标与常数I06基线避免“几乎不预测变化也通过”的假阳性。两种评价分别报告，不相互替代。','',
 '## 6. 决策与授权','',
 '建议有条件继续Feature-Based路线，限于局部可区分性与前瞻模型误差研究，不扩展为广域公式或优化预算。四点足以形成最小对称两轴割线，不能预先保证独立或全局唯一。若反力/身份/材料覆盖或数值审核不满足，停止并保留partial/null；若弱方向与数值差同量级，结论UNRESOLVED，不自动缩步、补点或调整材料。',
 '建议未来最多4个新Job且不重算中心：先另行允许CAE准备四份INP与公开Preflight/Dry-run，冻结完整SHA/Job/独立工作目录后，再授权14CPU0GPU、各一次DC成功后Full、零重试、正式Project且GUI人工启动的具体四项。当前尚无INP/hash或执行授权，不能直接入队或求解。计划每项4–20min仅供预算估计，I06曾约294s，不保证新点耗时。',
 '低n门控证据值得先做离线机制澄清；四个I06邻点不补全低n全域空白，也不解决高应变材料形式、夹具或真实实验定义不确定性。未使用拉伸数据选点、改材料或调模型。run046冻结和run047/048正式NOT_EVALUABLE边界及历史信息暴露均保留。','',
 '本轮Git治理PASS，科学设计WARNING/CONDITIONAL；当前新FE预算0，无INP、Queue、Solver、Datacheck、BO/DE/RL、材料重拟合或Git提交。完成后停止。','']
 sciencepath=P/'scientific_report.md';write(sciencepath,'\n'.join(science))
 decision={'at':at,'run':'run_056','Git':'PASS_IN_AUTHORISED_SCOPE','CAE_untracked':2,'CAE_local_unchanged':True,'science':'WARNING_CONDITIONAL_PROSPECTIVE_DESIGN','six_null_software_failed':0,'six_null_classification':'completed but original numerical-admission/score gate unmet; D09 original interruption separately retained','low_n_failure_causality':'NOT_ESTABLISHED','I06':'eligible exploratory local anchor, NOT independently time-step-qualified precision reference','four_points_provide_independent_information':'NOT_YET_ESTABLISHED; only future same-control FE can test','future_proposed_FE':4,'current_authorized_FE':0,'inputs_generated':0,'queue_writes':0,'future_requires_input_preparation_then_specific_authorisation':True,'frozen_contract':rel(P/'prospective_design_contract.json'),'frozen_contract_sha256':sha(P/'prospective_design_contract.json'),'run055_models_unchanged':True,'new_model_training':False}
 save(P/'scientific_decision.json',decision)
 em=P/'evidence_manifest.json';save(em,{'run':'run_056','at':now(),'files':[{'path':rel(f),'sha256':sha(f),'bytes':f.stat().st_size,'visibility':'PRIVATE'} for f in sorted(P.rglob('*')) if f.is_file() and f.name!='hub_session.json'],'excluded':'self,liveidentity/lease,laterHubreceipt andcloseout'})
 registered=[];tid=ss['task_id']
 for path in [P/'git_hygiene_report.md',P/'git_hygiene_verified.json',sciencepath,P/'run055_recheck.json',P/'six_null_mechanisms.csv',P/'low_n_and_I06_audit.json',P/'prospective_design_contract.json',P/'prospective_parameter_points.csv',P/'prospective_evaluation_protocol.md',P/'scientific_decision.json',em]:registered.append(hub.artifact(tid,ss['identity']['agent_id'],path,{'run':'run_056','scope':'Git index cleanup and offline prospective preregistration only','no_FE_or_inputs':True},version='run056-v2'))
 result={'run':'run_056','Git':'PASS','untracked_CAE_count':2,'local_CAE_unchanged':True,'scientific_status':'WARNING_CONDITIONAL','report':rel(sciencepath),'report_sha256':sha(sciencepath),'git_report':rel(P/'git_hygiene_report.md'),'git_report_sha256':sha(P/'git_hygiene_report.md'),'contract':rel(P/'prospective_design_contract.json'),'contract_sha256':sha(P/'prospective_design_contract.json'),'I06_eligibility':decision['I06'],'new_FE':0,'planned_future_FE':4,'no_new_INP_or_queue':True}
 hub.message(tid,ss['identity']['agent_id'],'MAIN',result,'run056-git-prospective-result-v2');hub.finish(ss['lease'],result,evidence_state='RECORDED',science_state='WARNING');assert hub.verify_chain();save(P/'agenthub_completion_receipt.json',{'task_id':tid,'task':hub.task(tid),'artifacts':registered,'audit_chain_verified':True,'persistent_message_not_automatic_chat_wakeup':True})
 write(RUN/'summary.md','# run_056 — Git治理与前瞻性特征识别设计\n\n**Git：PASS；科学：WARNING / CONDITIONAL_PROSPECTIVE_DESIGN_ONLY。** 根.gitignore已保护CAE及备份/大型结果，2个明确CAE仅解除索引追踪，本地hash不变；原忽略策略与源码/输入/通用日志管理保留。\n\n已复核run055的25点、24/6集合及嵌套评估；六个null可读代表Job均软件完成，数值审核/评分门控未满足，不等同低n必然Solver失败。I06符合原探索性锚点门控，但不是独立精度基准。四点参数和A局部割线/B冻结模型前瞻预测协议已预注册，当前没有输入或执行授权。\n\n详见[Git报告](artifacts/private/git_hygiene_report.md)、[科研报告](artifacts/private/scientific_report.md)、[前瞻协议](artifacts/private/prospective_evaluation_protocol.md)、[冻结机器契约](artifacts/private/prospective_design_contract.json)、[证据hash](artifacts/private/evidence_manifest.json)。26项Git路径检查及7项设计测试通过，AgentHub已登记。\n\n当前新FE预算0，无新INP、Solver、Datacheck、入队、重拟合或优化，不commit/push。原模型与历史冻结保留，完成后停止。\n')
 index=R/'run/README.md';s=index.read_text(encoding='utf-8-sig');assert '## run_056' not in s;index.write_text(s+'\n\n## run_056 — Git治理及前瞻性特征识别\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_056 | CAE索引/忽略治理、低n门控复核及四点前瞻协议 | Git PASS / Science WARNING | [summary](run_056/summary.md) |\n\n本地CAE完整，仅2项解除索引；无新输入、求解或入队，执行预算0，完成后停止。\n',encoding='utf-8')
 sp=R/'status/PROJECT_STATUS.md';s=sp.read_text(encoding='utf-8-sig');pre='# SMALL-PUNCH 项目状态\n';assert s.startswith(pre) and 'run_056' not in s;sp.write_text(pre+'\n## 当前状态 — run_056（'+at[:10]+'，Asia/Shanghai）\n\n**Git PASS / Science WARNING_CONDITIONAL_PROSPECTIVE_DESIGN_ONLY。** CAE/备份忽略保护及2项索引解除完成，本地文件完整。复核六个null为完成但数值门控未满足，不认定低n必然求解失败；I06作为带警告探索锚点，四点A/B前瞻协议已预注册但没有新输入或计算授权。见[run_056](../run/run_056/summary.md)。新FE预算0，无求解/入队/重拟合/优化或Git提交，当前停止。\n\n'+s[len(pre):],encoding='utf-8')
 manifest=A/'manifest.json';save(manifest,{'run_id':'run_056','files':[{'path':rel(f),'role':'offline audit/design code','sha256':sha(f),'visibility':'PUBLIC_CODE'} for f in sorted(A.glob('*.py'))]+[{'path':'.gitignore','role':'authorised ignore policy revision','sha256':sha(R/'.gitignore'),'visibility':'PUBLIC'},{'path':rel(sciencepath),'role':'scientific report','sha256':sha(sciencepath),'visibility':'PRIVATE'},{'path':rel(em),'role':'private evidence identities','sha256':sha(em),'visibility':'PRIVATE'}]})
 j=read(RUN/'run.json');(RUN/'checkpoints/run_before_complete.json').write_bytes((RUN/'run.json').read_bytes());j.update(status='WARNING',end_time=now(),outcome='GIT_HYGIENE_PASS_CONDITIONAL_FOUR_POINT_DESIGN',inputs=[{'path':rel(P/'source_manifest.json'),'role':'bounded old-source identities','sha256':sha(P/'source_manifest.json')},{'path':rel(P/'git_before.json'),'role':'pre-change Git/model baseline','sha256':sha(P/'git_before.json')}],outputs=[{'path':'.gitignore','role':'CAE/results ignore rules','sha256':sha(R/'.gitignore')},{'path':rel(sciencepath),'role':'scientific review','sha256':sha(sciencepath)},{'path':rel(P/'prospective_design_contract.json'),'role':'preregistered design only','sha256':sha(P/'prospective_design_contract.json')},{'path':rel(em),'role':'private evidence manifest','sha256':sha(em)}],validation=[{'check':'Git/model preservation','status':'PASS','evidence':rel(P/'git_hygiene_verified.json'),'scope':'2exactcachedremovals,localmodelsSHAunchanged,26ruleprobes'},{'check':'oldscienceandnullreasonaudit','status':'PASS','evidence':rel(P/'low_n_and_I06_audit.json'),'scope':'rawSTA/MSGandFDreviewof7completedJobs,oldnullsunchanged'},{'check':'designsanity','status':'PASS','evidence':rel(P/'design_tests.json'),'scope':'7tests,noinputs/FE;constantcenterfailsresolutiongoal'},{'check':'I06strictprecisionqualification','status':'NOT_EVALUABLE','evidence':rel(P/'prospective_design_contract.json'),'scope':'conditionalexploratoryanchoronly,nopoint-leveltime-stepconvergenceproof'}],agenthub_task_id=tid,new_FE=0,new_INP=0,new_queue=0,CAE_index_removals=2,CAE_local_deleted=0,errors=[])
 tmp=RUN/'run.json.tmp';tmp.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');read(tmp);os.replace(tmp,RUN/'run.json')
 for model in gb['target_CAE_models']:assert sha(R/model['path'])==model['sha256']
 for src in sources:assert sha(R/src['path'])==src['sha256']
 assert set(git('diff','--cached','--name-status').splitlines())=={'D\t'+m['path'] for m in gb['target_CAE_models']}
 assert not list(RUN.rglob('*.inp')) and not list(RUN.rglob('*.odb'))
 private=[x for x in P.rglob('*') if x.is_file()]
 for f in private:assert subprocess.run(['git','check-ignore','--quiet','--',str(f)],cwd=R).returncode==0,str(f)
 save(RUN/'checkpoints/completed.json',{'at':now(),'git_branch':git('branch','--show-current'),'git_head':git('rev-parse','HEAD'),'git_working_tree':git('status','--short'),'git_staged':git('diff','--cached','--name-status'),'gitignore_sha256':sha(R/'.gitignore'),'local_CAE_SHA_unchanged':True,'private_files_ignored':len(private),'old_sources_unchanged':len(sources),'report_sha256':sha(sciencepath),'contract_sha256':sha(P/'prospective_design_contract.json'),'Hub_state':hub.task(tid)['execution_state'],'new_FE':0,'stop':True})
 print(json.dumps({'run':'run_056','Git':'PASS','CAE_untracked':2,'CAE_local_preserved':2,'science':'WARNING_CONDITIONAL','points':contract['points'],'report':str(sciencepath),'report_sha256':sha(sciencepath),'protocol_sha256':sha(P/'prospective_design_contract.json'),'Hub_task':tid,'new_FE':0}))
if __name__=='__main__':main()
