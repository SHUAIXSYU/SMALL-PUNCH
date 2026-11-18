"""Finalize the queue-only execution record without touching Runner or Solver."""
import hashlib,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];R=ROOT/'run/run_028';A=R/'artifacts'
sys.dont_write_bytecode=True
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def rel(p):return p.relative_to(ROOT).as_posix()
e=read(A/'enqueue_result.json');ad=read(A/'admission.json');q=read(A/'queue_after.json');post=read(A/'postcheck.json');receipt=read(A/'agenthub_receipt.json')
assert e['status']=='SPIO_R027_CTR_M0025_QUEUED_AWAITING_MANUAL_START' and receipt['audit_chain_valid']
assert e['queue_id']==receipt['queue_id'] and e['inp_sha256']=='dae9345bc60973c27edec498dfbd27f269e1f5bbe151316918862954faac40c9'
assert sha(Path(e['inp_path']))==e['inp_sha256'] and q['existing'][0]['queue_id']==e['queue_id']
assert len([j for j in q['queue']['jobs'] if j['status']=='QUEUED'])==1
assert q['existing'][0]['status']=='QUEUED' and post['status']['status']=='QUEUED'
assert not e['datacheck_started'] and not e['solver_started'] and not e['V02_queued']
assert ad['preflight']['status']=='PREVIEW_READY' and ad['dry_run']['status']=='DRY_RUN_READY'
assert ad['settings']['settings_response']['status']=='PERSISTED'
assert post['runtime']['owner']['state']=='ABSENT' and post['runtime']['recovery']['status']=='CLEAN'
assert not any(Path(e['working_dir']).iterdir())
summary=f'''# run_028 — 单项授权 Queue-only 入队

**SPIO_R027_CTR_M0025_QUEUED_AWAITING_MANUAL_START。** 本 Run 仅处理用户新授权的一个候选。入队时间记录：{e['at']}。Datacheck、Full Analysis 和数值资格均未开始或评价。

| 身份 | 值 |
| --- | --- |
| Job | `{e['job_name']}` |
| queue_id | `{e['queue_id']}` |
| AgentHub MAIN task_id | `{e['task_id']}` |
| Project ID | `{e['project_id']}` |
| INP | `{rel(Path(e['inp_path']))}` |
| INP SHA-256 | `{e['inp_sha256']}` |
| 工作目录 | `{rel(Path(e['working_dir']))}` |
| CPU / GPU | 14 / 0 |
| 模式与次数 | 单次 Datacheck 成功后单次 Full Analysis；零自动重试 |

## 入队前核验

依实际 `AGENTS.md`、Run 协议、盲反演协议和 AgentHub 契约创建独立 run_028。已记录 Git branch、HEAD、remote、初始工作树及绝对 Torch-GPU Python 解释器；保留原有用户改动，未 commit/push。源是 run_027 冻结候选，不重生成 INP；完整 SHA 与用户授权一致、逐字节与 V01 的唯一允许变化一致。冻结工作目录原先为空，入队后仍无输出。

本机 AbqJobPilot 0.2.2 公开接口确认 Project ID 与目录，Settings=`PERSISTED`，Abaqus 2024 命令真实存在，14 CPU/0 GPU、Datacheck/Full开启。Runner owner=`ABSENT`、live=`IDLE`、recovery=`CLEAN`，无锁或相关活跃进程。入队前其余七项均是历史终态，没有其他可执行 Queue 记录，也无本候选历史尝试或同名 Queue 记录。Preflight=`PREVIEW_READY`、Dry-run=`DRY_RUN_READY`；预览未改变 Queue。

MAIN 使用 AgentHub 正式接口建立任务并绑定用户授权，任务级批准 `enqueue`；随后在 AbqJobPilot 正式运行时事务内通过公开 API 一次 `enqueue_only`，`allow_solver_submit=False`。真实回读确认只有本候选可执行且状态为 `QUEUED`，输入、SHA、资源、阶段及工作目录一致；原有七项历史终态保留。已保存不可自动重试的调用尝试记录和 queue_id，并在 AgentHub 登记证据、核验审计链。

## 人工停止点

请在修复版 AbqJobPilot GUI 打开 Project `{e['project_id']}` 对应目录，确认只有 `{e['job_name']}` 待执行，然后由用户本人点击一次 **Start Queue**。Codex 未启动 Runner、Datacheck 或 Solver。GUI 启动后的真实状态必须待用户通知并通过公开历史和真实输出重新核验；入队不代表计算完成或数值资格通过。V02 未入队，其原条件授权未使用或转移。

后续仅在真实计算结束后按 `run027-adjacent-refinement-v1` 冻结契约做只读 ODB 提取与比较；run_025 原 `BLOCKED_V01_NUMERICAL_QUALIFICATION` 结论保留。无新计算、参数搜索或封存拉伸数据访问授权。

审计文件：`artifacts/admission.json`、`artifacts/authorization.json`、`artifacts/request.json`、`artifacts/enqueue_response.json`、`artifacts/queue_after.json`、`artifacts/postcheck.json`、`artifacts/enqueue_result.json`、`artifacts/agenthub_receipt.json`、`checkpoints/enqueue_attempt.json`。
'''
(R/'summary.md').write_text(summary,encoding='utf8')
run=read(R/'run.json');run['status']='WARNING';run['stage']='single job queued; awaiting manual GUI start';run['end_time']=now()
run['outputs']=[{'path':rel(p),'sha256':sha(p)} for p in [R/'summary.md',A/'admission.json',A/'authorization.json',A/'request.json',A/'queue_after.json',A/'postcheck.json',A/'enqueue_result.json',A/'agenthub_receipt.json']]
run['validation']=[{'check':'frozen_identity','status':'PASS'},{'check':'project_settings','status':'PASS'},{'check':'runner_recovery_queue','status':'PASS'},{'check':'preflight_dry_run','status':'PASS'},{'check':'single_queue_item','status':'PASS'},{'check':'no_solver_start','status':'PASS'},{'check':'numerical_qualification','status':'NOT_EVALUATED'}]
run['queue_id']=e['queue_id'];run['task_id']=e['task_id'];run['study_complete']=False
dump(R/'run.json',run)
idx=ROOT/'run/README.md';s=idx.read_text(encoding='utf8');assert '## run_028' not in s
idx.write_text(s.rstrip()+'''\n\n## run_028 — 单一中心点授权 Queue-only\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_028 | run_027 唯一候选正式入队；等待用户GUI启动 | WARNING / AWAITING_MANUAL_START | [summary](run_028/summary.md) |\n\n唯一Job已QUEUED；Codex未启动Solver，停止等待用户手动Start Queue。\n''',encoding='utf8')
st=ROOT/'status/PROJECT_STATUS.md';s=st.read_text(encoding='utf8');assert '## 当前状态 — run_028' not in s
st.write_text(s.replace('# SMALL-PUNCH 项目状态\n','# SMALL-PUNCH 项目状态\n\n## 当前状态 — run_028（2026-10-24，Asia/Shanghai）\n\n**WARNING / SPIO_R027_CTR_M0025_QUEUED_AWAITING_MANUAL_START。** 用户授权的唯一run_027中心候选已通过公开API入队，queue_id=`'+e['queue_id']+'`；只有该Job可执行，14 CPU/0 GPU、Datacheck+Full，Codex未启动Runner或求解。用户须在正确Project手动Start Queue。run_025数值资格BLOCKED保留，V02未入队。见[run_028报告](../run/run_028/summary.md)。\n\n',1),encoding='utf8')
dump(R/'checkpoints/completion.json',{'at':now(),'status':e['status'],'queue_id':e['queue_id'],'task_id':e['task_id'],'solver_started':False,'datacheck_started':False})
print(json.dumps({'status':e['status'],'queue_id':e['queue_id'],'task_id':e['task_id']}))
