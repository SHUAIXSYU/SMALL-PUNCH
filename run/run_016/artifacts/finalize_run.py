"""Finish the current offline Run through public Hub methods; never launch FE."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from agenthub_sp_invopt.hub import Hub

RUN = ROOT/'run/run_016'
OUT = RUN/'artifacts'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def atomic_text(path, text, checkpoint):
    if path.exists():
        with (RUN/'checkpoints'/checkpoint).open('xb') as f:
            f.write(path.read_bytes())
    temp = path.with_name(path.name+'.run016.tmp')
    with temp.open('x', encoding='utf8') as f:
        f.write(text)
    if path.suffix == '.json':
        json.loads(temp.read_text(encoding='utf8'))
    temp.replace(path)


def main():
    stamp = datetime.now().astimezone().isoformat()
    private_paths = [p.relative_to(ROOT).as_posix() for p in (OUT/'private').rglob('*') if p.is_file()]
    proc = subprocess.run(['git','check-ignore','--stdin','-z'], input=('\0'.join(private_paths)+'\0').encode('utf8'),
                          cwd=ROOT, capture_output=True)
    ignored = set(proc.stdout.decode('utf8').rstrip('\0').split('\0'))
    if proc.returncode != 0 or ignored != set(private_paths):
        raise ValueError('Private output ignore coverage incomplete')
    tracked = subprocess.run(['git','ls-files','run/run_016/artifacts/private'], cwd=ROOT,
                             capture_output=True, text=True, encoding='utf8', check=True).stdout
    if tracked.strip():
        raise ValueError('Private data unexpectedly tracked')
    privacy = dict(observed_at=stamp, private_output_count=len(private_paths),
                   all_ignored=True, tracked_private_count=0, heldout_new_access=False)
    write_new(OUT/'privacy_check.json', privacy)

    identity_data = json.loads((OUT/'hub_tasks.json').read_text(encoding='utf8'))
    identity = identity_data['identity']
    lease = json.loads((OUT/'private/main_lease.json').read_text(encoding='utf8'))
    hub = Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3', lease_seconds=1800)
    hub.heartbeat(lease)
    static = ['private/collaborator_declaration.json', 'private/main_qualification_report.md',
              'private/worker_verification.json', 'private/integrity_check.json', 'private/loss_review.json',
              'parameter_and_budget_protocol.md', 'inversion_qualification_contract.json',
              'loss_test_results.json', 'loss_test_log.txt', 'test_loss_qualification.py',
              'review_loss.py', 'freeze_qualification.py', 'authorization_guard_check.json',
              'privacy_check.json', 'finalize_run.py']
    records = []
    for rel in static:
        record = hub.artifact(lease['task_id'], identity['agent_id'], OUT/rel,
                              dict(run='run_016', method='Offline qualification; no new FE',
                                   heldout_access=False, original_run015_preserved=True),
                              version='run016-v1')
        records.append(dict(artifact_id=record['artifact_id'], path=(OUT/rel).relative_to(ROOT).as_posix(),
                            sha256=record['sha256']))
    outcome = dict(run='run_016', audit_execution='COMPLETED', qualification='BLOCKED',
                   cae_geometry='BLOCKED', spt_force_units='UNRESOLVED', displacement='WARNING',
                   loss_and_window='PROVISIONAL', formal_loss=None, loss_tests_passed=19,
                   worker_artifacts_verified=14, parameter_domain=dict(sigma_y_mpa=[150,1000], n=[.02,.50]),
                   protocol='run/run_016/artifacts/inversion_qualification_contract.json',
                   first_batch_ready=False, current_recommended_jobs=0, contingent_pilot_jobs=5,
                   new_jobs_authorized=0, new_jobs_executed=0,
                   blind_status='Independent retained validation with historical exposure; no new access',
                   report='run/run_016/artifacts/private/main_qualification_report.md')
    hub.finish(lease, outcome, evidence_state='RECORDED', science_state='WARNING')
    msg = hub.message(lease['task_id'], identity['agent_id'], 'MAIN', outcome,
                      'run016-main-qualification-complete-v1')
    write_new(OUT/'agenthub_receipt.json', dict(observed_at=stamp, task_id=lease['task_id'],
                  execution_state=hub.task(lease['task_id'])['execution_state'],
                  message_id=msg['message_id'], outcome=outcome, artifacts=records))

    summary = '''# run_016 — Experimental-to-FE Qualification

**BLOCKED（正式反演准入）；离线审计已完成。** 新增 Solver/Datacheck、Queue 写入、FE 搜索、RL、自动重试和 Git commit/push 均为 0。

## 实际完成

- 合作方条件作为新的私有声明登记，保留 run_015 原结论。
- MAIN 经 AgentHub 分配真实 CAE 与 ODB 会话；两任务完成，14 项产物哈希及完成消息核验通过，并留存 MAIN 确认。
- CAE 核对实际候选 INP 身份和名义试样尺寸；固定环带缺少已验证的下夹具接触等效性，实际冲头/夹持仍待确认。
- ODB 核对 SPT 两容器相同数值序列、标签冲突与预先登记的峰前窗口规则。单位冲突未解决；窗口保持 PROVISIONAL。
- MAIN 复现冻结的探索性 Loss，解释归一化含义；原 12 项加 7 项资格测试，共 19 项合成测试通过。Loss 实现及旧配置未改。
- 基于公开资料和明确工程假设，定版探索域及分阶段预算规范；这是离线协议，新 Job 授权仍为 0。

## 准入结论

CAE 几何 **BLOCKED**；SPT 单位 **UNRESOLVED**；位移定义 **WARNING**；Loss/窗口 **PROVISIONAL**。当前不具备申请 DE/BO 新 Job 的条件。未来解决资格问题后，可先申请最多 5 个先导计算（中心及两参数各正负方向），而不是自动消耗 48 个规划上限。

## 证据与修改

- [私有总审报告](artifacts/private/main_qualification_report.md)
- [CAE 私有报告](artifacts/private/cae/geometry_qualification.md)
- [ODB 私有报告](artifacts/private/odb/spt_qualification_report.md)
- [参数与预算协议](artifacts/parameter_and_budget_protocol.md)
- [定版协议身份](artifacts/inversion_qualification_contract.json)
- [Loss 测试](artifacts/loss_test_results.json)
- [AgentHub 登记](artifacts/agenthub_receipt.json)
- [证据清单](artifacts/manifest.json)

新文件仅在本 Run；更新 Run 索引及项目状态。8 个明确基线文件（SPT 源、候选输入、既有 FE CSV、Loss/配置、Abq Queue/project.db）哈希保持；原始实验/模型未编辑，外部项目未修改。所有可恢复实验数据位于 Git 忽略的私有区域。

## 隔离与停止

研究为“独立数据保留验证，存在历史信息暴露”。run_015 的 MAIN/ODB 暴露记录保留；本轮没有继续访问保留拉伸源及派生内容。严格独立审查需未接触者或隔离流程。

后续应先取得最小缺失条件、资格审查/必要模型变更授权，再冻结正式目标。BO 实现及合成验收尚待完成。建议不构成计算授权；本 Run 完成后停止。
'''
    atomic_text(RUN/'summary.md', summary, 'summary_initial.md')
    index = ROOT/'run/README.md'
    old_index = index.read_text(encoding='utf8')
    if '## 新授权 Run — run_016' in old_index:
        raise ValueError('Run already indexed')
    index_add = '''

## 新授权 Run — run_016

| Run | 阶段 | 目标 | 状态 | 总结 |
| --- | --- | --- | --- | --- |
| run_016 | Experimental-to-FE Qualification | 合作方声明、真实 CAE/ODB 准入审计、Loss 复核及分阶段预算 | BLOCKED（正式反演准入；离线完成） | [summary](run_016/summary.md) |

几何/夹具等效与载荷单位仍未解决；位移声明改善对应依据，Loss/窗口保持 PROVISIONAL。19 项合成测试通过，公开依据探索域和条件式预算已登记。新 Job 授权/执行均 0；保留历史信息暴露，不再访问保留拉伸数据。完成后停止。
'''
    atomic_text(index, old_index+index_add, 'run_index_before.md')
    status_path = ROOT/'status/PROJECT_STATUS.md'
    old_status = status_path.read_text(encoding='utf8')
    if '## 当前状态 — run_016' in old_status:
        raise ValueError('Status already updated')
    heading = '# SMALL-PUNCH 项目状态\n'
    if not old_status.startswith(heading):
        raise ValueError('Unexpected status header')
    current = '''
## 当前状态 — run_016（2026-10-23，Asia/Shanghai）

**BLOCKED（正式反演准入）；离线审计完成。** 真实 CAE/ODB 两项正式任务已完成并登记证据，MAIN 核验 14 项角色产物。名义试样尺寸相符，但固定夹持环带与实际下夹具接触未证明等效；SPT 力单位冲突仍未解决。合作方确认实际压头位移，校正细节仍待核验。Loss/窗口保持 PROVISIONAL，19 项合成测试通过。

公开资料与明确假设支持的新探索域及分阶段预算已定版，计算授权和执行仍为 0。当前不具备 DE/BO 首批新 Job 准入；解除阻塞后才考虑最多 5 个先导计算。run_014 单次求解授权已用完。见 [run_016 总结](../run/run_016/summary.md)。

**先读[保留验证隔离协议](../docs/Blind_Inversion_Protocol.md)。** 当前定义为“独立数据保留验证，存在历史信息暴露”；旧暴露审计保留。本轮未继续访问保留拉伸源或派生内容，后续独立审查需未接触者。完成后停止，不自动计算或解盲。

'''
    remainder = old_status[len(heading):].replace('## 当前状态 — run_015', '## 历史状态 — run_015', 1)
    atomic_text(status_path, heading+current+remainder, 'project_status_before.md')

    run = json.loads((RUN/'run.json').read_text(encoding='utf8'))
    run.update(status='BLOCKED', end_time=stamp, offline_work_completed=True,
               qualification=outcome, outputs=[dict(path=(OUT/rel).relative_to(ROOT).as_posix(), role=rel)
                   for rel in static+['agenthub_receipt.json','manifest.json']],
               validation=[dict(check='Real CAE/ODB handoff and hashes',status='PASS',evidence='run/run_016/artifacts/private/worker_verification.json',scope='two tasks, 14 artifacts'),
                           dict(check='Loss synthetic regression',status='PASS',evidence='run/run_016/artifacts/loss_test_results.json',scope='19 tests'),
                           dict(check='Protected allowlist integrity',status='PASS',evidence='run/run_016/artifacts/private/integrity_check.json',scope='8 baselined files'),
                           dict(check='Private artifacts ignored',status='PASS',evidence='run/run_016/artifacts/privacy_check.json',scope='current Run private files'),
                           dict(check='Experimental-to-FE qualification',status='BLOCKED',evidence='run/run_016/artifacts/private/main_qualification_report.md',scope='geometry, units, window and scientific readiness')],
               errors=[dict(code=code,severity='BLOCKED' if code in ('FIXTURE_NOT_QUALIFIED','FORCE_UNIT_UNRESOLVED') else 'WARNING',
                            message=message,evidence='run/run_016/artifacts/private/main_qualification_report.md',resolution='Future evidence/authorization; no automatic action')
                       for code,message in [('FIXTURE_NOT_QUALIFIED','Fixed annuli are not verified as actual support/contact'),
                                            ('FORCE_UNIT_UNRESOLVED','Conflicting XLSX and Origin load labels'),
                                            ('MEASUREMENT_AND_WINDOW_PROVISIONAL','Correction and undamaged window not independently qualified'),
                                            ('NUMERICAL_QUALITY_UNRESOLVED','Existing FE warnings and sensitivity require evaluation')]])
    atomic_text(RUN/'run.json', json.dumps(run,ensure_ascii=False,indent=2)+'\n', 'run_initial.json')
    files = [p for p in RUN.rglob('*') if p.is_file() and p.name not in ('run.json','manifest.json')
             and '__pycache__' not in p.parts and p.name not in ('main_lease.json','lease.json')]
    manifest = dict(observed_at=stamp, run='run_016', entries=[
        dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p), visibility='PRIVATE' if 'private' in p.parts else 'PUBLIC',
             role='evidence_or_protocol') for p in sorted(files)])
    write_new(OUT/'manifest.json', manifest)
    print(json.dumps(dict(status='BLOCKED', audit='COMPLETED', registered_main_artifacts=len(records),
                          manifest_files=len(files), privacy=privacy, outcome=outcome),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
