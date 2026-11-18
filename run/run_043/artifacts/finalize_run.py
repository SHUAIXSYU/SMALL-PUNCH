"""MAIN checks real CAE byte edits, freezes artifacts and records research decisions."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from datetime import datetime
from pathlib import Path

ROOT=Path(r'E:\Projects\SMALL-PUNCH');RUN=ROOT/'run/run_043';ART=RUN/'artifacts';PRIVATE=ART/'private';MAIN=PRIVATE/'main';CAE=PRIVATE/'cae'
sys.path.insert(0,str(ROOT))
from agenthub_sp_invopt.hub import Hub

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def now():return datetime.now().astimezone().isoformat()
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x',encoding='utf-8') as stream:json.dump(v,stream,ensure_ascii=False,indent=2);stream.write('\n')
def atomic(p,v):
    tmp=p.with_suffix(p.suffix+'.tmp');save(tmp,v);os.replace(tmp,p)

def main():
    assert not (RUN/'checkpoints/completed.json').exists()
    analysis=read(MAIN/'analysis.json');baseline=read(PRIVATE/'baseline_audit.json');contract=read(ART/'comparison_contract.json');ids=read(ART/'task_ids.json')
    result=read(CAE/'structured_result.json');preview=read(CAE/'preview_result.json');static=read(CAE/'static_verification.json')
    hub=Hub(ROOT/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
    assert hub.task(ids['cae_task_id'])['execution_state']=='COMPLETED'
    received=[m for m in hub.poll_messages(ids['identity']) if m['task_id']==ids['cae_task_id']]
    assert received,'Real CAE completion message missing'
    for item in result['artifacts']:assert sha(ROOT/item['path'])==item['sha256']
    assert result['comparison_contract_sha256']==sha(ART/'comparison_contract.json')
    assert result['baseline_audit_sha256']==sha(PRIVATE/'baseline_audit.json')
    assert result['preflight_passed']==result['dry_run_passed']==2
    assert preview['settings']=='PERSISTED' and preview['abqjobpilot_version']=='0.2.2'
    assert preview['queue_unchanged'] and preview['settings_unchanged'] and preview['new_queue_records']==0
    assert not preview['solver_started'] and not preview['datacheck_started']
    old=b'0.001, 1., 1e-12, 0.0025';new=b'0.001, 1., 1e-12, 0.00125';points=[]
    for base,candidate,pv in zip(baseline['records'],result['candidates'],preview['points']):
        assert base['point_id']==candidate['point_id']==pv['point_id']
        source=(ROOT/base['source_inp']).read_bytes();actual=(ROOT/candidate['inp_path']).read_bytes()
        assert source.count(old)==1 and actual==source.replace(old,new,1)
        assert sha(ROOT/base['source_inp'])==base['source_inp_sha256']==candidate['source_sha256']
        assert sha(ROOT/candidate['inp_path'])==candidate['inp_sha256']==pv['inp_sha256']
        assert sha(ROOT/candidate['parameters_path'])==candidate['parameters_sha256']
        params=read(ROOT/candidate['parameters_path'])
        assert params['sigma_y_mpa']==base['sigma_y_mpa'] and params['n']==base['n']
        assert candidate['job_name']==base['job_name'] and candidate['working_dir']==base['working_dir']
        assert (ROOT/candidate['working_dir']).is_dir() and not any((ROOT/candidate['working_dir']).iterdir())
        assert not (ROOT/candidate['expected_odb']).exists()
        assert (pv['request']['cpus'],pv['request']['gpus'],pv['request']['run_datacheck'],pv['request']['run_full'])==(14,0,True,True)
        assert pv['preflight']['status']=='PREVIEW_READY' and pv['dry_run']['status']=='DRY_RUN_READY'
        assert not pv['dry_run']['queue_file_mutated'] and not pv['dry_run']['solver_started']
        points.append({**candidate,'baseline_result_path':base['result_path'],'baseline_result_sha256':base['result_sha256'],
                       'baseline_fd_path':base['fd_path'],'baseline_fd_sha256':base['fd_sha256'],
                       'baseline_odb_path':base['source_odb'],'baseline_odb_sha256':base['source_odb_sha256'],
                       'baseline_loss':base['loss'],'only_edit':{'old_maximum_increment':.0025,'new_maximum_increment':.00125},
                       'preflight':'PREVIEW_READY','dry_run':'DRY_RUN_READY','queue_id':None,'solver_status':'NOT_AUTHORIZED_NOT_STARTED'})
    assert len(points)==2 and len(set(p['inp_sha256'] for p in points))==2
    tests=[]
    for path,count in [('run/run_023/artifacts/test_compare_validation.py',12),('run/run_043/artifacts/test_ranking_screen.py',4)]:
        proc=subprocess.run([sys.executable,'-B',str(ROOT/path)],cwd=ROOT,capture_output=True,text=True)
        tests.append({'path':path,'sha256':sha(ROOT/path),'return_code':proc.returncode,'expected_count':count,'output':proc.stdout+proc.stderr})
        assert proc.returncode==0 and f'Ran {count} tests' in proc.stdout+proc.stderr
    save(PRIVATE/'test_results.json',{'at':now(),'tests':tests,'purpose':'comparison and future ranking screen only, no FE execution'})
    prepared={'version':'run043-two-point-refinement-prepared-v1','frozen_at':now(),'status':'PREPARED_NO_SOLVER_AUTHORIZATION',
              'project_id':preview['project_id'],'project_path':'agenthub_sp_invopt/abqjobpilot_project',
              'comparison_contract_path':rel(ART/'comparison_contract.json'),'comparison_contract_sha256':sha(ART/'comparison_contract.json'),
              'cae_task_id':ids['cae_task_id'],'cae_result_sha256':sha(CAE/'structured_result.json'),
              'candidate_numeric_version':'run043-standard-m00125-pending-v1','baseline_numeric_version':'run030-standard-m0025-hollomon-v1',
              'loss_version':contract['loss_version'],'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,
              'new_solver_authorization':False,'new_enqueue_authorization':False,'automatic_retries':0,
              'order':[p['job_name'] for p in points],'points':points}
    save(ART/'prepared_batch.json',prepared)
    main_review={'at':now(),'cae_task_id':ids['cae_task_id'],'real_message_received':True,'artifacts_rehashed':len(result['artifacts']),
                 'all_other_input_bytes_identical':True,'preflight_passed':2,'dry_run_passed':2,'queue_unchanged':True,
                 'new_solver_starts':0,'new_datacheck_starts':0,'new_enqueues':0,'candidate_hashes':[p['inp_sha256'] for p in points]}
    save(MAIN/'engineering_review.json',main_review)
    d=analysis['baseline']['D01'];i=analysis['baseline']['I08'];gap=contract['baseline_gap_i08_minus_d01']
    rows='\n'.join(f"| {p['job_name']} | `{p['inp_sha256']}` | {p['preflight']} / {p['dry_run']} |" for p in points)
    residual_table='\n'.join(f"| {r['point_id']} | {r['lower_mm']:.1f}–{r['upper_mm']:.1f} | {r['rmse_n']:.3f} | {r['bias_n']:.3f} | {r['fraction_of_full_Loss']*100:.2f}% |" for r in analysis['residual_intervals'])
    true_table='\n'.join(f"| {r['true_total_strain']:.3g} | {r['D01_true_stress_mpa']:.3f} | {r['I08_true_stress_mpa']:.3f} | {r['I08_minus_D01_mpa']:.3f} |" for r in analysis['true_total_constitutive_samples'] if r['true_total_strain'] in [.001,.002,.01,.05,.1,.2,.4])
    report=f"""# run_043 — D01/I08 低Loss可识别性与数值资格准备

## 已有FE身份和质量

两点均有公开AbqJobPilot单次成功Datacheck/Full记录；INP、实际ODB与已完成真实ODB提取结果的SHA-256重新核验，已有派生文件和来源一致。D01：σy={d['sigma_y_mpa']:.15g} MPa，n={d['n']:.15g}；I08：σy={i['sigma_y_mpa']:.15g} MPa，n={i['n']:.15g}。既有数值契约为run030-standard-m0025-hollomon-v1。D01有408个接受增量、3次cutback；I08为415、7。最大保存帧PEEQ分别{d['max_saved_peeq']:.9f}、{i['max_saved_peeq']:.9f}，均小于材料表0.9；接受态仅既有零力矩提示，大应变标题在被拒试算中，DAT接触跟踪提示保留。质量继续WARNING/PROVISIONAL，未以软件成功宣称物理有效。

## F–D和区间残差

严格沿用run017-exploratory-fd-v1的241点0–1.2 mm目标、F_ref=1428.9 N、线性插值，不平滑、不移零点、不裁窗、不外推。D01原始接受历史409点，I08为416点，两者投影到同一冻结网格比较。独立复算Loss分别{d['loss']:.15g}、{i['loss']:.15g}，间隔{gap:.15g}；RMSE为{d['rmse_n']:.3f} N和{i['rmse_n']:.3f} N。

两条FE曲线互比RMSE={analysis['pair_fd']['rmse_n']:.3f} N（固定F_ref的4.04%），最大差{analysis['pair_fd']['max_abs_difference_n']:.3f} N位于{analysis['pair_fd']['max_abs_at_mm']:.3f} mm。近似标量Loss不代表两条F–D完全等同。D01整体偏低（均值{d['bias_n']:.3f} N），I08整体偏高（{i['bias_n']:.3f} N）；残差的位移分布含有区分信息，不能据两个近似Loss断言严格非唯一性。

下表四区间按预定等宽描述性分箱，前三段右端开区间、最后含终点，完整分割241点；没有改变拟合窗口或权重。

| 点 | 位移 mm | 区间RMSE N | 平均偏差 N | 占该点完整Loss |
| --- | --- | ---: | ---: | ---: |
{residual_table}

D01约54.1%的平方残差来自0–0.3 mm；I08约89.8%来自0.3–0.9 mm。解释和未来识别设计可以利用此形状差异，但当前Loss保持原定义。

## 预测单轴真总应变本构差异

只调用冻结inverse/hollomon.py候选公式，E=210 GPa、ν=0.3，没有读取真实拉伸文件或其派生结果。D01与I08的屈服真总应变分别{d['yield_true_total_strain']:.10g}、{i['yield_true_total_strain']:.10g}；屈服应力差112.702 MPa（相对D01约74.0%），硬化指数差0.0762624。相同真总应变下的预测如下：

| 真总应变 | D01 MPa | I08 MPa | I08−D01 MPa |
| ---: | ---: | ---: | ---: |
{true_table}

真总应变0.002时差92.08 MPa（约47.8%），0.01时差85.83 MPa（30.8%），0.1时差46.06 MPa（9.71%）；到0.4时排序交叉，I08低约8.48 MPa。低应变屈服与较大应变硬化可发生补偿，不能把两条预测曲线视为同一材料答案。

实际Abaqus应力–等效塑性应变表逐行读取既有INP：D01 51行、I08 40行，范围0–0.9，没有重新采样材料输入。p=0.1时分别约476.635、522.350 MPa；共同保存PEEQ包络上限p={analysis['strain_scope']['common_saved_peeq_envelope'][1]:.9f}处分别约720.846、688.659 MPa，差−32.187 MPa。I08自身保存最大p约0.65336，两个表都覆盖该坐标。最大PEEQ只是多轴积分点标量包络，不能当成真实单轴应变历程或说明试样大部分材料达到该值；塑性坐标与真总应变图严格区分。表外0.9不外推。

## 稀疏数据中的可识别性

合并run_039的19点与run_042的5个新可评分点，共24个同数值/Loss契约的真实FE点。Loss≤2×最低值仅D01和I08；Loss≤0.002包含D01/I08/I04/BO04，σy约152.3–385.1 MPa、n约0.0810–0.2307。这是人为阈值下的已观测集合，不是置信区间。已有点支持多个竞争候选及高σy/低n补偿方向；尚没有沿谷地连续剖面，也不能证明全局唯一或非唯一。

D01距σy下界150 MPa仅2.309 MPa。边界外未知，当前仍保持150–1000 MPa及n 0.02–0.50，不为更低Loss扩界。残差形状有区分力，因此下一步应做定向参数剖面和数值资格，而非只由标量Loss接近就认定不可辨识。本轮散点全部为真实计算值，没有把代理插值当成Loss真值。

## 两个待验证候选与工程证据

真实CAE任务 `{ids['cae_task_id']}` 已由独立会话领取、完成并向MAIN回传。MAIN收到消息，重算{len(result['artifacts'])}项文件哈希并独立验证每份候选 `new_bytes == old_bytes.replace(old_static_line,new_static_line,1)`。唯一变化是最大增量0.0025→0.00125，文件各增加1字节；其余每个字节（材料、几何、网格、BC、接触、摩擦、加载、输出及注释）完全保持来源定义。初始0.001、总时间1、最小1e-12、最大增量数999999保持。独立文件和空工作目录，无覆盖。

| Job | 完整INP SHA-256 | 当前工程预览 |
| --- | --- | --- |
{rows}

AbqJobPilot 0.2.2正式Project身份匹配、Settings=PERSISTED，14 CPU/0 GPU，Datacheck/Full选项仅用于预览；2/2 Preflight和2/2 Dry-run通过。Queue/Settings未变化，0次实际入队、Solver或Datacheck。预览不证明Abaqus语法、许可证、收敛或更小增量必然更准确。完整工作目录及输入来源见prepared_batch.json。

## 求解前冻结判据与排序筛查

复用run_023已测试的比较实现及完整SHA，原12项比较测试通过，新增排序筛查4项测试通过。两对均以各自0.0025基线为主比较，固定241点不变：F–D差RMSE≤2 N，最大绝对差≤7.1445 N，最大正则相对差≤5%（分母max(|基线力|,71.445 N)），|ΔLoss|≤0.00065，最大保存帧PEEQ差≤0.02；还需真实执行身份、完整窗口、材料覆盖和无未解释阻塞性数值问题。

另行冻结1.10–1.16 mm接受帧/接触CPRESS、COPEN、node23及由网格拓扑确定的邻近区域、cutback/接受拒绝尝试和警告、最大PEEQ与成本比较。COPEN非有限值或|值|≥1e30视为诊断缺失，保留原始值；CPRESS>0是压力建立代理，不是完整接触状态证明。局部诊断不能替代全窗口门槛。

原Loss间隔g={gap:.15g}。未来实际结果齐备后计算S=|ΔL_D01|+|ΔL_I08|及R=S/g；若S<g且两点各自数值资格通过，则这两次**已观测细化**不会翻转原排序；若S≥g，标记排序敏感复核，同时直接报告细化后的两点实际差值和排序，不能只凭筛查宣布翻转。任何缺失或资格失败均不能声称排序已稳定。S不是严格求解误差上界，单次细化也不是全域收敛证明。单点工程阈值的通过并不自动保证这么小的Loss间隔显著。

## 明确科研建议

值得另行授权这两个定向Job：它们直接检验当前最有竞争力的两条候选曲线，而不是再消耗宽域优化预算。两点历史计算时长合计541s；更小最大增量提高名义增量数，实际成本和cutback变化未知，未来记录Datacheck/Full实际时间，不作确定耗时承诺。本Run没有求解授权，不入队、不执行。

若两项验证通过且排序诊断完整，下一步优先研究补偿方向上的解集宽度与横向区分，而非立即继续BO/DE只追求更小Loss。若未通过，先形成点级数值问题诊断，不自动再减半或修改接触/网格。当前可以将两条曲线及输入完整哈希冻结为**探索性候选集合**，但尚不宜冻结唯一最终反演本构或宣布独立验证已就绪；应先完成两点数值资格和不确定性边界，再由用户明确授权读取保留拉伸数据。真正的独立验证不得据其结果回调当前反演。

run_015历史信息暴露、run_025 BLOCKED及所有先前证据保持；没有访问封存拉伸内容，没有新增FE/DE/BO/RL或Git提交。完成准备后停止，等待明确计算授权。
"""
    (MAIN/'REPORT.md').write_text(report,encoding='utf-8')
    decision={'at':now(),'status':'READY_TO_REQUEST_TWO_POINT_REFINEMENT_WITH_RANKING_GATE','worth_two_jobs':True,
              'current_solver_authorization':False,'enqueue_authorization':False,'unique_constitutive_identification':False,
              'exploratory_candidate_set_frozen':True,'final_independent_tensile_validation_ready':False,
              'next_if_pass':'Compensation-valley/profile and uncertainty assessment before further BO/DE',
              'next_if_fail':'Point-specific diagnosis; no automatic further refinement or model changes',
              'original_gap':gap,'ranking_rule':contract['ranking_screen']}
    save(MAIN/'research_decision.json',decision)
    summary=f"""# run_043 — 低Loss可识别性与数值资格准备

**WARNING / READY_TO_REQUEST_TWO_POINT_REFINEMENT。** D01/I08已有输入、ODB、单次执行与数值证据复核通过。两者Loss接近但残差形状不同：D01整体偏低约29.1 N，I08偏高约25.2 N；两条FE曲线互比RMSE57.71 N。预测真总应变1%处应力约278.97/364.81 MPa，差85.83 MPa。现有24个有效点支持多个竞争候选及补偿趋势，尚不能确定唯一材料本构。

真实CAE已准备两个独立候选，仅最大增量0.0025→0.00125，其余逐字节不变；2/2 Preflight、2/2 Dry-run通过。原五项工程判据及独立Loss排序敏感性筛查已冻结（基线间隔{gap:.10g}），比较12项与新增排序4项测试通过。当前0入队、0Solver/Datacheck。

建议申请这两项定向验证，通过后优先研究补偿谷地/不确定性；不直接恢复BO/DE。可冻结探索性候选集合，最终本构及独立拉伸验证尚待数值资格和明确解盲授权。完整[分析报告](artifacts/private/main/REPORT.md)、[F–D与残差](artifacts/private/main/fd_differences_residuals.png)、[预测真总应变本构](artifacts/private/main/predicted_true_total_curves.png)、[Abaqus塑性表](artifacts/private/main/abaqus_plastic_curves.png)、[冻结比较协议](artifacts/comparison_contract.json)及[候选清单](artifacts/prepared_batch.json)。封存拉伸禁读和历史暴露声明保持，完成后停止。
"""
    (RUN/'summary.md').write_text(summary,encoding='utf-8')
    files=[PRIVATE/'baseline_audit.json',PRIVATE/'test_results.json',CAE/'structured_result.json',CAE/'byte_diff_evidence.json',CAE/'static_verification.json',CAE/'preview_result.json',CAE/'preview_integrity.json',ART/'comparison_contract.json',ART/'prepared_batch.json',ART/'ranking_screen.py',ART/'test_ranking_screen.py',ART/'analyze_candidates.py',ART/'bootstrap.py',ART/'finalize_run.py',RUN/'summary.md']
    files.extend(p for p in sorted(MAIN.iterdir()) if p.is_file())
    evidence={'version':'run043-main-evidence-v1','at':now(),'files':[{'path':rel(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]}
    save(MAIN/'evidence_manifest.json',evidence)
    task=ids['review_task_id'];lease=hub.claim(task,ids['identity'],'run043-main-final-review-v1');save(PRIVATE/'review_lease.json',lease)
    for path in [MAIN/'REPORT.md',MAIN/'analysis.json',MAIN/'research_decision.json',MAIN/'engineering_review.json',MAIN/'evidence_manifest.json',ART/'prepared_batch.json',RUN/'summary.md']:
        hub.artifact(task,ids['identity']['agent_id'],path,{'run':'run_043','scope':'MAIN independent offline analysis and candidate review'},version='run043-v1')
    hub.finish(lease,{'status':decision['status'],'prepared':2,'preflight':2,'dry_run':2,'no_actual_enqueue_solver_datacheck':True,
                      'original_loss_gap':gap,'report':rel(MAIN/'REPORT.md'),'report_sha256':sha(MAIN/'REPORT.md')},evidence_state='RECORDED',science_state='WARNING')
    assert hub.verify_chain()
    run=read(RUN/'run.json');run['status']='WARNING';run['end_time']=now()
    run['outputs']=[{'path':v['path'],'sha256':v['sha256']} for v in evidence['files']]+[{'path':rel(MAIN/'evidence_manifest.json'),'sha256':sha(MAIN/'evidence_manifest.json')}]
    run['validation']=[{'check':'existing_D01_I08_identity','status':'PASS','evidence':'INP/ODB/source extraction hashes, single completed attempts, no numerical blocker'},
         {'check':'SPT_Loss_and_offline_constitutive_comparison','status':'PASS','evidence':'fixed 241 points, original Loss reproduced, analytic and actual Abaqus plastic tables distinguished'},
         {'check':'future_comparison_tests','status':'PASS','evidence':'12 comparison and 4 ranking tests; contract frozen before solve'},
         {'check':'real_CAE_AgentHub_handoff','status':'PASS','evidence':'real message received and candidate bytes independently verified'},
         {'check':'two_candidate_Preflight_Dry_run','status':'PASS','evidence':'2/2 each, Settings=PERSISTED, queue unchanged'},
         {'check':'ranking_and_identifiability','status':'WARNING','evidence':'new candidates not solved; original gap small, no unique material conclusion'},
         {'check':'execution_and_holdout_boundary','status':'PASS','evidence':'no new solver/datacheck/enqueue or sealed data access; historic exposure retained'}]
    atomic(RUN/'run.json',run)
    save(RUN/'checkpoints/completed.json',{'at':run['end_time'],'status':'WARNING','cae_task_id':ids['cae_task_id'],'review_task_id':task,'evidence_manifest_sha256':sha(MAIN/'evidence_manifest.json')})
    save(ART/'manifest.json',{'version':'run043-evidence-index-v1','private_manifest_path':rel(MAIN/'evidence_manifest.json'),'private_manifest_sha256':sha(MAIN/'evidence_manifest.json'),'file_count':len(files)})
    index=ROOT/'run/README.md';text=index.read_text(encoding='utf-8');assert '## run_043 — 低Loss可识别性与数值资格准备' not in text
    index.write_text(text.rstrip()+'\n\n## run_043 — 低Loss可识别性与数值资格准备\n\n| Run | 目标 | 状态 | 报告 |\n| --- | --- | --- | --- |\n| run_043 | D01/I08残差及预测本构、排序协议、真实CAE两项增量验证输入与预览 | WARNING / PREPARED_NO_SOLVER_AUTHORIZATION | [summary](run_043/summary.md) |\n\n2/2 Preflight和dry-run通过；无入队或求解，等待新授权。\n',encoding='utf-8')
    status=ROOT/'status/PROJECT_STATUS.md';text=status.read_text(encoding='utf-8');assert '## 当前状态 — run_043' not in text
    block='## 当前状态 — run_043（2026-10-26，Asia/Shanghai）\n\n**WARNING / READY_TO_REQUEST_TWO_POINT_REFINEMENT。** D01/I08完整输入和ODB证据复核；Loss近似但残差区间不同、预测本构小中应变差异明显，尚不能唯一识别。真实CAE完成两项仅最大增量0.0025→0.00125的独立候选，MAIN逐字节验证，2/2 Preflight、2/2 dry-run通过。原五指标及Loss排序敏感性协议在求解前冻结，12+4项离线测试通过；0入队/0Solver/Datacheck。建议申请两次定向数值验证，通过后优先补偿谷地和参数不确定性，不直接继续BO/DE；最终单一本构与独立拉伸验证仍待资格和明确解盲授权。见[run_043报告](../run/run_043/summary.md)。历史BLOCKED、信息暴露和封存拉伸禁读规则保留。\n\n'
    status.write_text(text.replace('# SMALL-PUNCH 项目状态\n\n','# SMALL-PUNCH 项目状态\n\n'+block,1),encoding='utf-8')
    print(json.dumps({'status':'WARNING','prepared':2,'preflight':2,'dry_run':2,'new_solver':0,'new_enqueue':0,'hub_chain':hub.verify_chain(),'candidate_hashes':[p['inp_sha256'] for p in points]},ensure_ascii=False))

if __name__=='__main__':main()
