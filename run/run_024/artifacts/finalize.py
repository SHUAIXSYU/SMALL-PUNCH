import sys,json,hashlib,shutil,subprocess
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub
R=ROOT/'run/run_024';A=R/'artifacts'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now().astimezone().isoformat()
def save(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
v=read(A/'enqueue_result.json');assert v['status']=='V01_QUEUED_AWAITING_MANUAL_START'
text=f'''# run_024 — 两阶段数值验证授权：V01 Queue-only

**WARNING / V01_QUEUED_AWAITING_MANUAL_START。本Run完成第一阶段入队；两项数值验证研究尚未完成。**

| 项目 | 实际状态 |
| --- | --- |
| V01 Job | {v['job_name']} |
| queue_id | {v['queue_id']} |
| MAIN入队任务 | {v['task_id']} |
| 两阶段预算登记任务 | {v['budget_task_id']} |
| Project ID | {v['project_id']} |
| CPU / GPU | 14 / 0 |
| Datacheck / Full | True / True，均未启动 |
| V01数值资格 | NOT_EVALUATED |
| V02 | 未入队；须V01数值审核PASS后才能安排 |
| 每Job上限 / 自动重试 | 一次两阶段尝试 / 0 |

用户正式授权两项冻结Job，逐项入队、用户GUI启动，失败同样消耗对应授权。当前只有V01为QUEUED；V02授权有条件保留，无须在V01真正PASS后重复申请，但必须重新检查Runner、恢复状态、队列与输入身份。WARNING/BLOCKED时禁止V02入队。没有第三项、中心重算以外的额外参数计算或DE/BO/RL授权。

## 已执行核验

读取AGENTS、Run/AgentHub/盲反演协议及run014/022/023报告，独占创建下一合法run024。选用已登记迁移后的Torch-GPU绝对解释器，Python3.11.13/SQLite3.50.2，未安装依赖。Git基线及用户已有改动留档，无commit/push。

冻结批次整体hash对照run023 manifest，两个输入完整SHA及其对应基线均核对；每份新输入仅含批准的Static数据行差异，材料、物理模型与其他字节一致。初始.001、最大.005、总时间1、最小1e-12、inc999999；没有重新生成输入、没有外部文件依赖。V01 SHA-256 `{v['inp_sha256']}`。输入及输出绝对路径见[入队结果](artifacts/enqueue_result.json)，工作目录在run023冻结位置，不迁移文件。

修复版公开API核实Project ID/路径，Settings=PERSISTED，无默认值补齐；Abaqus2024命令真实存在、14CPU/0GPU、Datacheck/Full开启、Auto shutdown关闭。Runner owner=ABSENT、live=IDLE、只读recovery assessment=CLEAN，无目标/求解进程冲突、无锁、无其他可执行Queue记录；Queue和History均无既有V01/V02尝试，两目录为空。

V01 preflight=PREVIEW_READY、dry-run=DRY_RUN_READY。通过公开enqueue_only、allow_solver_submit=False，仅一次真实enqueue；调用前保存独占attempt记录，重复执行受阻并须只读核对，不可自动重试。使用官方运行时事务防止检查与入队间GUI获取Runner。真实回读确认唯一可执行V01、完整身份/资源/阶段/输出目录一致，旧终态条目保持不变，V02无记录。API status为QUEUED，无ODB/LCK，无开始/结束时间。Solver/datacheck/Runner均未由Codex启动。

Queue变化由公开API完成；project.db、Settings、原始输入、冻结比较契约和历史Run结论未变，没有直接改写内部持久化状态。AgentHub正式API登记总预算及V01 enqueue approval，未授予Codex start_solver/retry；记录了输入hash、queue_id、执行状态和剩余条件授权。ODB任务等待真实求解结束后创建，不将消息入库当作自动唤醒会话。

## 人工停止点与后续门控

请在正确Project确认只有V01待执行，再由用户点击一次Start Queue。AUTO_STOP_UNAVAILABLE继续保留；目前坚持单Job可执行队列。入队不是求解成功，也不是数值精度PASS。

V01完成后，新结果审计通过正式API和真实ODB会话提取，MAIN按run023-increment-qualification-v1及run017-exploratory-fd-v1复核。不得修改已冻结阈值、窗口或相对差分母。全部指标及数值风险门控通过才使用PASS_V01_NUMERICAL_QUALIFICATION；否则WARNING_V01_REVIEW_REQUIRED或BLOCKED_V01_NUMERICAL_QUALIFICATION，并保持V02不入队。当前没有任何新F-D/Loss/PEEQ或精度结论。用户需回到MAIN确认完成以继续；未设置自动轮询唤醒。

修改范围：新run024证据、正式Hub任务、公开API单项Queue、Run索引和状态。封存拉伸数据未读取，历史信息暴露声明不变。完成当前入队指令后停止。
'''
shutil.copyfile(R/'summary.md',R/'checkpoints/summary.running.md');(R/'summary.md').write_text(text,encoding='utf8')
meta=read(R/'run.json');shutil.copyfile(R/'run.json',R/'checkpoints/run.running.json')
meta.update(status='WARNING',end_time=now(),stage='V01 queued; awaiting manual start',study_complete=False,
    outputs=[dict(path='run/run_024/'+p,role=role) for p,role in [('summary.md','Stage report'),('artifacts/authorization.json','Conditional two-job user authorization'),('artifacts/enqueue_result.json','Actual unique V01 queue identity'),('artifacts/agenthub_receipt.json','Formal ledger receipt')]],
    validation=[dict(check=k,status='PASS',scope=s) for k,s in [('frozen_identity','Exact hashes and byte-only authorized increment change'),('project_settings','PERSISTED, explicit ID/path, CPU/GPU/modes'),('runtime','ABSENT/IDLE/CLEAN; no ownership or recovery conflict'),('preview','V01 preflight/dry-run passed'),('single_queue_item','Only V01 QUEUED; V02 absent'),('no_solver_start','API flags plus empty output directory and queued timestamps')]]+[dict(check='numerical_qualification',status='WARNING',scope='Not evaluated; requires actual output and real ODB review')])
t=R/'run.json.tmp';t.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8');read(t);t.replace(R/'run.json')
idx=ROOT/'run/README.md';old=idx.read_text(encoding='utf-8-sig');assert '## run_024' not in old
idx.write_text(old+'\n\n## run_024 — 两阶段验证授权：V01入队\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_024 | 冻结V01单项Queue-only与条件预算登记 | WARNING / V01_QUEUED_AWAITING_MANUAL_START | [summary](run_024/summary.md) |\n\nV02未入队，须V01数值资格PASS；停止等待用户GUI启动。\n',encoding='utf8')
sp=ROOT/'status/PROJECT_STATUS.md';old=sp.read_text(encoding='utf-8-sig');heading='# SMALL-PUNCH 项目状态\n';assert old.startswith(heading)
sp.write_text(heading+f'\n## 当前状态 — run_024（2026-10-24，Asia/Shanghai）\n\n**WARNING / V01_QUEUED_AWAITING_MANUAL_START。** 唯一V01已通过公开API入队，queue_id `{v["queue_id"]}`，14CPU/0GPU、两阶段开启、零重试。用户GUI手动启动；Codex未启动Solver/datacheck。V02未入队，仅在V01按冻结门槛取得PASS后可在原授权内安排。两项验证研究尚未完成，无新精度结论。见[run_024报告](../run/run_024/summary.md)。保留AUTO_STOP_UNAVAILABLE，单Job门控；当前停止。\n\n'+old[len(heading):],encoding='utf8')
paths=[R/'summary.md']+[A/name for name in ['queue_v01.py','admission.json','authorization.json','request.json','enqueue_response.json','queue_after.json','postcheck.json','enqueue_result.json','agenthub_receipt.json']]
save(A/'manifest.json',dict(at=now(),files=[dict(path=str(p.relative_to(ROOT)).replace('\\','/'),sha256=sha(p)) for p in paths]))
session=read(A/'private/session.json');h=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3')
m=h.message(v['task_id'],session['identity']['agent_id'],'MAIN',dict(stage='V01_QUEUED_AWAITING_MANUAL_START',report='run/run_024/summary.md',report_sha256=sha(R/'summary.md'),manifest='run/run_024/artifacts/manifest.json',manifest_sha256=sha(A/'manifest.json'),study_complete=False,V02_not_queued=True),'run024-final-report-v1')
save(R/'checkpoints/stage_complete.json',dict(at=now(),queue_id=v['queue_id'],run_json_sha256=sha(R/'run.json'),manifest_sha256=sha(A/'manifest.json'),report_message_id=m['message_id'],study_complete=False,next_action='USER_GUI_START_ONLY; stop automation'))
print(json.dumps(dict(status=v['status'],queue_id=v['queue_id'],report='run/run_024/summary.md',study_complete=False)))
