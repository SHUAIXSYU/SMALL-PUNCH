"""Finalize reports only; no queue mutation or Solver actions."""
import sys,json,hashlib,importlib.util
from pathlib import Path
from datetime import datetime
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];RUN=ROOT/'run/run_021';OUT=RUN/'artifacts'
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now().astimezone().isoformat()
def save(p,v):
    assert not p.exists()
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');read(t);t.replace(p)
def update(p,v):
    t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8');read(t);t.replace(p)
assert not (OUT/'final_report_receipt.json').exists()
r=read(OUT/'enqueue_result.json');auth=read(OUT/'authorization.json');receipt=read(OUT/'agenthub_receipt.json')
for artifact in receipt['artifacts']:assert sha(Path(artifact['path']))==artifact['sha256']
spec=importlib.util.spec_from_file_location('qverify',OUT/'queue_four.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
batch=q.frozen();api,settings=q.preview.inspect_settings();listing,found,old=q.inspect(api,batch)
assert len(found)==4 and [j['queue_id'] for j in found]==[j['queue_id'] for j in r['jobs']]
assert q.protected()==read(RUN/'checkpoints/protected_before.json')
assert settings['source_head']==read(OUT/'admission.json')['settings']['source_head'] and settings['source_working_tree']==''
state=q.idle()
save(OUT/'final_verification.json',dict(observed_at=now(),pending_count=4,other_pending_count=0,queue_ids=[j['queue_id'] for j in found],all_registered_hashes_valid=True,protected_files_unchanged=True,installation_unchanged=True,runner_state=state['owner']['state'],gui_process_binding=state['process_observation']['gui_binding']))
rows='\n'.join('| '+str(i)+' | '+j['job_name']+' | `'+j['queue_id']+'` | QUEUED |' for i,j in enumerate(r['jobs'],1))
summary=f'''# run_021 — run_020 四点 Queue-only 入队

**WARNING / FOUR_JOBS_QUEUED_AWAITING_MANUAL_START**

用户授权的四个冻结输入已经通过公开API按L01→L04入队，每项14 CPU、0 GPU、Datacheck=True、Full=True、最多一次尝试/零自动重试。中心不重算；没有其他可执行任务。Solver和Datacheck均未启动，科学分析尚未发生。

|顺序|Job|queue_id|状态|
|---|---|---|---|
{rows}

AgentHub正式任务：`{r['task_id']}`。授权、请求、实际Queue、输入身份、资源、预览和结果已登记；MAIN读回任务及证据，未声称自动跨会话唤醒。

## 已执行的核验

- Project ID完全一致：b87d2cd6-8519-4ac3-bae6-7eb989fb2dae。Settings严格返回PERSISTED，Abaqus2024命令文件存在，14/0资源、两阶段开启、自动关机关闭。
- 四个完整INP/参数hash匹配冻结清单，独立工作目录为空，无外部引用依赖；四项Preflight/Dry-run全部通过。当前Runner所有权ABSENT、live状态IDLE，无目标Solver进程或恢复冲突。
- 入队前无既有四点记录，入队后四个唯一queue_id顺序正确且时间字段未启动；两条历史已完成记录未变。实际入队使用显式JobRequest和公开API，官方runtime事务防止GUI在批次入队间取得所有权，未直接写Queue/DB。
- 原输入、参数、Settings、ProjectDB、live_status及所审计外部源码保持hash不变。没有修改外部安装，没有生成第五个Job、重新计算中心或重试。

## 异常控制：AUTO_STOP_UNAVAILABLE

本机安装0.2.2，Git HEAD 7012133e7cc0176bb3e56fc24d7154ee3b90bb81、工作树干净。审计了该安装的GUI/Runner代码，并完成7项隔离Fake检查；没有真实Solver测试。核验时没有观察到正在运行的GUI进程，不能声称已绑定当前窗口；用户启动时应使用该安装并打开正确Project。

Datacheck失败会阻止**同一Job**继续Full，但Queue循环仍可执行下一Job。Full失败或COMPLETED_WITH_WARNINGS同样不会自动暂停整队列。Start Queue执行所有QUEUED/DATACHECK_OK项，界面选择/过滤不限制执行范围。Stop After Current Job只是循环边界标志，存在请求晚于检查的竞态；启动前设置还会被start清零，因此不是真正逐项审核门控。正常停止保留后续QUEUED任务；崩溃/关闭GUI不能保证终止活动Solver，可能留下需要恢复的执行状态。

**点击Start Queue可能连续执行全部四项，失败和严重警告不会自动阻断后续项。** 用户已允许在此限制下入队。本轮没有实现或宣称自动fail-stop。建议人工在场监控；如果需要保证每项审核后才能继续，应在实际启动前另行完善并验证受控逐项执行方式。不要依赖关闭GUI或临近边界点击停止作为可靠联锁。

## 交付和停止

通过GUI Open Project打开`E:\\Projects\\SMALL-PUNCH\\agenthub_sp_invopt\\abqjobpilot_project`。入队完成后已停止主动执行，由用户决定手动启动；不代点Start。原run_020逐项放行建议保留为历史，本轮依新授权一次性加入四项，但不把人工建议冒充Runner能力。

产物：[输入/资源与入队结果](artifacts/enqueue_result.json)、[本机Runner审核](artifacts/runner_audit.md)、[7项Fake结果](artifacts/runner_fake_tests.json)、[AgentHub登记](artifacts/agenthub_receipt.json)、[最终核验](artifacts/final_verification.json)。Run索引和项目状态更新；旧Run不改。

第6–9节的ODB提取、Loss和可识别性分析未执行，须待用户完成计算再据实际结果开展。未访问封存拉伸数据；独立数据保留验证，存在历史信息暴露。不commit/push。
'''
(RUN/'summary.md').write_text(summary,encoding='utf8')
run=read(RUN/'run.json');run.update(status='WARNING',end_time=now(),outputs=[dict(path='run/run_021/'+p,role=role) for p,role in [('summary.md','Final report'),('artifacts/enqueue_result.json','Actual four queue identities'),('artifacts/runner_audit.md','Local failure-stop audit'),('artifacts/agenthub_receipt.json','Formal Hub evidence'),('artifacts/final_verification.json','Readback validation')]],validation=[dict(check=k,status='PASS',scope=s,evidence=e) for k,s,e in [('frozen_identity_and_settings','Four inputs and strict Project settings','run/run_021/artifacts/admission.json'),('public_preflight_dry_run','Four preview requests; no solve','run/run_021/artifacts/admission.json'),('fake_runner_checks','7 in-memory control-flow cases','run/run_021/artifacts/runner_fake_tests.json'),('queue_readback','Four unique ordered queued jobs, no other pending','run/run_021/artifacts/final_verification.json')]],errors=[dict(code='AUTO_STOP_UNAVAILABLE',severity='WARNING',message='Failures/warnings do not automatically stop the queue; manual stop has boundary race.',evidence='run/run_021/artifacts/runner_audit.md',resolution='Explicit user permits enqueue; attended/manual controlled execution required')],task_id=r['task_id'],queue_ids=[j['queue_id'] for j in r['jobs']],solver_started=False,datacheck_started=False,automatic_retries=0)
update(RUN/'run.json',run)
index=ROOT/'run/README.md';text=index.read_text(encoding='utf8');assert '## run_021' not in text
index.write_text(text+'\n\n## run_021 — 四点授权 Queue-only 入队\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_021 | 四点正式入队、本机Runner异常控制审计 | WARNING / AWAITING_MANUAL_START | [summary](run_021/summary.md) |\n\n四项QUEUED，AUTO_STOP_UNAVAILABLE；用户GUI手动启动，Codex未启动求解，停止等待。\n',encoding='utf8')
status=ROOT/'status/PROJECT_STATUS.md';text=status.read_text(encoding='utf8');title,rest=text.split('\n',1)
status.write_text(title+'\n\n## 当前状态 — run_021（2026-10-24，Asia/Shanghai）\n\n**WARNING / FOUR_JOBS_QUEUED_AWAITING_MANUAL_START。** run_020冻结四项已按L01→L04正式入队，14CPU/0GPU，两阶段开启，零自动重试；无其他待执行项，Solver/Datacheck未启动。**AUTO_STOP_UNAVAILABLE：Start Queue可能连续执行四项，失败/严重警告不会自动阻断后续；Stop After Current Job不是可靠逐项审核联锁。** 用户启动前须知此风险，建议在场监控或先完善受控逐项执行。见[run_021报告](../run/run_021/summary.md)。已停止；ODB/Loss分析等待用户完成计算，未访问封存数据。\n\n'+rest,encoding='utf8')
files=[RUN/'summary.md',OUT/'runner_audit.md',OUT/'enqueue_result.json',OUT/'runner_fake_tests.json',OUT/'final_verification.json',OUT/'finalize_run.py']
manifest=[dict(path=str(p.relative_to(ROOT)).replace('\\','/'),sha256=sha(p),role='Final immutable evidence') for p in files]
save(OUT/'manifest.json',dict(files=manifest))
hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3');assert hub.task(r['task_id'])['execution_state']=='COMPLETED'
msg=hub.message(r['task_id'],auth['identity']['agent_id'],'MAIN',dict(status=r['status'],run_status='WARNING',report='run/run_021/summary.md',report_sha256=sha(RUN/'summary.md'),manifest=manifest,auto_stop='AUTO_STOP_UNAVAILABLE',solver_started=False),'run021-final-report-v1')
save(OUT/'final_report_receipt.json',dict(task_id=r['task_id'],message_id=msg['message_id'],report_sha256=sha(RUN/'summary.md'),observed_at=now()))
print(json.dumps(dict(status=r['status'],run='run_021',auto_stop='AUTO_STOP_UNAVAILABLE',queue_count=4,solver_started=False)))
