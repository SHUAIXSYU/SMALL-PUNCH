"""Finalize the Run only after real CAE completion and MAIN receipt verification."""
import datetime,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'run/run_010'
OUT=RUN/'artifacts'
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):
    tmp=path.with_suffix('.tmp.json')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    json.loads(tmp.read_text(encoding='utf-8'))
    tmp.replace(path)
h=read(OUT/'real_handoff.json')
a=read(OUT/'abqjobpilot_verification.json')
assert h['execution_complete'] and h['artifact_hashes_valid'] and h['audit_hash_chain_valid']
assert h.get('main_received_completion_message'), 'Require an actual CAE completion message receipt'
v=read(OUT/'cae/verification.json')
assert all(v['checks'].values())
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
run=read(RUN/'run.json')
write(RUN/'checkpoints/run_before_finalize.json',run)
run.update({'end_time':now,'status':'BLOCKED' if a['status']=='BLOCKED' else 'WARNING','inputs':[{'path':'agenthub_sp_invopt/CLI.md','role':'existing Hub CLI contract'},{'path':v['candidate_relative_path'],'role':'existing candidate INP','sha256':v['candidate_sha256']},{'path':'run/run_008/run.json','role':'prior candidate and Project identity'},{'path':'run/run_009/run.json','role':'existing ledger and CLI implementation'}], 'outputs':[{'path':'run/run_010/artifacts/real_handoff.json','role':'task, receipts, audit events and artifact hashes'},{'path':'run/run_010/artifacts/abqjobpilot_verification.json','role':'stable public API and configuration audit'},{'path':'run/run_010/artifacts/cae/verification.json','role':'real CAE static INP verification'},{'path':'run/run_010/artifacts/manifest.json','role':'evidence manifest'},{'path':'run/run_010/summary.md','role':'Run summary'}], 'validation':[{'check':'MAIN to real CAE Codex session through existing AgentHub','status':'PASS','evidence':'run/run_010/artifacts/real_handoff.json','scope':'actual CAE claim, artifacts, completion, MAIN durable receipt; platform-notified, not a background auto-wakeup service'},{'check':'Candidate INP static verification','status':'PASS','evidence':'run/run_010/artifacts/cae/verification.json','scope':'11 static checks; no physics or fresh Solver validation'},{'check':'AbqJobPilot persisted Settings','status':a['settings']['status'],'evidence':'run/run_010/artifacts/abqjobpilot_verification.json','scope':'actual Project/global/legacy Settings lookup'},{'check':'Public preflight / dry-run','status':a['preflight']['status'],'evidence':'run/run_010/artifacts/abqjobpilot_verification.json','scope':'not executed because Settings missing'}], 'errors':[{'code':'CAE_LEASE_EXPIRED','severity':'WARNING','message':'First real CAE claim expired before registration. Worker completion verified, MAIN task-scoped recover_retry approved, same task reclaimed by real CAE.','evidence':'run/run_010/checkpoints/cae_stopped_before_recovery.json','resolution':'RESOLVED; generation 2 completed'},{'code':'SETTINGS_MISSING','severity':'BLOCKED','message':'Abaqus command, CPU/GPU and datacheck/full-run values could not be verified from persisted Settings.','evidence':'run/run_010/artifacts/private/abq_settings_sources.json','resolution':'UNRESOLVED; no guessed defaults or preview calls'}], 'cae_agent_id':h['task']['lease_agent'],'cae_session_id':h['task']['lease_session'],'cae_generation':h['task']['generation'],'science_state':'NOT_EVALUATED','solver_authorization_ready':False,'solver_started':False,'datacheck_started':False,'queue_written':False,'hub_lease_recovery_performed':True,'abqjobpilot_retry_performed':False,'commit_performed':False,'push_performed':False})
write(RUN/'run.json',run)
summary=f'''# run_010 — Real Agent Integration & Preflight

状态：BLOCKED。真实 MAIN → AgentHub → CAE → AgentHub → MAIN 交付已完成；候选 INP 静态核验通过。AbqJobPilot 实际 Settings 缺失，preflight/dry-run 未执行，不具备单次 Solver 授权条件。

## 真实任务与证据

- task_id：`{run['task_id']}`。
- CAE Codex chat：`01a15d5e-a3ad-75f1-b53c-ac6a12c21c48`；真实 Agent：`{run['cae_agent_id']}`；session：`{run['cae_session_id']}`。
- 沿用原 SQLite，没有重建数据库。MAIN 正式创建任务并批准 verify_inp，通过平台向已有 CAE chat 发送明确交付提示。CAE 在其实际执行回合中领取任务、核验和登记；MAIN 未启动模拟 CAE worker。
- 首次租约30秒到期，CAE停止并发送诊断。平台确认其回合 completed/idle 后，MAIN 单独批准本地 Hub recover_retry 并恢复原任务。真实 CAE 第2次领取并完成，未涉及 AbqJobPilot/求解重试。
- MAIN 已收到该任务的持久完成消息；登记产物 SHA-256 均回读验证通过，审计链有效。见 [真实交接证据](artifacts/real_handoff.json) 与 [平台完成凭证](checkpoints/cae_completed.json)。
- 此结果证明本次授权的平台通知加真实会话主动领取，不代表 Hub 已部署后台自动唤醒服务。

## INP 结果

候选 `SPIO_R008_Q200_N010_Candidate.inp` SHA-256 `{v['candidate_sha256']}` 与 run_008/task 一致。11项静态检查通过：E=210 GPa、ν=0.3、σy=200 MPa、n=0.1、pmax=0.9，35行表与现有 Hollomon 生成器完全一致，源 INP 除候选材料表和说明注释外可重建一致。保留首次检查脚本边界错误报告；修正后通过，未修改候选。当前 CAE 数据库与历史 INP 等价性仍 UNKNOWN；本构仍为候选真总应变解释，没有实验/物理验证。

## AbqJobPilot

稳定版0.2.2，HEAD `{a['source_head']}`，源码工作树干净。复用 Project `b87d2cd6-8519-4ac3-bae6-7eb989fb2dae`；公开 API show_project、capabilities、Queue/History和输出定位均已读取。Project/global/legacy Settings 文件不存在，六项真实资源和阶段配置 UNKNOWN。源码默认值只作为来源审计记录，没有作为用户配置使用。

公开 API preflight 与 enqueue(dry_run=True) 的签名和实现已检查，但因缺少真实 Settings 均 BLOCKED/未执行。另观察到0.2.2命令预览读取 config.ABAQUS_CMD，且总是展示两个阶段模板，不能把它当成 Project Settings 或实际运行阶段的证据。项目/队列/用户 recent registry 的哈希前后相同，Queue为空。

## 交付与后续条件

新增 Run 010 协调/审计脚本、真实 CAE报告、台账事件和收件凭证，更新Run索引与项目状态。旧CAE/INP/ODB、外部稳定版源码均未修改；未 Solver/datacheck/实际入队/RL/commit/push。

单次 Solver 授权条件尚不满足。下一步需提供并核验本 Project 的实际 Abaqus 命令、CPU/GPU、datacheck/full-run Settings，并在相同 INP hash 上通过已授权的公开 preflight/dry-run；实际入队和启动仍须独立明确授权。Run 010到此停止。
'''
(RUN/'summary.md').write_text(summary,encoding='utf-8')
index=ROOT/'run/README.md'
text=index.read_text(encoding='utf-8')
if '| run_010 |' not in text:
    index.write_text(text+'\n\n## 新授权 Run — run_010\n\n| Run | 阶段 | 目标 | 状态 | 总结 |\n| --- | --- | --- | --- | --- |\n| run_010 | 真实会话集成 | MAIN→CAE真实任务交付、候选INP静态核验、稳定版Project/Settings审计 | BLOCKED | [summary](run_010/summary.md) |\n\n真实CAE领取、证据登记和MAIN完成消息接收通过；Settings仍缺失，preflight/dry-run未执行，未入队/求解。\n',encoding='utf-8')
status=ROOT/'status/PROJECT_STATUS.md'
text=status.read_text(encoding='utf-8')
if '## 当前状态 — run_010' not in text:
    text=text.replace('## 当前状态 — run_009','## 历史状态 — run_009',1)
    heading='# SMALL-PUNCH 项目状态\n'
    update='\n## 当前状态 — run_010（2026-10-21，Asia/Shanghai）\n\n**BLOCKED：真实 MAIN→AgentHub→CAE→MAIN 已验证，AbqJobPilot Settings 缺失阻塞 preflight/dry-run。** 原SQLite正式任务 `a4b4805f-4989-4168-a54a-3bbf435b52a6` 已由真实CAE会话领取、登记产物并完成；MAIN回读产物哈希与持久完成消息。首次本地租约超时后按协议独立批准恢复，同一任务第2代完成。11项INP静态核验通过，科学状态NOT_EVALUATED。稳定版0.2.2 Project身份确认、Queue为空且未改；六项实际运行配置UNKNOWN。未Solver/datacheck/实际入队/修改旧模型/训练/commit/push；尚不具备单次Solver授权条件。见 [run_010总结](../run/run_010/summary.md)。\n'
    status.write_text(text.replace(heading,heading+update,1),encoding='utf-8')
files=[p for p in RUN.rglob('*') if p.is_file() and 'private' not in p.parts and p.name not in ['run.json','manifest.json'] and p.suffix!='.pyc']
manifest={'run_id':'run_010','generated_at':now,'artifacts':[{'path':p.relative_to(ROOT).as_posix(),'sha256':digest(p)} for p in sorted(files)],'private_audit':'run/run_010/artifacts/private/','database':'agenthub_sp_invopt/runtime/sp_invopt.sqlite3'}
write(OUT/'manifest.json',manifest)
print(json.dumps({'status':run['status'],'task_id':run['task_id'],'cae_generation':run['cae_generation'],'solver_authorization_ready':False},indent=2))
