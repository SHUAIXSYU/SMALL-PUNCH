"""Read-only final Queue verification and manual GUI handoff for two validations."""
from __future__ import annotations
import json,os
from pathlib import Path
import queue_validation as v

def main():
    assert not (v.RUN/'checkpoints/phase1_completed.json').exists()
    points=v.load_points();m=v.read(v.PRIVATE/'queue_manifest.json');ids=v.read(v.PRIVATE/'task_ids.json')
    api=v.AbqJobPilotClient();scoped=api.for_project(project_id=v.PID)
    env=v.q.environment(api);runtime=v.q.runtime_guard(deep=True)
    queue=scoped.list_jobs();history=api.list_project_jobs(project_id=v.PID).to_dict()
    assert queue['status']==history['status']=='OK'
    executable=[j for j in queue['jobs'] if j['raw_status'] in v.q.EXECUTABLE|v.q.ACTIVE]
    assert [j['job_name'] for j in executable]==v.ORDER
    details=[]
    for p,j in zip(points,executable):
        assert j['raw_status']=='QUEUED' and not j['started_at'] and not j['ended_at']
        assert Path(j['inp_path']).resolve()==(v.ROOT/p['inp_path']).resolve()
        assert Path(j['work_dir']).resolve()==(v.ROOT/p['working_dir']).resolve()
        assert (j['cpus'],j['gpus'],j['run_datacheck'],j['run_full'])==(14,0,True,True)
        hh=[h for h in history['jobs'] if h['job_name']==p['job_name']]
        assert len(hh)<=1
        if hh:
            detail=api.show_job(hh[0]['job_id'],project_id=v.PID).to_dict()
            assert len(detail['runs'])==1
            rr=detail['runs'][0]
            assert rr['queue_id']==j['queue_id'] and rr['raw_status']=='QUEUED'
            assert not rr['started_at'] and not rr['completed_at']
            details.append(detail)
    final={'queue':queue,'history':history,'queued_placeholder_details':details,
           'queue_ids':[j['queue_id'] for j in executable],'executable_count':2}
    assert final['queue_ids']==m['queue_ids'] and len(set(m['queue_ids']))==2
    pre=v.read(v.PRIVATE/'precheck.json')
    assert v.sha(v.RT/'settings.json')==pre['protected_after']['settings']
    db_changed=v.sha(v.PROJECT/'project.db')!=pre['protected_after']['db']
    v.save(v.PRIVATE/'final_readback.json',{'at':v.now(),'environment':env,'runtime':runtime,'queue':final,
                  'new_solver_started':False,'new_datacheck_started':False,'all_workdirs_empty':True,'source_inputs_unchanged':True,
                  'history_QUEUED_rows_are_not_started_attempts':True,'project_db_changed_after_enqueue_snapshot':db_changed,
                  'history_sync_source':{'public_history_reader':'ProjectHistoryRepository(read_only=True)',
                     'gui_sync_source':str(v.q.ABQ/'abqjobpilot/gui_app.py'),'gui_sync_sha256':v.sha(v.q.ABQ/'abqjobpilot/gui_app.py'),
                     'evidence':'GUI refresh invokes official sync_history_from_runtime; observed records have provenance runtime_json and null started/completed times'}})
    ledger={'at':v.now(),'authorized':2,'prepared':2,'queued':2,'started':0,'completed':0,'failed':0,'uncertain':0,
            'consumed_FE_attempts':0,'reserved_for_these_inputs':2,'automatic_retries':0,'third_job_authorized':False,
            'numeric_qualification':'NOT_EVALUATED','scientific_judgment':'NOT_EVALUATED'}
    v.save(v.PRIVATE/'budget_ledger.json',ledger)
    table='\n'.join(f"| {r['position']} | `{r['job_name']}` | `{r['queue_id']}` | QUEUED |" for r in m['points'])
    summary=f"""# run_044 — D01/I08 两项数值验证授权入队

**WARNING / TWO_VALIDATION_JOBS_QUEUED_AWAITING_MANUAL_START。** 第一阶段完成；当前只有两个获授权Job可执行，均QUEUED，尚未启动Datacheck或Solver。请用户在正确Project核对后手动点击一次 **Start Queue**。

Project：`E:\\Projects\\SMALL-PUNCH\\agenthub_sp_invopt\\abqjobpilot_project`；ID `{v.PID}`。

| 顺序 | Job | queue_id | 实际回读状态 |
| --- | --- | --- | --- |
{table}

## 当前检查与输入身份

新合法执行Run为run_044，原run_043准备和历史报告均保持不变。完整候选信息严格从run_043 prepared_batch.json读取，清单本身SHA与该Run输出记录一致；比较契约、比较实现、排序筛查实现及SPT目标hash同样核验。

两份完整INP hash：D01 `13e48fb2501a930f323b391c03e5f4e9ee6c3881959a837ca22cf94aab8939ca`，I08 `8b42fa6d30c4c3a7c47c3b732aafcd1fbd37b6588dfe5dff6b5a5aec7f647944`。每份相对各自原始源文件只进行已批准的0.0025→0.00125最大增量替换，其余每字节完全相同。初始增量0.001、总时间1、最小1e-12、最大增量数999999保持，材料/几何/网格/BC/接触/摩擦/加载/输出未变。独立工作目录为空，无覆盖、重复Queue或既有执行历史。

当前本机AbqJobPilot 0.2.2公开API确认Project身份及PERSISTED Settings；`D:\\ABAQUS2024\\Commands\\abq2024.bat`存在，14CPU、0GPU、Datacheck=True、Full=True。2/2本轮Preflight与2/2 Dry-run通过后才开始公开API enqueue-only。未直接修改Queue JSON或Project DB；预览阶段保护文件hash未变，API入队即时检查Project DB未变，最终Settings仍一致。随后官方运行历史同步产生了来源runtime_json的两项QUEUED占位记录，started_at/completed_at均为空；History的run_count=1不能被当作已消耗一次真实FE尝试。最终Queue回读输入、工作目录、资源、模式、顺序、唯一queue_id和无started_at证据一致。

Runner所有权ABSENT、当前状态IDLE、运行恢复评估CLEAN、Solver进程CLEAR。旧run_033 D09独立目录的历史锁仍保留，通用计划中的旧锁警告已记录，不属于新输出目录、未清理或复用。当前无阻塞。

## 授权和停止点

MAIN经正式AgentHub接口登记本次用户明确授权、两输入hash、每项最多一次Datacheck+成功后一次Full、14CPU/0GPU、零自动重试和仅用户GUI启动方式。当前准备2、入队2、实际启动0、实际FE消耗0，额度仅保留给这两份冻结输入，不允许第三Job或替代/重试。

用户已接受AUTO_STOP_UNAVAILABLE批量风险：单项失败或警告后，Runner可能继续另一项；本机代码仍没有按求解结果可靠自动fail-stop，人工Stop After Current不能替代该能力。Codex没有点击GUI、调用Abaqus或启动后台求解程序。

两项统一完成后所需MAIN真实终态审计、真实ODB只读提取、MAIN五指标与Loss排序分析任务已在Hub登记，并以依赖约束隔离；目前未唤醒ODB会话，未宣称已完成求解或数值资格。只有用户通知运行结束后才开展第二阶段，严格使用run_043冻结协议，失败/不完整保留原始证据、不重试。

授权、每次API请求/响应、逐项回读、budget_ledger及最终完整Queue证据位于artifacts/private/。封存拉伸及其派生资料未访问，历史信息暴露和BLOCKED结论保留；无额外BO/DE、RL或Git提交。现在停止，等待用户GUI手动Start Queue。
"""
    (v.RUN/'summary.md').write_text(summary,encoding='utf-8')
    files=[v.PRIVATE/'authorization_scope.json',v.PRIVATE/'precheck.json',v.PRIVATE/'queue_manifest.json',v.PRIVATE/'final_readback.json',
           v.PRIVATE/'budget_ledger.json',v.ART/'queue_validation.py',v.ART/'finalize_phase1.py',v.RUN/'summary.md']+sorted(v.RECEIPTS.glob('*.json'))
    manifest={'version':'run044-phase1-evidence-v1','at':v.now(),'files':[{'path':v.rel(p),'sha256':v.sha(p),'bytes':p.stat().st_size} for p in files]}
    v.save(v.PRIVATE/'evidence_manifest.json',manifest)
    hub=v.Hub(v.ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);actor=ids['identity']
    task=hub.create_task(actor['agent_id'],'MAIN','record_two_validation_manual_start_handoff',{'run':'run_044','queue_manifest_sha256':v.sha(v.PRIVATE/'queue_manifest.json')},'run044-final-handoff-v1',depends=(ids['confirm_task_id'],))
    lease=hub.claim(task['task_id'],actor,'run044-handoff-claim-v1');v.save(v.PRIVATE/'handoff_lease.json',lease)
    for p in [v.RUN/'summary.md',v.PRIVATE/'budget_ledger.json',v.PRIVATE/'evidence_manifest.json',v.PRIVATE/'final_readback.json']:
        hub.artifact(task['task_id'],actor['agent_id'],p,{'run':'run_044','scope':'queue-only handoff, not a solve'},version='run044-v1')
    hub.finish(lease,{'status':m['status'],'queued':2,'started':0,'consumed':0,'queue_ids':m['queue_ids'],'manual_gui_start_required':True},evidence_state='RECORDED',science_state='NOT_EVALUATED')
    assert hub.verify_chain()
    run=v.read(v.RUN/'run.json');run['status']='WARNING';run['end_time']=v.now();run['phase1_status']=m['status'];run['phase2_status']='AWAITING_USER_COMPLETION'
    run['errors']=[{'code':'HISTORY_PLACEHOLDER_REVIEW','severity':'RECOVERED','message':'Initial final-readback guard expected no History record; official runtime history sync introduced QUEUED placeholders. Read-only show_job verified matching queue_ids, no start/completion and no outputs; no re-enqueue.'}]
    run['outputs']=[{'path':r['path'],'sha256':r['sha256']} for r in manifest['files']]+[{'path':v.rel(v.PRIVATE/'evidence_manifest.json'),'sha256':v.sha(v.PRIVATE/'evidence_manifest.json')}]
    run['validation']=[{'check':'frozen_input_hash_and_exact_single_change','status':'PASS','evidence':'two full hashes, original bytes except maximum increment, comparison contract unchanged'},
      {'check':'current_public_previews','status':'PASS','evidence':'2/2 Preflight and dry-run, PERSISTED Settings, proper Project/resources'},
      {'check':'real_queue_readback','status':'PASS','evidence':'only two executable jobs, correct order and unique ids, both QUEUED, zero starts'},
      {'check':'AgentHub_authorization_and_budget','status':'PASS','evidence':'authorized2, queued2, started0, consumed0, chain valid'},
      {'check':'automatic_fail_stop','status':'WARNING','evidence':'unavailable; explicit batch risk accepted by user'},
      {'check':'historical_isolated_D09_lock','status':'WARNING','evidence':'retained; current runtime CLEAN/owner ABSENT/processes CLEAR'},
      {'check':'boundary_and_sealed_holdout','status':'PASS','evidence':'no solver/datacheck/retry/extra job or sealed data access'}]
    tmp=v.RUN/'run.json.tmp';v.save(tmp,run);os.replace(tmp,v.RUN/'run.json')
    v.save(v.RUN/'checkpoints/phase1_completed.json',{'at':run['end_time'],'status':m['status'],'queue_ids':m['queue_ids'],'started':0,
        'handoff_task_id':task['task_id'],'evidence_manifest_sha256':v.sha(v.PRIVATE/'evidence_manifest.json')})
    v.save(v.ART/'manifest.json',{'version':'run044-evidence-index-v1','private_manifest_path':v.rel(v.PRIVATE/'evidence_manifest.json'),'private_manifest_sha256':v.sha(v.PRIVATE/'evidence_manifest.json'),'file_count':len(files)})
    index=v.ROOT/'run/README.md';text=index.read_text(encoding='utf-8');assert '## run_044 — 两项数值验证授权入队' not in text
    index.write_text(text.rstrip()+'\n\n## run_044 — 两项数值验证授权入队\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_044 | D01/I08冻结验证输入授权登记、当前预检查与一次性queue-only入队 | WARNING / TWO_VALIDATION_JOBS_QUEUED_AWAITING_MANUAL_START | [summary](run_044/summary.md) |\n\n两项QUEUED，0启动，等待用户GUI一次Start Queue。\n',encoding='utf-8')
    status=v.ROOT/'status/PROJECT_STATUS.md';text=status.read_text(encoding='utf-8');assert '## 当前状态 — run_044' not in text
    block='## 当前状态 — run_044（2026-10-26，Asia/Shanghai）\n\n**WARNING / TWO_VALIDATION_JOBS_QUEUED_AWAITING_MANUAL_START。** 用户明确批准run_043两个冻结验证Job一次性入队，14CPU/0GPU、每项一次Datacheck+Full、零重试、仅用户GUI启动，并接受无可靠自动fail-stop。完整哈希/唯一最大增量替换及当前2/2 Preflight、2/2 dry-run通过；已通过公开API按D01→I08入队，恰好两项QUEUED、唯一queue_id，实际启动/预算消耗0。Hub已登记授权、Queue证据和未来统一ODB/五指标/排序分析任务；当前停止等待用户人工Start Queue。详见[run_044报告](../run/run_044/summary.md)。未启动Solver/datacheck，旧D09锁隔离保留且运行状态CLEAN，无额外Job、BO/DE/RL、Git提交或解盲。\n\n'
    status.write_text(text.replace('# SMALL-PUNCH 项目状态\n\n','# SMALL-PUNCH 项目状态\n\n'+block,1),encoding='utf-8')
    print(json.dumps({'status':m['status'],'queue_ids':m['queue_ids'],'queued':2,'started':0,'blocking':False,'hub_chain':hub.verify_chain()}))

if __name__=='__main__':main()
