"""Prepare four new material-only variants of hash-verified I06. No Abaqus invocation."""
from common import *
import csv, re, difflib
import numpy as np
sys.path[:0]=[str(R), str(R/'run/run_055/artifacts'),str(R/'run/run_056/artifacts')]
from inverse.hollomon import generate_hollomon_table, stress_at_plastic_strain
from feature_core import extract
from review_science import parse_trials
from agenthub_sp_invopt.hub import Hub

def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def main():
    contract=read(R/'run/run_056/artifacts/private/prospective_design_contract.json')
    ss=read(P/'hub_session.json');hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400)
    hub.heartbeat(ss['lease']);hub.require_approval(ss['task_id'],'generate_inp')
    b=contract['baseline'];source=R/b['inp_path'];raw=source.read_bytes()
    assert sha(source)==b['inp_sha256'] and sha(R/'inverse/hollomon.py')==contract['material']['generator_sha256']
    diag=read(R/b['diagnostics_path']);result=read(R/b['result_path'])
    for s in diag['provenance']['source_files'].values(): assert sha(R/s['path'])==s['sha256']
    for path,h in result['artifact_hashes'].items(): assert sha(R/path)==h,path
    trial=parse_trials(diag['provenance']['source_files'])
    assert trial['accepted_increments']==439 and trial['cutback_count']==18
    assert trial['warning_counts']['ACCEPTED_TRIAL']=={'ZERO_MOMENT':1}
    assert result['datacheck_status']['return_code']==0 and result['full_status']['return_code']==0
    assert result['full_status']['odb_job_status']=='JOB_STATUS_COMPLETED_SUCCESSFULLY'
    assert not result['numerical_blocking_issues']
    assert all(diag['identity_checks'].values())
    for field in ['inp_sha256','odb_sha256','job_name','queue_id']: assert result[field]==b[field]
    assert b['sigma_y_mpa']==236.49902622197678 and b['n']==.0968
    pp=read(R/b['params_path']);assert pp['sigma_y_mpa']==b['sigma_y_mpa'] and pp['n']==b['n']
    pre,post,rows=split_plastic(raw)
    rebuilt=generate_hollomon_table(b['sigma_y_mpa'],b['n'],max_plastic_strain=.9,relative_tolerance=.001)
    assert rows==list(rebuilt.rows)
    assert re.findall(rb'^\*Static\s*\r?\n([^\r\n]+)',raw,re.M|re.I)==[b'0.001, 1., 1e-12, 0.0025']
    assert b'inc=999999' in raw and b'RF2, U2' in raw
    assert not re.search(rb'^\*(?:include|import)\b',raw,re.M|re.I)
    assert b' 2.1e+11, 0.3' in raw
    fd=csvrows(R/b['fd_path']);hist=csvrows(R/result['raw_u2_rf2_step_time_csv'])
    assert len(fd)==len(hist)==440
    u=np.array([float(v['displacement_m']) for v in fd]);f=np.array([float(v['force_n']) for v in fd])
    np.testing.assert_array_equal(u,-np.array([float(v['U2_raw_m']) for v in hist]))
    np.testing.assert_array_equal(f,-np.array([float(v['RF2_raw_n']) for v in hist]))
    features,curve,ex=extract(u,f)
    arrays=read(R/'run/run_055/artifacts/private/feature_arrays.json')
    np.testing.assert_array_equal(curve,arrays['curves']['I06'])
    np.testing.assert_array_equal(features,arrays['features']['I06'])
    assert np.min(np.diff(f))>0 and result['max_saved_peeq']<.9
    save(P/'I06_baseline_audit.json',{'status':'QUALIFIED_WITH_LIMITATIONS','verified_at':now(),'baseline':b,'source_sha256':sha(source),'reproduced_original_material_rows':len(rows),'physical_skeleton_sha256':hashlib.sha256(effective_skeleton(raw)).hexdigest(),'actual_numerics':contract['numerics'],'history_and_FD_sign_verified':True,'raw_points':len(fd),'complete_window':True,'extracted_features_and_grid_match_run055':True,'rp':diag['rp'],'trials_reparsed':trial,'warnings_preserved':result['numerical_review_warnings'],'process_evidence_gap_retained':True,'independent_time_step_qualification':False,'no_new_center_job':True,'limit':'read-only hash and prior extraction evidence recheck; no new ODB extraction or proof of point-level time-step convergence'})
    variants=[]
    for i,p in enumerate(contract['points'],1):
        pid=f'P{i:02d}';suffix=['SYM','SYP','NM','NP'][i-1];job=f'SPIO_R057_{pid}_{suffix}'
        assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',job)
        folder=A/'candidates'/job;folder.mkdir(parents=True,exist_ok=False)
        work=A/'solver'/job;work.mkdir(parents=True,exist_ok=False)
        assert not any(work.iterdir())
        table=generate_hollomon_table(p['sigma_y_mpa'],p['n'],max_plastic_strain=.9,relative_tolerance=.001)
        values=np.asarray(table.rows)
        assert values[0,1]==0 and values[-1,1]==.9
        assert np.all(np.diff(values[:,0])>0) and np.all(np.diff(values[:,1])>0)
        assert values[0,0]==p['sigma_y_mpa']*1e6
        qs=np.unique(np.r_[np.linspace(0,.9,10001),np.geomspace(1e-10,.9,5000),values[:,1]])
        exact=np.array([stress_at_plastic_strain(q,p['sigma_y_mpa'],p['n']) for q in qs])
        linear=np.interp(qs,values[:,1],values[:,0]);error=float(np.max(abs(linear-exact)/exact))
        assert error<=.00100000001 and table.conservative_relative_error_bound<=.001
        newline=b'\r\n' if b'\r\n' in raw else b'\n'
        rows_bytes=newline.join(f'{s:.17g}, {q:.17g}'.encode() for s,q in table.rows)+newline
        newpre=pre
        replacements=[(b'** Job name: Job-1 Model name: Model-1',f'** Job name: {job} Model name: Model-1'.encode()),
            (b'** RUN_030 POINT I06; job=SPIO_R030_I06_L; offline candidate only',f'** RUN_057 POINT {pid}; job={job}; offline preparation only'.encode())]
        oldparam=next(l.strip() for l in pre.splitlines() if l.startswith(b'** sigma_y_MPa='))
        newparam=f'** sigma_y_MPa={p["sigma_y_mpa"]:.17g}; n={p["n"]:.17g}; design_sha256={sha(R/"run/run_056/artifacts/private/prospective_design_contract.json")}'.encode()
        replacements.append((oldparam,newparam))
        for old,new in replacements:
            assert newpre.count(old)==1
            newpre=newpre.replace(old,new,1)
        candidate=newpre+rows_bytes+post
        assert effective_skeleton(candidate)==effective_skeleton(raw)
        a,z,crows=split_plastic(candidate)
        assert z==post and a==newpre and crows==list(table.rows)
        inp=folder/(job+'.inp');inp.write_bytes(candidate)
        (folder/'plastic_rows.inc.txt').write_bytes(rows_bytes)
        with (folder/'plastic_table.csv').open('x',encoding='utf-8',newline='') as stream:
            w=csv.writer(stream);w.writerow(['yield_stress_pa','equivalent_plastic_strain']);w.writerows(table.rows)
        delta=''.join(difflib.unified_diff(raw.decode().splitlines(keepends=True),candidate.decode().splitlines(keepends=True),fromfile='frozen_I06',tofile=job))
        write(folder/'source_difference.patch',delta)
        point={'candidate_id':pid,'design_id':p['design_id'],'job_name':job,'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n'],'x':p['x'],'y':p['y'],'E_pa':210e9,'nu':.3,'material_model':contract['material']['type'],'stress_unit':'Pa','plastic_strain_unit':'dimensionless equivalent plastic strain','max_plastic_strain':.9,'relative_tolerance':.001,'source_inp':rel(source),'source_inp_sha256':sha(source),'source_ODB':b['odb_path'],'source_ODB_sha256':b['odb_sha256'],'generator':'inverse/hollomon.py','generator_sha256':sha(R/'inverse/hollomon.py'),'design_contract':rel(R/'run/run_056/artifacts/private/prospective_design_contract.json'),'design_contract_sha256':sha(R/'run/run_056/artifacts/private/prospective_design_contract.json'),'numerical_contract':'run030-standard-m0025-hollomon-v1','numerics':contract['numerics'],'inp_path':rel(inp),'inp_absolute_path':str(inp),'inp_sha256':sha(inp),'working_dir':rel(work),'working_dir_absolute':str(work),'expected_odb':rel(work/(job+'.odb')),'expected_odb_absolute':str(work/(job+'.odb')),'material_rows':len(table.rows),'table_path':rel(folder/'plastic_table.csv'),'table_sha256':sha(folder/'plastic_table.csv'),'plastic_rows_path':rel(folder/'plastic_rows.inc.txt'),'plastic_rows_sha256':sha(folder/'plastic_rows.inc.txt'),'physical_skeleton_sha256':hashlib.sha256(effective_skeleton(candidate)).hexdigest(),'nonplastic_bytes_identical_except_three_identity_comments':True,'comment_replacements':[{'old':x.decode(),'new':y.decode()} for x,y in replacements],'interpolation_conservative_relative_bound':table.conservative_relative_error_bound,'dense_15000_check_max_relative_error':error,'resources':{'cpus':14,'gpus':0,'run_datacheck':True,'run_full':True,'automatic_retries':0},'queue_id':None,'attempts':0,'execution_authorized':False,'outside_observed_parameter_hull':p['outside_observed_parameter_hull']}
        save(folder/'parameters.json',point)
        point['parameters_path']=rel(folder/'parameters.json');point['parameters_sha256']=sha(folder/'parameters.json')
        variants.append(point)
    assert len(set(p['inp_sha256'] for p in variants))==4
    save(P/'candidate_generation.json',{'version':'run057-material-only-preparation-v1','at':now(),'actor':ss['identity']['agent_id'],'cross_session_CAE_execution_claimed':False,'source':b,'points':variants,'new_FE':0,'queue_writes':0})
    print(json.dumps({'baseline':'QUALIFIED_WITH_LIMITATIONS','candidate_count':4,'table_rows':[v['material_rows'] for v in variants],'hashes':[v['inp_sha256'] for v in variants],'only_material_and_identity_comments_changed':True}))

if __name__=='__main__':main()
