"""SPT-only D01/I08 residual and constitutive identifiability diagnostics."""
from __future__ import annotations
import csv,hashlib,json,math,sys
from datetime import datetime
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(r'E:\Projects\SMALL-PUNCH');RUN=ROOT/'run/run_043';OUT=RUN/'artifacts/private/main'
sys.path.insert(0,str(ROOT))
from inverse.hollomon import stress_at_plastic_strain,stress_from_total_strain

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_csv(p,data,keys):
    with Path(p).open('w',encoding='utf-8',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=keys);w.writeheader()
        for r in data:w.writerow({k:r.get(k) for k in keys})
def plastic_table(path):
    lines=Path(path).read_text(encoding='utf-8').splitlines();i=next(i for i,s in enumerate(lines) if s.strip().lower()=='*plastic')
    vals=[]
    for s in lines[i+1:]:
        if s.lstrip().startswith('*'):break
        if s.strip():vals.append(tuple(float(v) for v in s.split(',')))
    return np.array(vals)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    audit=read(RUN/'artifacts/private/baseline_audit.json');pair=audit['records']
    contract=read(RUN/'artifacts/comparison_contract.json')
    target=rows(ROOT/contract['target_path'])[:241]
    assert sha(ROOT/contract['target_path'])==contract['target_sha256']
    u=np.array([float(r['displacement_m']) for r in target]);exp=np.array([float(r['force_n']) for r in target]);ref=1428.9
    assert np.max(np.abs(u-np.array(contract['grid_m'])))==0
    curves={};residuals={};tables={};results={};rawcounts={}
    for p in pair:
        pid=p['point_id'];assert sha(ROOT/p['source_inp'])==p['source_inp_sha256']
        assert sha(ROOT/p['fd_path'])==p['fd_sha256']
        rr=rows(ROOT/p['fd_path']);ux=np.array([float(r['displacement_m']) for r in rr]);ff=np.array([float(r['force_n']) for r in rr])
        assert np.all(np.diff(ux)>0) and ux[0]<=u[0] and ux[-1]>=u[-1]
        curves[pid]=np.interp(u,ux,ff);residuals[pid]=curves[pid]-exp;rawcounts[pid]=len(ux)
        loss=float(np.mean((residuals[pid]/ref)**2));assert abs(loss-p['loss'])<1e-12
        results[pid]={'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n'],'yield_true_total_strain':p['sigma_y_mpa']/210000,
                      'loss':loss,'rmse_n':float(np.sqrt(np.mean(residuals[pid]**2))),
                      'bias_n':float(np.mean(residuals[pid])),'max_abs_residual_n':float(np.max(np.abs(residuals[pid]))),
                      'raw_fd_points':len(ux),'max_saved_peeq':p['max_saved_peeq'],'cutback':p['cutback']}
        tables[pid]=plastic_table(ROOT/p['source_inp'])
        assert tables[pid][0,1]==0 and tables[pid][-1,1]==.9 and np.all(np.diff(tables[pid][:,1])>0)
    delta=curves['I08']-curves['D01'];idx=int(np.argmax(np.abs(delta)))
    pairfd={'definition':'F_I08-F_D01 on frozen experiment grid','rmse_n':float(np.sqrt(np.mean(delta**2))),
            'max_abs_difference_n':float(abs(delta[idx])),'max_abs_at_mm':float(u[idx]*1000),
            'normalized_rmse_by_1428p9':float(np.sqrt(np.mean(delta**2))/ref)}
    bins=[(0,.0003),(.0003,.0006),(.0006,.0009),(.0009,.0012)]
    intervals=[]
    for i,(lo,hi) in enumerate(bins):
        mask=(u>=lo-1e-15)&((u<hi-1e-15) if i<3 else (u<=hi+1e-15))
        for pid in ['D01','I08']:
            r=residuals[pid][mask]
            intervals.append({'point_id':pid,'lower_mm':lo*1000,'upper_mm':hi*1000,'points':int(mask.sum()),
                              'bias_n':float(np.mean(r)),'rmse_n':float(np.sqrt(np.mean(r*r))),
                              'max_abs_residual_n':float(np.max(np.abs(r))),
                              'contribution_to_full_Loss':float(np.sum((r/ref)**2)/241),
                              'fraction_of_full_Loss':float(np.sum(r*r)/np.sum(residuals[pid]**2)),
                              'pair_fd_rmse_n':float(np.sqrt(np.mean(delta[mask]**2)))})
    for pid in ['D01','I08']:
        assert abs(sum(r['contribution_to_full_Loss'] for r in intervals if r['point_id']==pid)-results[pid]['loss'])<1e-12
    common_p=min(p['max_saved_peeq'] for p in pair);union_p=max(p['max_saved_peeq'] for p in pair)
    sample_eps=[0,.0005,pair[0]['sigma_y_mpa']/210000,.001,pair[1]['sigma_y_mpa']/210000,.002,.005,.01,.02,.05,.1,.2,.4]
    true_samples=[]
    for e in sorted(set(sample_eps)):
        stresses=[stress_from_total_strain(e,p['sigma_y_mpa'],p['n'])/1e6 for p in pair]
        true_samples.append({'true_total_strain':e,'D01_true_stress_mpa':stresses[0],'I08_true_stress_mpa':stresses[1],
                             'I08_minus_D01_mpa':stresses[1]-stresses[0],
                             'relative_difference_to_D01':(stresses[1]-stresses[0])/stresses[0] if stresses[0]>0 else None})
    plastic_samples=[]
    for pp in sorted(set([0,.002,.01,.05,.1,.2,.4,common_p,union_p,.9])):
        linear=[float(np.interp(pp,tables[p['point_id']][:,1],tables[p['point_id']][:,0]))/1e6 for p in pair]
        analytic=[stress_at_plastic_strain(pp,p['sigma_y_mpa'],p['n'])/1e6 for p in pair]
        plastic_samples.append({'equivalent_plastic_strain':pp,'D01_abaqus_stress_mpa':linear[0],'I08_abaqus_stress_mpa':linear[1],
                                'D01_analytic_stress_mpa':analytic[0],'I08_analytic_stress_mpa':analytic[1],
                                'I08_minus_D01_table_mpa':linear[1]-linear[0],
                                'within_both_saved_peeq_envelopes':pp<=common_p,'within_either_saved_peeq_envelope':pp<=union_p})
    pgrid=np.linspace(0,common_p,3001)
    stress_p=[np.interp(pgrid,tables[p['point_id']][:,1],tables[p['point_id']][:,0])/1e6 for p in pair]
    pd=stress_p[1]-stress_p[0];pi=int(np.argmax(np.abs(pd)))
    extrapolation_scope={'common_saved_peeq_envelope':[0,common_p],'union_saved_peeq_envelope':[0,union_p],
                         'material_table_coverage':[0,.9],'max_table_stress_difference_in_common_envelope_mpa':float(abs(pd[pi])),
                         'max_difference_at_plastic_strain':float(pgrid[pi]),
                         'limitation':'Saved maximum PEEQ is a multiaxial scalar envelope, not a uniaxial strain history or volume-weighted distribution; rejected/unsaved trial peaks unknown'}
    # Union of actual reviewed FE values, with no surrogate or hidden validation data.
    main42=read(ROOT/'run/run_042/artifacts/private/main/main_analysis.json')
    base=read(ROOT/'run/run_040/artifacts/private/initial_dataset.json')
    all_valid=[{'point_id':r['point_id'],'sigma_y_mpa':r['sigma_y_mpa'],'n':r['n'],'x':r['x'],'y':r['y'],'loss':r['loss'],'origin':'DOE'} for r in base['valid']]
    all_valid.extend({'point_id':r['candidate_id'],'sigma_y_mpa':r['sigma_y_mpa'],'n':r['n'],'x':r['x'],'y':r['y'],'loss':r['loss'],'origin':r['algorithm']} for r in main42['rows'] if r['loss'] is not None)
    assert len(all_valid)==24 and len({r['point_id'] for r in all_valid})==24
    best=min(r['loss'] for r in all_valid);sets={}
    for name,threshold in [('two_times_best',2*best),('absolute_0p002',.002),('absolute_0p01',.01)]:
        rr=[r for r in all_valid if r['loss']<=threshold]
        sets[name]={'threshold':threshold,'point_ids':[r['point_id'] for r in rr],
                    'sigma_y_range_mpa':[min(r['sigma_y_mpa'] for r in rr),max(r['sigma_y_mpa'] for r in rr)],
                    'n_range':[min(r['n'] for r in rr),max(r['n'] for r in rr)]}
    finding={'version':'run043-low-loss-comparison-v1','at':datetime.now().astimezone().isoformat(),'baseline':results,
             'loss_gap_i08_minus_d01':results['I08']['loss']-results['D01']['loss'],'pair_fd':pairfd,'residual_intervals':intervals,
             'true_total_constitutive_samples':true_samples,'abaqus_plastic_samples':plastic_samples,'strain_scope':extrapolation_scope,
             'sampled_low_loss_sets':sets,'reviewed_valid_points':24,'parameter_boundary_note':'D01 sigma_y only 2.30863354 MPa above retained lower bound 150 MPa',
             'scientific_scope':'Multiple competing observed candidates; continuous valley, unique parameters and confidence intervals not established; no tensile data accessed'}
    save(OUT/'analysis.json',finding)
    write_csv(OUT/'residual_intervals.csv',intervals,list(intervals[0]))
    write_csv(OUT/'predicted_true_total_samples.csv',true_samples,list(true_samples[0]))
    write_csv(OUT/'abaqus_plastic_samples.csv',plastic_samples,list(plastic_samples[0]))
    dense=[]
    for p in pair:
        for e in np.linspace(0,union_p+.006,2001):
            s=stress_from_total_strain(float(e),p['sigma_y_mpa'],p['n'])
            dense.append({'point_id':p['point_id'],'true_total_strain':float(e),'predicted_true_stress_pa':s,
                          'uniaxial_plastic_strain_under_candidate_law':max(0,float(e)-s/210e9)})
        t=tables[p['point_id']]
        write_csv(OUT/f"{p['point_id']}_abaqus_table.csv",[{'stress_pa':float(s),'equivalent_plastic_strain':float(pp)} for s,pp in t],['stress_pa','equivalent_plastic_strain'])
    write_csv(OUT/'predicted_constitutive_dense.csv',dense,['point_id','true_total_strain','predicted_true_stress_pa','uniaxial_plastic_strain_under_candidate_law'])
    save(OUT/'constitutive_provenance.json',{'generator_path':'inverse/hollomon.py','generator_sha256':sha(ROOT/'inverse/hollomon.py'),
             'source_inputs':[{'point_id':p['point_id'],'path':p['source_inp'],'sha256':p['source_inp_sha256'],'sigma_y_mpa':p['sigma_y_mpa'],'n':p['n']} for p in pair],
             'candidate_interpretation':'true-total Hollomon candidate, E=210GPa, nu=0.3; no tensile experiment used',
             'status':'EXPLORATORY_CANDIDATE_SET_NOT_FINAL_INVERSION','strain_scope':extrapolation_scope})
    write_csv(OUT/'frozen_grid_comparison.csv',[{'displacement_m':float(a),'experiment_force_n':float(b),'D01_force_n':float(c),'I08_force_n':float(d),
               'I08_minus_D01_n':float(d-c),'D01_residual_n':float(c-b),'I08_residual_n':float(d-b)} for a,b,c,d in zip(u,exp,curves['D01'],curves['I08'])],
               ['displacement_m','experiment_force_n','D01_force_n','I08_force_n','I08_minus_D01_n','D01_residual_n','I08_residual_n'])
    fig,axes=plt.subplots(3,1,figsize=(10,10),layout='constrained',sharex=True)
    axes[0].plot(u*1000,exp,'k',lw=2,label='SPT experiment')
    for pid in ['D01','I08']:axes[0].plot(u*1000,curves[pid],label=f"{pid}, Loss={results[pid]['loss']:.6g}")
    axes[0].set(ylabel='Force (N)',title='Actual FE curves, frozen 241-point comparison');axes[0].legend()
    axes[1].plot(u*1000,delta,color='purple');axes[1].axhline(0,color='black',lw=.7);axes[1].set(ylabel='F_I08 - F_D01 (N)')
    for pid in ['D01','I08']:axes[2].plot(u*1000,residuals[pid],label=pid)
    axes[2].axhline(0,color='black',lw=.7);axes[2].set(xlabel='Punch displacement (mm)',ylabel='FE minus experiment (N)');axes[2].legend()
    fig.savefig(OUT/'fd_differences_residuals.png',dpi=170);plt.close(fig)
    # Analytic true-total law at yield, moderate strain and a plastic-envelope-derived view.
    extent=union_p+.006
    fig,axes=plt.subplots(1,3,figsize=(16,5),layout='constrained')
    for ax,limit,title in zip(axes,[.003,.2,extent],['Yield neighborhood','Moderate true total strain','Constitutive range spanning saved PEEQ envelope']):
        ee=np.linspace(0,limit,1001)
        for p in pair:
            ss=np.array([stress_from_total_strain(float(e),p['sigma_y_mpa'],p['n'])/1e6 for e in ee])
            ax.plot(ee,ss,label=p['point_id'])
        ax.set(xlabel='Predicted true total strain',ylabel='Predicted true stress (MPa)',title=title);ax.legend()
    fig.suptitle('SPT-derived candidate laws; no tensile experiment used; PEEQ is not uniaxial total strain')
    fig.savefig(OUT/'predicted_true_total_curves.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    ax.axvspan(0,common_p,color='green',alpha=.07,label='Common saved PEEQ envelope')
    for p in pair:
        pid=p['point_id'];t=tables[pid]
        ax.plot(t[:,1],t[:,0]/1e6,marker='.',markersize=3,label=f'{pid}: actual Abaqus table')
        ax.axvline(p['max_saved_peeq'],ls='--',alpha=.6)
    ax.set(xlabel='Equivalent plastic strain',ylabel='Abaqus table true stress (MPa)',title='Frozen piecewise-linear plastic tables; dashed lines = saved PEEQ maxima');ax.legend()
    fig.savefig(OUT/'abaqus_plastic_curves.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax in axes:
        m=ax.scatter([r['sigma_y_mpa'] for r in all_valid],[r['n'] for r in all_valid],c=[math.log10(r['loss']) for r in all_valid],cmap='viridis',s=55,edgecolors='black',vmin=-4,vmax=1.2)
        for p in pair:ax.scatter(p['sigma_y_mpa'],p['n'],s=180,facecolors='none',edgecolors='red');ax.annotate(p['point_id'],(p['sigma_y_mpa'],p['n']),xytext=(5,5),textcoords='offset points')
        ax.axvline(150,color='red',ls='--',lw=.7);ax.set(xlabel='sigma_y (MPa)',ylabel='n')
    axes[0].set(xscale='log',title='24 actual reviewed FE points')
    axes[1].set(xlim=(145,410),ylim=(.05,.3),title='Low-Loss region, no interpolated valley assumed')
    fig.colorbar(m,ax=axes,label='log10(frozen Loss)');fig.savefig(OUT/'parameter_compensation_points.png',dpi=170);plt.close(fig)
    print(json.dumps({'baseline':results,'pair_fd':pairfd,'loss_gap':finding['loss_gap_i08_minus_d01'],'samples_true':true_samples,'plastic':plastic_samples,'low_loss_sets':sets},ensure_ascii=False))

if __name__=='__main__':main()
