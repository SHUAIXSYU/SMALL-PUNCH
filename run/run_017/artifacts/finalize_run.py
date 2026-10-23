"""Publish offline preparation evidence via Hub, then finalize Run records."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];RUN=ROOT/'run/run_017';OUT=RUN/'artifacts'
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def save(p,v):
    with p.open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def replace_checked(path,text,checkpoint):
    with (RUN/'checkpoints'/checkpoint).open('xb') as f:f.write(path.read_bytes())
    tmp=path.with_name(path.name+'.run017.tmp')
    with tmp.open('x',encoding='utf8') as f:f.write(text)
    if path.suffix=='.json':json.loads(tmp.read_text(encoding='utf8'))
    tmp.replace(path)

def main():
    stamp=datetime.now().astimezone().isoformat()
    private=[p.relative_to(ROOT).as_posix() for p in (OUT/'private').rglob('*') if p.is_file()]
    ignored=subprocess.run(['git','check-ignore','--stdin','-z'],cwd=ROOT,
                           input=('\0'.join(private)+'\0').encode('utf8'),capture_output=True,check=True)
    assert set(ignored.stdout.decode('utf8').rstrip('\0').split('\0'))==set(private)
    assert not subprocess.check_output(['git','ls-files','run/run_017/artifacts/private'],cwd=ROOT,text=True).strip()
    save(OUT/'privacy_check.json',dict(observed_at=stamp,all_private_ignored=True,
                                      private_count=len(private),tracked_private_files=0,heldout_new_access=False))
    baseline=read(OUT/'private/source_inventory.json')
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in baseline['files'])
    bundle=read(OUT/'prepared_batch.json')
    assert all(sha(ROOT/r['path'])==r['sha256'] for r in bundle['contracts'])
    assert all(sha(ROOT/p['inp_path'])==p['inp_sha256'] and not any((ROOT/p['working_dir']).iterdir()) for p in bundle['points'])
    assert read(OUT/'test_results.json')['successful']
    tasks=read(OUT/'hub_tasks.json');identity=tasks['identity'];lease=read(OUT/'private/main_lease.json')
    hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=1800);hub.heartbeat(lease)
    main_files=['private/experimental_metadata.json','private/main_preparation_report.md',
       'private/canonical_fd_source_confirmed.csv','private/canonical_provenance.json',
       'private/loss_contract.json','private/reference_loss.json','private/cae_handoff_verified.json',
       'private/integrity_check.json','private/abq_integrity.json','loss_contract_identity.json',
       'parameter_design.json','prepared_batch.json','run016_resolution_by_new_evidence.json',
       'abq_settings_verification.json','batch_preview_result.json','execution_permission_check.json',
       'odb_analysis_protocol.md','sensitivity_analysis.py','test_sensitivity_analysis.py',
       'test_results.json','test_log.txt','freeze_experimental_contract.py','preview_batch.py',
       'run_tests.py','freeze_batch.py','finalize_run.py','privacy_check.json','solver/.gitignore']
    main_files += ['previews/'+p['point_id']+'.json' for p in bundle['points']]
    artifacts=[]
    for rel in main_files:
        a=hub.artifact(lease['task_id'],identity['agent_id'],OUT/rel,
          dict(run='run_017',scope='Source-confirmed exploratory sensitivity preparation; no new FE',
               original_sources_preserved=True,heldout_access=False),version='run017-v1')
        artifacts.append(dict(artifact_id=a['artifact_id'],path=(OUT/rel).relative_to(ROOT).as_posix(),sha256=a['sha256']))
    outcome=dict(run='run_017',status='WARNING',execution='PREPARATION_COMPLETED',
          source_units='CONFIRMED_BY_COLLABORATOR',geometry='PASS_FOR_IDEALISED_CLAMPING_BASELINE',
          complete_fixture_equivalence=False,loss_version='run017-exploratory-fd-v1',
          loss_status='FROZEN_EXPLORATORY_COMPARISON',candidate_count=5,
          preflight_pass=5,dry_run_pass=5,settings='PERSISTED',synthetic_tests_pass=28,
          ready_to_request_first_five_job_sensitivity_batch=True,authorized_jobs=0,
          queued_jobs=0,solver_executions=0,automatic_retries=0,
          formal_inversion_qualified=False,batch='run/run_017/artifacts/prepared_batch.json',
          main_report='run/run_017/artifacts/private/main_preparation_report.md',
          independent_validation='Retained dataset with historical information exposure; no new access')
    hub.finish(lease,outcome,evidence_state='RECORDED',science_state='WARNING')
    message=hub.message(lease['task_id'],identity['agent_id'],'MAIN',outcome,'run017-main-preparation-complete-v1')
    save(OUT/'agenthub_receipt.json',dict(observed_at=stamp,task_id=lease['task_id'],
         identity=identity,execution_state=hub.task(lease['task_id'])['execution_state'],
         artifacts=artifacts,message_id=message['message_id'],outcome=outcome))
    summary='''# run_017 — First Constitutive Sensitivity Study Preparation

**WARNING（离线准备完成）；具备申请首批最多五个探索性敏感性 Job 的条件。当前授权数=0、入队数=0、Solver/Datacheck 执行数=0。**

## 实际完成与准入

- 新的合作方实验元数据已登记；载荷单位冲突由来源方澄清，保留原冲突与 run_016 历史结论。
- 真实 CAE 会话领取并完成正式任务，MAIN 核验 19 项 Hub 证据；名义几何一致。固定环带按用户许可作为 idealised clamping baseline，不宣称完整夹具等效。
- 生成五个独立材料变体、参数 JSON、唯一 Job 名与独立工作目录。除 Plastic 表和候选注释外，与原输入字节一致；旧模型未改。
- 新版 `run017-exploratory-fd-v1` 冻结实验比较契约，重新计算既有参考。实验数值保持；不二次校正、不按候选调整窗口、零点或尺度。仍不构成正式材料反演结论。
- 指定 Project 的实际 Settings 返回 PERSISTED，14 CPU/0 GPU、Datacheck 与 Full 开启、Auto shutdown 关闭；五个 Preflight/Dry-run 全部通过。Queue、Settings 与 Project DB 未变。
- 28 项合成测试通过（19 Loss、9 局部敏感性）；五个 INP 静态复核通过。未执行 Abaqus 语法/datacheck 或未来结果提取。

## 五点设计

x=ln(σ_y/150)/ln(1000/150)，y=(n−0.02)/0.48；中心 (0.5,0.5)，各方向扰动 ±0.2。中心不是真实材料参数。

| 点 | σ_y / MPa | n | Job |
| --- | ---: | ---: | --- |
| P01 | 387.298335 | 0.260 | SPIO_R017_P01_CTR |
| P02 | 265.010988 | 0.260 | SPIO_R017_P02_SYM |
| P03 | 566.014266 | 0.260 | SPIO_R017_P03_SYP |
| P04 | 387.298335 | 0.164 | SPIO_R017_P04_NM |
| P05 | 387.298335 | 0.356 | SPIO_R017_P05_NP |

使用冻结 JSON 的完整精度；E=210 GPa、ν=0.3，真总应变候选 Hollomon、塑性表覆盖至0.9。未来 PEEQ 是否充分覆盖未知。

## 证据与修改

- [完整私有报告](artifacts/private/main_preparation_report.md)
- [冻结批次/完整输入哈希](artifacts/prepared_batch.json)
- [CAE 候选清单](artifacts/cae_candidate_manifest.json)
- [逐点公开 API 预览](artifacts/batch_preview_result.json)
- [Loss 契约身份](artifacts/loss_contract_identity.json)
- [ODB、敏感性、成本与停止协议](artifacts/odb_analysis_protocol.md)
- [合成测试](artifacts/test_results.json)
- [旧阻塞的新证据说明](artifacts/run016_resolution_by_new_evidence.json)
- [AgentHub 登记](artifacts/agenthub_receipt.json)
- [证据清单](artifacts/manifest.json)

全部新分析/候选文件在本 Run；更新 Run 索引及项目状态。私有实验曲线/来源审计在 Git 忽略区，未来 Solver 输出目录也已忽略。14 个明确基线文件哈希保持，未改外部项目/环境、原始实验/模型，不 commit/push。

## 剩余限制与下一步

位移校正方法、夹具完整接触/预紧/柔度、摩擦、试验速度/温度、无损伤窗口、数值充分性与材料模型科学有效性仍有不确定性。首次是局部敏感性研究，不能证明全局唯一性或直接启动正式 DE/BO。

按历史165秒机械外推，五个约13.75分钟、3.21分配核时，实际成本待测。建议未来串行、一次只入队一个、逐个审核，失败或重要警告停批；每个最多一次，零自动重试。获得授权后仍需在执行时复核身份、Settings、空输出与 Runner 状态。

研究继续表述为“独立数据保留验证，存在历史信息暴露”；未重新读取保留拉伸源及派生内容。完成本轮后停止，等待用户正式授权；不自动创建下一 Run 或启动计算。
'''
    replace_checked(RUN/'summary.md',summary,'summary_initial.md')
    index=ROOT/'run/README.md';old=index.read_text(encoding='utf8');assert '## 新授权 Run — run_017' not in old
    extra='''

## 新授权 Run — run_017

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_017 | First Constitutive Sensitivity Study Preparation | 来源确认、探索性 Loss 冻结、真实 CAE 五输入及公开 API 预览 | WARNING（准备完成） | [summary](run_017/summary.md) |

来源方澄清力单位，名义几何一致；用户接受理想化夹持作为本批基线。五个 INP/Preflight/Dry-run 就绪，28 项合成测试通过；可以申请最多五个探索性 Job，授权/入队/执行均0。完整夹具等效、位移校正与材料科学有效性仍未验证；完成后停止。
'''
    replace_checked(index,old+extra,'run_index_before.md')
    status=ROOT/'status/PROJECT_STATUS.md';old=status.read_text(encoding='utf8');heading='# SMALL-PUNCH 项目状态\n'
    assert old.startswith(heading) and '## 当前状态 — run_017' not in old
    new='''
## 当前状态 — run_017（2026-10-23，Asia/Shanghai）

**WARNING（离线准备完成）：具备申请最多五个探索性局部敏感性 Job 的条件；当前求解授权、实际入队和新 FE 均为 0。** 合作方确认力/位移单位及球径，名义几何一致；用户接受现有固定环带为 idealised clamping baseline，完整夹具等效仍未验证。

真实 CAE 已生成五个独立材料变体并登记，非材料输入与历史基线一致。新版探索性 Loss/窗口及五点归一化设计已冻结；指定 Project Settings 为 PERSISTED，五个 Preflight/Dry-run 全部通过，Queue 未变，28 项合成测试通过。见 [run_017 总结](../run/run_017/summary.md) 与 [冻结批次](../run/run_017/artifacts/prepared_batch.json)。

位移校正方法、无损伤适用性和数值充分性继续保留不确定性。此准入仅用于首批探索性研究，不是正式反演或材料验证。旧 run_016 阻塞记录保留，新声明/许可的作用单独记录。未来需用户明确授权最多五个具体输入，串行逐个审核，无自动重试。

**保留验证隔离协议继续有效：独立数据保留验证，存在历史信息暴露。** 本轮没有读取/哈希隐藏拉伸源或派生内容；不宣称完全盲测。完成后停止，不自动求解、优化或解盲。

'''
    replace_checked(status,heading+new+old[len(heading):].replace('## 当前状态 — run_016','## 历史状态 — run_016',1),'project_status_before.md')
    r=read(RUN/'run.json')
    r.update(status='WARNING',end_time=stamp,outcome=outcome,
      inputs=[dict(path='run/run_016/artifacts/private/main_qualification_report.md',role='Immutable prior qualification'),
              dict(path='run/run_017/artifacts/private/source_inventory.json',role='14 explicit source identities'),
              dict(path='run/run_017/artifacts/private/experimental_metadata.json',role='New source confirmation'),
              dict(path='run/run_017/artifacts/parameter_design.json',role='Frozen five points')],
      outputs=[dict(path='run/run_017/artifacts/'+p,role=p) for p in main_files+['agenthub_receipt.json','cae_candidate_manifest.json','manifest.json']],
      validation=[dict(check=name,status='PASS',evidence='run/run_017/artifacts/'+evidence,scope=scope) for name,evidence,scope in [
          ('Real CAE handoff','private/cae_handoff_verified.json','19 artifacts and actual session completion'),
          ('Five static candidate checks','private/cae/verification.json','Material-only changes, coverage and interpolation'),
          ('Public API preview','batch_preview_result.json','Five preflight and dry-run; no execution'),
          ('Synthetic tests','test_results.json','28 synthetic tests only'),
          ('Source preservation','private/integrity_check.json','14 explicit baseline files'),
          ('Privacy','privacy_check.json','Current private outputs ignored')]],
      errors=[dict(code='MODEL_LIMITATIONS_RETAINED',severity='WARNING',message='Correction, complete fixture equivalence, damage/model/numerical validity remain uncertain',
                   evidence='run/run_017/artifacts/private/main_preparation_report.md',resolution='Explicitly limited exploratory baseline; not formal inversion'),
              dict(code='CAE_VERIFIER_COMMENT_BOUNDARY_REPAIRED',severity='WARNING',message='First independent verifier failed on two comment markers; verifier corrected and re-read passed without changing candidates',
                   evidence='run/run_017/artifacts/private/cae/operation_log.json',resolution='RESOLVED_TOOL_LOGIC; failure retained')])
    replace_checked(RUN/'run.json',json.dumps(r,ensure_ascii=False,indent=2)+'\n','run_initial.json')
    files=[p for p in RUN.rglob('*') if p.is_file() and p.name not in ('run.json','manifest.json','main_lease.json','lease.json') and '__pycache__' not in p.parts]
    save(OUT/'manifest.json',dict(observed_at=stamp,entries=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),
         visibility='PRIVATE' if 'private' in p.parts else 'PUBLIC') for p in sorted(files)],
         note='Excludes mutable run.json, own manifest, lease secrets and bytecode; future solver files do not exist'))
    print(json.dumps(dict(status='WARNING',main_task=lease['task_id'],registered_main_artifacts=len(artifacts),
            manifest_files=len(files),ready_to_request_five_jobs=True,authorized_jobs=0),indent=2))

if __name__=='__main__':main()
