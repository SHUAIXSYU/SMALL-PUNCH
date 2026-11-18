"""Verify real ODB task, preserve source identities, register MAIN review."""
import sys,json,hashlib,sqlite3,math,subprocess
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];RUN=ROOT/'run/run_019';OUT=RUN/'artifacts';P=OUT/'private';AN=P/'main_analysis'
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
def now():return datetime.now(timezone(timedelta(hours=8))).isoformat()
def rel(p):return p.relative_to(ROOT).as_posix()
def save(p,v,replace=False):
    assert replace or not p.exists(),p
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf8');read(t);t.replace(p)

ids=read(OUT/'task_ids.json');db=ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3';hub=Hub(db,lease_seconds=3600)
task=hub.task(ids['odb_task_id']);assert task['execution_state']=='COMPLETED',task['execution_state']
assert task['lease_agent']=='ODB:codex-local-01a15d5e-f6e8-7373-8991-ae275dfd3b40'
with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as c:
    c.row_factory=sqlite3.Row
    artifacts=[dict(r) for r in c.execute('SELECT * FROM artifacts WHERE task_id=?',(ids['odb_task_id'],))]
    messages=[dict(r) for r in c.execute('SELECT * FROM messages WHERE task_id=? AND recipient_role=?',(ids['odb_task_id'],'MAIN'))]
assert artifacts and messages
for a in artifacts:assert sha(Path(a['path']))==a['sha256'],a['path']
save(P/'odb_handoff_verified.json',dict(observed_at=now(),task=task,artifacts=artifacts,messages=messages,all_hashes_match=True,actual_thread='01a15d5e-f6e8-7373-8991-ae275dfd3b40',sealed_tasks_accessed=False))
audit=read(P/'execution_audit.json');loss=read(AN/'loss_results.json');score=loss['P01'];diag=read(P/'odb/p01_diagnostics.json');logs=read(AN/'numerical_audit.json')[0]
odbscore=read(P/'odb/p01_provisional_loss.json')
assert math.isclose(odbscore['loss'],score['loss'],rel_tol=1e-14)
assert odbscore['configuration_id']==score['configuration_id'] and odbscore['point_count']==241
assert odbscore['sha256']['diagnostics']==sha(P/'odb/p01_diagnostics.json')
assert odbscore['sha256']['fe_curve']==score['fd_sha256']
assert diag['peeq']['saved_frame_max']<diag['peeq']['material_table_pmax']
assert diag['rp_identity']['field_U2_max_abs_error']==diag['rp_identity']['field_RF2_max_abs_error']==0
protected=audit['protected_before'];assert all(sha(Path(p))==h for p,h in protected.items())
sourcechecks=[]
for rec in audit['records']:
    point=rec['point'];assert sha(ROOT/point['inp_path'])==point['inp_sha256']
    for f in rec['files'].values():
        assert sha(ROOT/f['path'])==f['sha256']
        sourcechecks.append(dict(path=f['path'],exists=f['exists'],sha256=f['sha256']))
save(P/'final_integrity.json',dict(observed_at=now(),protected_unchanged=True,protected=protected,sources=sourcechecks,new_solver=0,new_datacheck=0,new_enqueue=0,hidden_tensile_access=False))
rows='\n'.join('| {point_id} | {sigma_y_mpa:.9f} | {n:.3f} | {loss_text} | {status} | {time_text} |'.format(**r,loss_text='—' if r['loss'] is None else format(r['loss'],'.12f'),time_text='—' if r['duration_sec'] is None else str(r['duration_sec'])) for r in loss['rows'])
report=f'''# run_019 — 已有首批结果分析（私有）

## 结论与证据边界

**WARNING：分析工作完成；五点批次仅发现 P01 一项成功计算，四个扰动点未执行证据缺失，不能构成五点敏感性结论。**

正式 Project ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae` 的 Queue、Project History 和冻结输出目录均已核对。P01 queue_id=`q_bdec6a60a31849d0a2afe200a70231bd`，History run_count=1；P02–P05 无对应 Queue/History，冻结预期 ODB/STA/MSG/DAT/LOG 均不存在。已执行成功率为 1/1；冻结设计完成率为 1/5，不能把未执行四点计作求解失败。

## 真实 ODB 交接

MAIN task `{ids['main_task_id']}`；真实 ODB task `{ids['odb_task_id']}`。实际 ODB Codex 会话自行注册/领取、以 Abaqus2024 自带 `SMAPython.exe`（Python3.10.5）只读提取，向 AgentHub 登记产物及完成消息。MAIN 在当前任务范围内读取结果和回传消息并核验全部 {len(artifacts)} 项产物哈希；没有扫描封存任务或全局历史消息。

初次只读提取的 JobData.name 身份判断误把路径当成纯名称，错误已保留；修正为严格路径 basename 后提取成功。这是离线提取脚本修正，不是 Solver 重试。两次源 ODB 哈希一致。原始审计因 Datacheck 一个瞬时子进程身份不全而给出安全门槛 false；真实 ODB 后续两次当前进程扫描、文件独占读探针、无目标锁和稳定哈希补充了当前只读安全证据。该历史身份缺口仍为 UNCONFIRMED，不追溯抹除。

ODB jobStatus=COMPLETED_SUCCESSFULLY、0 errors，STA最终完成、Runner两阶段退出0；不是只依据 ODB 存在。唯一 RP `Node ASM_SPT.1`，U2/RF2历史与场输出、时间轴逐点一致。79个历史点/保存帧，覆盖0–1.200000056997 mm；转换为 u=-U2、F=-RF2，单位m/N，无绝对值、2π、零点平移、二次柔度校正。MAIN 另对 ODB 的完整47行塑性表和弹性表进行哈希比较，与冻结 P01 INP 数值完全一致；旧材料名称 Q200N01 不用于判断参数。

## 冻结实验 Loss

契约 `run017-exploratory-fd-v1`，配置/代码/339点源CSV哈希一致。固定0–1.2 mm内241原始实验采样点、等权、F_ref=1428.9 N；线性插值FE到实验轴，不外推、不改窗口。直接调用冻结 `inverse/fd_loss.py`，MAIN另以显式归一化MSE公式核对。模型和实验测量/夹持/损伤等限制仍存在，所有数值为 **FROZEN_EXPLORATORY_COMPARISON / PROVISIONAL**，不是正式实验验证误差。

| 点 | sigma_y / MPa | n | Loss | Solver 状态 | 总耗时/s |
| --- | ---: | ---: | ---: | --- | ---: |
{rows}

P01 RMSE={score['rmse_n']:.8f} N，NRMSE={score['nrmse']:.10f}（RMSE/固定F_ref），Loss=NRMSE²。NRMSE不是逐点相对误差，Loss不等于50.4855%的平均载荷误差。

P01明显高估实验载荷。在本批唯一完成点中，P01（sigma_y=387.2983346207417 MPa、n=0.26）是唯一可评价参数组合，不存在五点排名依据。纳入历史run_014（200 MPa、0.1）后，历史Loss={score['run014_reference_loss_recomputed']:.18f}低于P01；MAIN已使用同一当前契约重新计算并核对原参考值。此比较不代表全局最优，也不能把run_014当作某个单参数扰动点。

## 敏感性与局部可识别性

缺少P02/P03，S_x=(F_P03−F_P02)/0.4不可计算；缺少P04/P05，S_y=(F_P05−F_P04)/0.4不可计算。J、列范数、余弦/夹角、奇异值、条件数和分位移区间信息贡献均为null，有明确缺项原因。两个参数的影响大小、补偿或混淆程度、最有辨识价值的位移区间目前均无法判断。残差较大区间不等于参数辨识信息多。

当前只有中心点和一个同时改变两个参数的历史点，不能分离偏导数。未绘制伪造五曲线或敏感性曲线；实际交付P01/实验/历史参考叠加图、现有点Loss图、P01残差图及缺项诊断JSON。未来若扰动点齐备，原始S单位为N/单位归一化参数；冻结实现的J还除以F_ref，SVD采用J/√N，需同时报告原始与无量纲尺度。

## 数值稳健性和成本

- Datacheck：31 s，return_code=0；Full：82 s，return_code=0；Runner总113 s。14 CPU/0 GPU，分配核时{logs['allocated_core_hours']:.8f} CPUh。阶段时间包括启动/预处理/收尾；MSG另报求解器墙钟54 s，不能混用为全部任务耗时。
- 78成功增量，18次被拒尝试/cutback，454次迭代；最小尝试增量0.000625。增量cutback不是新Job/自动重新入队。
- 两条“应变增量超过初始屈服应变50倍”警告位于增量1、尝试1，被拒后缩步；随后完成全步。三条zero moment警告包含被拒及接受尝试，应保留而不视为所有接受状态失败。
- MSG汇总负特征值警告0、数值问题警告0、错误0；未发现畸变相关日志。没有警告不证明网格/增量独立性。
- DAT记录解析刚体面不支持path-based tracking，实际采用state-based tracking。此自动求解器回退应作为模型实现事实保留。
- 最大保存帧PEEQ={diag['peeq']['saved_frame_max']:.12f}，位置为末帧/增量78、ASM_SPT-1单元172积分点1，小于表上限0.9（余量{diag['peeq']['coverage_margin']:.12f}）。仅覆盖已保存帧，不证明未保存极值或无损伤。
- ALLAE=ALLSD=0；末值ALLWK=1.932585358620 J，F–D梯形积分=1.932585515756 J，差约1.57e-7 J。最大|ETOTAL|≈0.00054665 J，但完整接触能量平衡未独立验证。没有动能输出用于额外比值诊断。
- Queue warning_count=8、MSG警告头5+DAT警告1、ODB诊断warnings=3是不同计数口径，不能简单相加或当作同一独立事件集合。

执行成功、材料表已保存帧覆盖通过；数值充分性仍WARNING，物理可信度未验证。当前未见致命收敛/畸变失败，但cutback、初始接触迭代和接触算法回退需要在后续研究中审查，尚无空间/时间离散误差估计。

## 下一阶段建议（不含执行授权）

**不建议现在启动DE/BO。** 单点不足以评价局部可区分性，模型差异不能直接归咎于材料参数，正式反演门槛仍未满足。先由MAIN审核现有数值警告和模型定义；如用户愿意继续冻结敏感性研究，可另行授权最多4个尚未执行的P02–P05，分别补齐sigma_y负/正扰动和n负/正扰动。逐Job执行后人工审查，无自动重试；不能沿用run_018仅P01授权。

若机械沿用P01成本，4个约452 s（7.53 min）、1.758分配CPUh，仅为粗略规划，参数变化可能显著改变收敛耗时。失败计入授权预算并暂停。已有run_017累计60 min审查上限可作为未来申请参考，不代表当前获批。完成扰动并审查可识别性、模型误差与数值稳定性后再制定冻结的BO/DE共享初始设计、相等新FE额度、随机种子/失败规则；本轮不据单点制定优化器排名或启动搜索。

## 私有产物

- `execution_audit.json`：五点Queue/History/API输出、文件身份、过程证据。
- `odb/`：真实ODB提取、原始RP/FD/PEEQ/能量CSV、诊断、provenance及Hub结果。
- `main_analysis/`：独立Loss、实际可用曲线叠加/残差图、五点缺项表、数值与敏感性诊断。
- `full_material_identity.json`、`contract_verification.json`、`odb_handoff_verified.json`、`final_integrity.json`。

所有原始实验/模型/ODB不改写。Queue/Settings/ProjectDB和源文件哈希保持不变；本轮新Solver/Datacheck/入队/重试为0，未训练或运行DE/BO/RL、未commit/push。禁读拉伸文件及派生材料未访问；研究仍为“独立数据保留验证，存在历史信息暴露”，不能声称严格无泄漏盲测。当前Run结束后停止。
'''
(P/'main_report.md').write_text(report,encoding='utf8')
public='''# run_019 — 已有计算结果分析

**WARNING：既有结果只读分析完成，冻结五点设计尚不完整。**

通过正式AbqJobPilot只读接口审计所有五点，真实ODB会话领取AgentHub任务并完成现有结果提取，MAIN独立复核冻结Loss、完整材料表与源哈希。分析数值、曲线、诊断及来源详情全部保存在Git忽略的私有区。

- [完整私有报告](artifacts/private/main_report.md)
- [实际执行审计](artifacts/private/execution_audit.json)
- [Loss与缺项表](artifacts/private/main_analysis/loss_results.json)
- [可用曲线叠加图](artifacts/private/main_analysis/available_fd_overlay.png)
- [局部可识别性缺项诊断](artifacts/private/main_analysis/sensitivity_diagnostic.json)
- [真实ODB交接核验](artifacts/private/odb_handoff_verified.json)

修改：新增run_019分析代码与私有证据、正式AgentHub任务/消息/证据记录，更新Run索引和项目状态。Queue、Settings、ProjectDB、输入和源输出哈希保持不变。验证范围为真实执行/文件身份、只读提取、公式及哈希复核；未新增或运行单元测试。

缺少必要扰动结果，当前不建议进入DE/BO。下一步最多可另行申请尚未执行的冻结扰动点，须先审核已有数值问题，建议不是授权。未启动Solver/datacheck、入队、重试、优化或训练；未访问封存拉伸内容，保留历史暴露事实；未commit/push。完成后停止。
'''
(RUN/'summary.md').write_text(public,encoding='utf8')
outcome=dict(status='WARNING',execution='EXISTING_RESULTS_ANALYSIS_COMPLETED',completed_batch_jobs=1,missing_points=['P02','P03','P04','P05'],loss_rows=loss['rows'],best_batch_evaluated_point='P01_ONLY_AVAILABLE',best_with_historical='run014',local_identifiability='NOT_COMPUTABLE',de_bo_recommended=False,new_solver=0,new_datacheck=0,new_enqueue=0,task_ids=ids,report=rel(P/'main_report.md'))
save(P/'main_result.json',outcome)
hub.heartbeat(read(P/'main_lease.json'))
registered=[]
paths=[p for p in P.iterdir() if p.is_file() and p.name!='main_lease.json']+[p for p in AN.iterdir() if p.is_file()]+[RUN/'summary.md',OUT/'audit_and_dispatch.py',OUT/'offline_analysis.py',OUT/'finalize_analysis.py']
for p in paths:
    registered.append(hub.artifact(ids['main_task_id'],ids['identity']['agent_id'],p,dict(run_id='run_019',method='MAIN review of actual ODB session and frozen offline analysis',project_id='b87d2cd6-8519-4ac3-bae6-7eb989fb2dae'),version='run019-v1'))
hub.finish(read(P/'main_lease.json'),outcome,evidence_state='RECORDED',science_state='WARNING')
msg=hub.message(ids['main_task_id'],ids['identity']['agent_id'],'MAIN',outcome,'run019-main-result-v1')
save(P/'agenthub_final_receipt.json',dict(observed_at=now(),task_ids=ids,artifacts=registered,message_id=msg['message_id'],odb_result_read_and_verified=True))
r=read(RUN/'run.json');save(RUN/'checkpoints/run_before_final.json',r)
r.update(status='WARNING',end_time=now(),time_notes='Asia/Shanghai UTC+08 observed timestamps; source runtime timestamps retain original form',task_ids=dict(MAIN=ids['main_task_id'],ODB=ids['odb_task_id']),outputs=[dict(path=rel(RUN/'summary.md'),role='Public summary'),dict(path=rel(P/'main_report.md'),role='Private scientific report'),dict(path=rel(P/'agenthub_final_receipt.json'),role='Private AgentHub receipt')],validation=[dict(check='Readonly actual execution/file audit and real ODB extraction',status='PASS',evidence=rel(P/'odb_handoff_verified.json'),scope='Observed existing points only'),dict(check='Frozen Loss and full material identity',status='PASS',evidence=rel(P/'full_material_identity.json'),scope='Exploratory analysis only'),dict(check='Source and runtime preservation',status='PASS',evidence=rel(P/'final_integrity.json'),scope='Exact allowlisted sources')],errors=[dict(code='MISSING_PERTURBATION_RESULTS',severity='WARNING',message='Complete local sensitivity cannot be evaluated',evidence=rel(AN/'sensitivity_diagnostic.json'),resolution='Requires separate explicit future calculation authorization'),dict(code='NUMERICAL_AND_PHYSICAL_LIMITATIONS',severity='WARNING',message='See private report; execution success does not validate constitutive inversion',evidence=rel(P/'main_report.md'),resolution='Retain uncertainty and review before further jobs')])
save(RUN/'run.json',r,replace=True)
index=ROOT/'run/README.md';assert 'run_019' not in index.read_text(encoding='utf-8-sig')
with index.open('a',encoding='utf8') as f:f.write('\n\n## run_019 — 已有计算结果分析\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_019 | 真实ODB交接、冻结Loss与可用敏感性证据审核 | WARNING（缺少扰动结果） | [summary](run_019/summary.md) |\n\n分析结果保存在忽略的私有区；新入队/求解为0，完成后停止。\n')
status=ROOT/'status/PROJECT_STATUS.md';old=status.read_text(encoding='utf-8-sig');head='# SMALL-PUNCH 项目状态\n';assert old.startswith(head) and 'run_019' not in old
status.write_text(head+'\n## 当前状态 — run_019（2026-10-24，Asia/Shanghai）\n\n**WARNING：已有结果分析完成，五点局部敏感性证据尚不完整，暂不建议DE/BO。** 真实ODB会话已通过AgentHub领取/提取/回传，MAIN完成冻结契约、输入/输出身份、数值诊断和数据完整性复核。科学数值、曲线、具体缺项及后续预算建议见[私有分析报告](../run/run_019/artifacts/private/main_report.md)。\n\n本轮未新增任何Solver/datacheck、入队或重试，原始数据与运行状态保持不变。保留历史信息暴露，未访问封存数据。当前Run完成后停止，后续计算须另行明确授权。此前Run结论保留如下。\n\n'+old[len(head):],encoding='utf8')
files=[p for p in RUN.rglob('*') if p.is_file() and 'mplconfig' not in p.parts and p.name not in {'manifest.json','run.json','manifest_private.json'}]
save(P/'manifest_private.json',dict(observed_at=now(),files=[dict(path=rel(p),sha256=sha(p)) for p in sorted(files)]))
save(OUT/'manifest.json',dict(observed_at=now(),public_files=[dict(path=rel(p),sha256=sha(p)) for p in files if 'private' not in p.parts],private_manifest=dict(path=rel(P/'manifest_private.json'),sha256=sha(P/'manifest_private.json'))))
print(json.dumps(dict(status='WARNING',main_task=ids['main_task_id'],odb_task=ids['odb_task_id'],verified_odb_artifacts=len(artifacts),registered_main_artifacts=len(registered),p01_loss=score['loss'],report=rel(P/'main_report.md'))))
