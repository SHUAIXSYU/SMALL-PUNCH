"""Finalize queue-only audit; no AbqJobPilot or Solver imports/calls."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import subprocess
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'run/run_018';OUT=RUN/'artifacts'
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,value):
    tmp=p.with_name(p.name+'.tmp')
    with tmp.open('x',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
    read(tmp);tmp.replace(p)
def rel(p):return p.relative_to(ROOT).as_posix()
def now():return datetime.now().astimezone().isoformat()

result=read(OUT/'enqueue_result.json');receipt=read(OUT/'agenthub_receipt.json')
assert result['status']=='PASS' and result['new_enqueues']==1 and result['pending_jobs']==1
assert result['task_id']==receipt['task_id'] and result['queue_id']==receipt['queue_id']
verified=[]
for artifact in receipt['artifacts']:
    # Hub returned schema is inspected directly; no other tasks/messages are loaded.
    path=Path(artifact['path'])
    assert sha(path)==artifact['sha256']
    verified.append(dict(path=rel(path),sha256=artifact['sha256']))
task=receipt['task']
assert task['execution_state']=='COMPLETED' and task['evidence_state']=='RECORDED' and task['science_state']=='NOT_EVALUATED'
atomic(OUT/'evidence_verification.json',dict(observed_at=now(),status='PASS',task_id=result['task_id'],verified=verified,
    hidden_tensile_access=False,scope='This task artifacts only; no global inbox or sealed audit content read'))
summary=f'''# run_018 — P01 Queue-only Submission

## 结果

**PASS，仅限唯一 P01 入队与证据登记。执行状态：QUEUED / AWAITING_GUI_START。**

- task_id：`{result['task_id']}`
- queue_id：`{result['queue_id']}`
- Job：`{result['job_name']}`
- INP：[冻结 P01](../run_017/artifacts/candidates/SPIO_R017_P01_CTR/SPIO_R017_P01_CTR.inp)
- SHA-256：`{result['inp_sha256']}`
- 参数：sigma_y=387.2983346207417 MPa、n=0.26、E=210 GPa、nu=0.3，候选真总应变 Hollomon 契约。
- 工作目录：`run/run_017/artifacts/solver/SPIO_R017_P01_CTR`（仓库相对路径）。
- CPU=14、GPU=0；Datacheck=True、Full Analysis=True；自动重试=0。

## 实际动作与核验

读取实际 Run/AgentHub 协议、冻结清单和环境登记；使用绝对 torch-gpu 解释器 Python 3.11.13。新建 run_018，保留已有 Git 改动及历史 Run。

正式 Project ID `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae` 完全匹配。修复版 AbqJobPilot 0.2.2 公开 API 返回 Settings=PERSISTED，无默认值回退。命令文件 `D:\\ABAQUS2024\\Commands\\abq2024.bat` 存在；14 CPU、GPU关闭、Datacheck/Full开启、自动关机关闭均与保存文件一致。

完整 INP/参数哈希通过，未重新生成或修改。未发现相对 INCLUDE/import 等外部输入依赖，工作目录为空。Preflight=PREVIEW_READY、Dry-run=DRY_RUN_READY；Runner ownership=ABSENT、live phase=IDLE，无冲突求解进程。预览不证明 Abaqus 语法、许可证或收敛有效。

通过公开 API 显式传入 Project、INP、Job、工作目录、资源和模式，仅一次 enqueue_only，allow_solver_submit=False。采用官方队列事务保护检查与写入，并在调用前独占保存 attempt 记录。没有直接编辑 Queue JSON/Project DB/AgentHub DB。

队列包含一个原有 run_014 完成记录及唯一待执行 P01。原历史记录逐字段保持不变，P02–P05 未入队。入队后资源、运行模式、输出身份及哈希核验通过；started_at/ended_at 为空、没有 ODB/LCK 或输出文件。Solver/datacheck 均未启动。Settings、Project DB、原 INP、冻结清单、live_status、最近项目和应用设置哈希保持不变，外部源码 Git 状态保持不变。

AgentHub 仅登记 enqueue 执行批准；用户手动 GUI 单次启动授权单独记录，未向 Codex 授予 start_solver/recover_retry。正式任务完成仅指入队工作完成，science_state=NOT_EVALUATED。授权、请求、队列状态和输出查询已登记，持久化 MAIN 消息不声称其他会话已接收。

## 文件与验证证据

- [准入](artifacts/admission.json)、[即时复核](artifacts/admission_before_enqueue.json)
- [授权](artifacts/authorization.json)、[公开 API 响应](artifacts/enqueue_response.json)
- [队列](artifacts/queue_after_enqueue.json)、[任务状态](artifacts/status_after_enqueue.json)、[输出定位](artifacts/outputs_after_enqueue.json)
- [结果](artifacts/enqueue_result.json)、[AgentHub 登记](artifacts/agenthub_receipt.json)、[证据哈希核验](artifacts/evidence_verification.json)
- 本轮新增 run_018 文件、更新 Run 索引和项目状态；授权的外部状态变化仅正式 Queue 和 AgentHub API 记录。未运行新的单元测试，执行的是上述实际准入及入队后验证。

## 停止点与研究限制

**P01 已入队，等待你在 AbqJobPilot GUI 点击 Start Queue。**

用户应打开 `E:\\Projects\\SMALL-PUNCH\\agenthub_sp_invopt\\abqjobpilot_project`，确认唯一待执行 Job 为 P01，然后手动点击一次。Codex 已停止执行链路，没有自动启动、重试或追加任务。求解结束后可按既有协议只读分析 ODB；失败不得自动重试，P02–P05 仍未授权。

模型适用性、夹持理想化与实验位移校正等既有科学不确定性保留；入队不构成求解成功或实验验证。隐藏拉伸数据未访问，保留“独立数据保留验证，存在历史信息暴露”历史记录。没有 commit/push。
'''
(RUN/'summary.md').write_text(summary,encoding='utf8')
r=read(RUN/'run.json');r.update(status='PASS',end_time=now(),time_notes='Observed local timezone',outcome=result)
r['task_ids']={'MAIN':result['task_id']};r['queue_id']=result['queue_id']
r['validation']=[dict(check=label,status='PASS',evidence='run/run_018/artifacts/'+file,scope=scope) for label,file,scope in [
    ('Project/Settings/input/admission','admission_before_enqueue.json','Exact frozen P01 only'),
    ('Single public enqueue','enqueue_response.json','Queue write only; no Solver start'),
    ('Post-enqueue identity/status','enqueue_result.json','One pending P01; phases NOT_STARTED'),
    ('AgentHub artifact verification','evidence_verification.json','Current task evidence hashes')]]
r['outputs']=[dict(path=rel(p),role=p.name) for p in sorted(OUT.rglob('*')) if p.is_file() and 'private' not in p.parts]+[dict(path='run/run_018/summary.md',role='Run report')]
atomic(RUN/'run.json',r)
index=ROOT/'run/README.md'
assert 'run_018' not in index.read_text(encoding='utf-8-sig')
with index.open('a',encoding='utf8') as f:f.write('\n\n## run_018 — P01 Queue-only Submission\n\n| Run | 阶段 | 目标 | 状态 | 总结 |\n| --- | --- | --- | --- | --- |\n| run_018 | P01 Queue-only | 唯一冻结 P01 正式入队；用户 GUI 手动启动 | PASS（入队范围） | [summary](run_018/summary.md) |\n\nP01 唯一待执行；Datacheck/Full 均未启动，P02–P05 未入队。停止等待用户 GUI。\n')
status=ROOT/'status/PROJECT_STATUS.md';old=status.read_text(encoding='utf-8-sig');head='# SMALL-PUNCH 项目状态\n'
assert old.startswith(head) and 'run_018' not in old
new=f'''\n## 当前状态 — run_018（{datetime.now().date()}，Asia/Shanghai）

**PASS（唯一 P01 入队范围）：QUEUED / AWAITING_GUI_START。** 用户授权已通过正式公开 API 完成一次入队，Job `{result['job_name']}`，queue_id `{result['queue_id']}`，CPU14/GPU0，Datacheck+Full=True。只有 P01 待执行；Solver/datacheck 尚未启动，P02–P05 未授权入队。本任务已停止，等待用户在正确 Project 的 GUI 点击一次 Start Queue。

正式 Project Settings=PERSISTED，冻结完整哈希、预览、Runner/输出冲突检查及入队后核验通过。AgentHub task `{result['task_id']}` 已登记授权和证据。见 [run_018 报告](../run/run_018/summary.md)。求解成功及物理有效性尚未评估，无自动重试；此前 run_017 结论保留在下方。

'''
status.write_text(head+new+old[len(head):],encoding='utf8')
hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3')
extra=[]
for p in [OUT/'finalize_run.py',OUT/'evidence_verification.json',RUN/'summary.md']:
    extra.append(dict(path=rel(p),sha256=sha(p)))
msg=hub.message(result['task_id'],receipt['identity']['agent_id'],'MAIN',dict(phase='Audit finalized after queue-task completion',files=extra,queue_id=result['queue_id']),'run018-final-report-v1')
atomic(OUT/'final_report_receipt.json',dict(observed_at=now(),task_id=result['task_id'],file_references=extra,message_id=msg['message_id']))
atomic(RUN/'checkpoints/git_final.json',dict(observed_at=now(),working_tree=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)))
files=[p for p in RUN.rglob('*') if p.is_file() and p.name not in {'manifest.json','run.json'}]
atomic(OUT/'manifest.json',dict(observed_at=now(),files=[dict(path=rel(p),sha256=sha(p),visibility='PRIVATE' if 'private' in p.parts else 'PUBLIC_AUDIT') for p in sorted(files)]))
print(json.dumps(dict(status='PASS',queue_id=result['queue_id'],hub_artifacts_verified=len(verified),report='run/run_018/summary.md',manifest_files=len(files)),ensure_ascii=False))
