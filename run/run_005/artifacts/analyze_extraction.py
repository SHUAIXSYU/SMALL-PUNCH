"""Analyze genuine read-only ODB exports using the selected research Python."""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
ART=ROOT/'run/run_005/artifacts'
PRIVATE=ART/'private'
os.environ['MPLCONFIGDIR']=str(PRIVATE/'mplconfig')
os.environ['MPLBACKEND']='Agg'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def read(name): return json.loads((PRIVATE/name).read_text(encoding='utf-8'))
def save(name,obj): (ART/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def csv_write(name,header,rows):
    with (ART/name).open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f); writer.writerow(header); writer.writerows(rows)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    expected=r'D:\XianLab\envs\conda\torch-gpu\python.exe'
    assert os.path.normcase(sys.executable)==os.path.normcase(expected)
    d=read('odb_extract_attempt03.json'); comparison=read('odb_temtry_comparison.json')
    assert d['status']=='PASS' and d['odb']['isReadOnly'] is True
    ib=read('inp_blocks.json'); model=read('inp_model.json'); logs=read('log_analysis.json')
    step_name='Step_Punch_Displacement'; region='Node ASM_SPT.1'
    step=d['steps'][step_name]; history=step['history_regions'][region]['outputs']
    # Prove that the history node belongs to the input's analytical punch rigid body.
    rigid=next(b for b in ib if b['keyword']=='rigid body' and b['instance']=='ASM_SPT')
    assert rigid['options']['analytical surface']=='surf_punch_contact'
    ref=next(b for b in ib if b['keyword']=='nset' and b['instance']=='ASM_SPT' and b['options']['nset']==rigid['options']['ref node'])
    punch=next(b for b in ib if b['keyword']=='nset' and b['instance']=='ASM_SPT' and b['options']['nset']=='set_punch_rp')
    assert ref['rows'][0]['text'].strip(' ,')==punch['rows'][0]['text'].strip(' ,')=='1'
    assert [v['label'] for v in d['instances']['ASM_SPT']['node_sets']['SET_PUNCH_RP']]==[1]
    bc=[r['text'] for b in ib if b['keyword']=='boundary' for r in b['rows']]
    assert 'ASM_SPT.set_punch_rp, 2, 2, -0.0012' in bc
    assert not any(b['keyword']=='transform' for b in ib)
    u=np.array(history['U2']['data'],dtype=float); rf=np.array(history['RF2']['data'],dtype=float)
    assert np.isfinite(u).all() and np.isfinite(rf).all()
    assert np.array_equal(u[:,0],rf[:,0]) and np.all(np.diff(u[:,0])>0)
    t=u[:,0]; displacement=-u[:,1]; force=-rf[:,1]
    assert u[0,1]==0 and np.all(u[:,1]<=0) and np.all(rf[:,1]<=0)
    csv_write('punch_rp_history_raw.csv',['step','history_region','step_time','U2_model_length','RF2_model_force'],
              [[step_name,region,float(a),float(b),float(c)] for a,b,c in zip(t,u[:,1],rf[:,1])])
    csv_write('punch_force_displacement.csv',['step','step_time','displacement_model_length','force_model_force'],
              [[step_name,float(a),float(b),float(c)] for a,b,c in zip(t,displacement,force)])
    energies=step['history_regions']['Assembly ASSEMBLY']['outputs']
    energy={k:np.array(v['data'],dtype=float) for k,v in energies.items()}
    assert all(np.array_equal(v[:,0],t) for v in energy.values())
    csv_write('energy_history.csv',['step_time']+list(energy),[[float(t[i])]+[float(v[i,1]) for v in energy.values()] for i in range(len(t))])
    frames=step['frames']; assert len(frames)==len(t)
    field_du=[]; field_drf=[]; rp_u1=[]; rp_ur=[]; rp_rm=[]; axial_residual=[]; pressure=[]; openings=[]
    for index,f in enumerate(frames):
        assert abs(f['frame_value']-t[index])<1e-7
        p=f['rp_fields']['ASM_SPT.1']
        field_du.append(p['U']['data'][1]-u[index,1]); field_drf.append(p['RF']['data'][1]-rf[index,1])
        rp_u1.append(p['U']['data'][0]); rp_ur.append(p['UR3']['data'][0]); rp_rm.append(p['RM3']['data'][0])
        axial_residual.append(sum(v[1] for v in f['resultant_rf'].values()))
        pressure.append(next(v['maximum'][0] for k,v in f['fields'].items() if k.startswith('CPRESS')))
        openings.append(next(v for k,v in f['fields'].items() if k.startswith('COPEN')))
    csv_write('field_diagnostics.csv',['step_time','RP_U1','RP_UR3','RP_RM3','axial_RF_sum','axis_max_abs_U1','CPRESS_max','COPEN_valid_min','COPEN_valid_max','COPEN_excluded_huge_count'],
        [[float(t[i]),rp_u1[i],rp_ur[i],rp_rm[i],axial_residual[i],f['axis_u1_max'],pressure[i],
          (openings[i]['valid_minimum'] or [None])[0],(openings[i]['valid_maximum'] or [None])[0],openings[i]['excluded_huge_or_nonfinite_count']] for i,f in enumerate(frames)])
    inp_nodes={int(v[0]):[float(x) for x in v[1:]] for b in ib if b['keyword']=='node' and b['part']=='part_specimen' for r in b['rows'] for v in [[s.strip() for s in r['text'].split(',') if s.strip()]]}
    inp_elements={int(v[0]):[int(x) for x in v[1:]] for b in ib if b['keyword']=='element' for r in b['rows'] for v in [[s.strip() for s in r['text'].split(',') if s.strip()]]}
    specimen=d['instances']['ASM_SPT-1']
    coordinate_error=max(abs(a-b) for n in specimen['nodes'] for a,b in zip(n['coordinates'],inp_nodes[n['label']]))
    topology_match=all(e['connectivity']==inp_elements[e['label']] and e['type']=='CAX4' for e in specimen['elements'])
    assert topology_match and coordinate_error<1e-9
    positive=[i for i,p in enumerate(pressure) if p>0]
    delta=np.diff(force); max_inc=int(np.argmax(delta)); max_drop=int(np.argmin(delta))
    work=float(np.trapezoid(force,displacement)); last={k:float(v[-1,1]) for k,v in energy.items()}
    compare_history=comparison['steps'][step_name]['history_regions'][region]['outputs']
    compare_u=np.array(compare_history['U2']['data']); compare_rf=np.array(compare_history['RF2']['data'])
    times_equal=np.array_equal(t,compare_u[:,0]) and np.array_equal(t,compare_rf[:,0])
    comparison_result=dict(independent_source_group='TempTry; never merged into Sanity curve',
        input_sha256_equal=digest(ROOT/'CAE/Models/Sanity/Job-1.inp')==digest(ROOT/'CAE/Models/TempTry/Job-1.inp'),
        odb_sha256_equal=digest(ROOT/'CAE/Models/Sanity/Job-1.odb')==digest(ROOT/'CAE/Models/TempTry/Job-1.odb'),
        status=comparison['diagnostic_data']['jobStatus'],sanity_created=d['job_data']['creationTime'],other_created=comparison['job_data']['creationTime'],
        times_exactly_equal=times_equal,max_U2_difference=float(np.max(np.abs(u[:,1]-compare_u[:,1]))) if times_equal else None,
        max_RF2_difference=float(np.max(np.abs(rf[:,1]-compare_rf[:,1]))) if times_equal else None,
        energies_exactly_equal=all(energies[k]['data']==comparison['steps'][step_name]['history_regions']['Assembly ASSEMBLY']['outputs'][k]['data'] for k in energies),
        limit='Historical same-input agreement only; no newly controlled rerun, no CAE-to-INP regeneration or mesh/material validity proof.')
    flagged=[]
    for w in logs['warnings']:
        if w['text'].startswith(('***WARNING: THE SYSTEM MATRIX','***WARNING: EXCESSIVE DISTORTION')):
            m=re.search(r'INCREMENT\s+(\d+).*ATTEMPT NUMBER\s+(\d+)',w['context']['text'])
            inc,attempt=map(int,m.groups())
            match=next(a for a in logs['sta_attempts'] if a['increment']==inc and int(a['attempt'].strip('U'))==attempt)
            flagged.append(dict(msg_line=w['line'],increment=inc,attempt=attempt,sta_unsuccessful='U' in match['attempt'],prior_accepted_step_time=match['step_time'],warning=w['text']))
    stats=dict(observed_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        status='WARNING',extraction_status='PASS',selected_step=step_name,selected_history_region=region,
        samples=len(t),frame_count=len(frames),step_time_period=step['attributes']['timePeriod'],step_start_total_time=step['attributes']['totalTime'],
        time_range=[float(t[0]),float(t[-1])],raw_U2_range=[float(u[:,1].min()),float(u[:,1].max())],raw_RF2_range=[float(rf[:,1].min()),float(rf[:,1].max())],
        displacement_end=float(displacement[-1]),force_end=float(force[-1]),peak_force=float(force.max()),
        sign_convention='Downward-positive punch displacement = -U2; downward applied compressive force = -RF2. No absolute value, no baseline shift, no 2*pi factor.',
        units='Model length/force/time units; no explicit physical unit declaration found. m-N-Pa interpretation plausible but NOT VERIFIED.',
        interpolation='None: U2/RF2/energy time arrays exactly identical. Fields checked by frame order with time tolerance 1e-7 for single precision history.',
        history_field_U2_max_error=max(abs(v) for v in field_du),history_field_RF2_max_error=max(abs(v) for v in field_drf),
        linear_loading_max_error=float(np.max(np.abs(u[:,1]+.0012*t))), displacement_monotonic=bool(np.all(np.diff(displacement)>0)),
        negative_force_increments=int(np.sum(delta<0)),largest_force_increment=dict(value=float(delta[max_inc]),times=[float(t[max_inc]),float(t[max_inc+1])],displacement_increment=float(displacement[max_inc+1]-displacement[max_inc])),
        minimum_force_increment=dict(value=float(delta[max_drop]),times=[float(t[max_drop]),float(t[max_drop+1])]),
        RP_U1_max_abs=max(abs(v) for v in rp_u1),RP_UR3_max_abs=max(abs(v) for v in rp_ur),RP_RM3_final=rp_rm[-1],RP_RF1_final=frames[-1]['rp_fields']['ASM_SPT.1']['RF']['data'][0],
        axial_force_balance_max_abs=max(abs(v) for v in axial_residual),axial_force_balance_max_over_peak=max(abs(v) for v in axial_residual)/float(force.max()),
        axis_U1_max_abs=max(f['axis_u1_max'] for f in frames),axis_radial_bc_present=False,
        first_positive_pressure_time=float(t[positive[0]]) if positive else None,first_positive_pressure_value=pressure[positive[0]] if positive else None,
        CPRESS_final_max=pressure[-1],COPEN_final= openings[-1],PEEQ_final_max=frames[-1]['fields']['PEEQ']['maximum'][0],
        energy_final=last,RP_work_trapezoid=work,RP_work_vs_ALLWK_abs_error=abs(work-last['ALLWK']),
        ETOTAL_max_abs_over_final_ALLWK=float(np.max(np.abs(energy['ETOTAL'][:,1]))/abs(last['ALLWK'])),
        incomplete_energy_residual=last['ALLIE']+last['ALLFD']+last['ALLSD']-last['ALLWK'],
        full_energy_reconstruction='NOT VERIFIED: ALLCCE/ALLCCDW and other full-balance terms absent; partial sum is not ETOTAL.',
        inp_odb_topology_match=topology_match,inp_odb_coordinate_max_error=coordinate_error,
        historical_comparison=comparison_result,warning_counts=logs['warning_counts'],unsuccessful_attempts=logs['unsuccessful_attempts'],flagged_attempts=flagged,
        assembly_node_sets=list(d['assembly_node_sets']),assembly_element_sets=list(d['assembly_element_sets']),
        field_variables=list(frames[-1]['fields']),history_variables={k:list(v['outputs']) for k,v in step['history_regions'].items()})
    slopes=np.diff(force)/np.diff(displacement)
    stats['force_curve_slope_review']=dict(method='Adjacent secant slope dF/dd; descriptive only, no acceptance threshold or smoothing',
        median=float(np.median(slopes)),maximum=float(slopes.max()),highest_five=[dict(index=int(i),time_interval=[float(t[i]),float(t[i+1])],
        displacement_interval=[float(displacement[i]),float(displacement[i+1])],force_increment=float(force[i+1]-force[i]),slope=float(slopes[i])) for i in np.argsort(slopes)[-5:][::-1]])
    save('numerical_sanity.json',stats)
    save('extraction_metadata.json',{k:stats[k] for k in ['selected_step','selected_history_region','samples','sign_convention','units','interpolation','history_field_U2_max_error','history_field_RF2_max_error']})
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2,'savefig.dpi':180})
    for filename,x,y,xlabel,ylabel,title in [
        ('punch_u2_time.png',t,u[:,1],'Step time [model time unit]','Raw U2 [model length unit]','Punch RP displacement | ASM_SPT.1'),
        ('punch_rf2_time.png',t,rf[:,1],'Step time [model time unit]','Raw RF2 [model force unit]','Punch RP reaction force | ASM_SPT.1'),
        ('force_displacement.png',displacement,force,'Punch displacement [model length unit]','Compressive force [model force unit]','Sanity Job-1 | genuine ODB history')]:
        fig,ax=plt.subplots(figsize=(8,5)); ax.plot(x,y,color='#176A8A',lw=2)
        ax.scatter(x[::10],y[::10],color='#176A8A',s=12)
        ax.set(xlabel=xlabel,ylabel=ylabel,title=title)
        fig.text(.5,.015,'181 original samples | no interpolation | no 2pi scaling | physical unit system unconfirmed',ha='center',fontsize=8,color='#555555')
        fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(ART/filename); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for k in ['ALLWK','ALLIE','ALLFD']: axes[0].plot(t,energy[k][:,1],label=k)
    axes[0].set(xlabel='Step time [model time unit]',ylabel='Energy [model energy unit]',title='Available energy history');axes[0].legend()
    axes[1].plot(t,energy['ETOTAL'][:,1],color='#AD5A23',label='Stored ETOTAL');axes[1].set(xlabel='Step time [model time unit]',ylabel='Energy [model energy unit]',title='Stored total energy balance')
    fig.tight_layout();fig.savefig(ART/'energy_diagnostics.png');plt.close(fig)
    # Show geometry actually resolved from input connectivity, not journal masks.
    fig,ax=plt.subplots(figsize=(10,3.5))
    for e in specimen['elements']:
        coords=np.array([inp_nodes[n] for n in e['connectivity']+[e['connectivity'][0]]]);ax.plot(coords[:,0],coords[:,1],color='#BCC7CF',lw=.4)
    for name,color,label in [('surf_specimen_top','#176A8A','Contact secondary surface'),('surf_specimen_clamped_top','#B84940','Clamped rim'),('surf_specimen_clamped_bot','#B84940',None)]:
        for j,s in enumerate(model['surfaces'][name]):
            xy=np.array(s['coordinates']);ax.plot(xy[:,0],xy[:,1],color=color,lw=2,label=label if j==0 else None)
    ax.set(xlabel='r [model length unit]',ylabel='z [model length unit]',title='Resolved INP mesh / surfaces (undeformed)');ax.set_aspect('equal');ax.legend(loc='lower center',bbox_to_anchor=(.5,1.02),ncol=2,fontsize=8)
    ax.set_title('Resolved INP mesh / surfaces (undeformed)',pad=42)
    fig.tight_layout();fig.savefig(ART/'input_geometry_audit.png');plt.close(fig)
    print(json.dumps({k:v for k,v in stats.items() if k not in ['field_variables','history_variables','COPEN_final','flagged_attempts']},indent=2))

if __name__=='__main__': main()
