"""MAIN: frozen constitutive comparison and independent axisymmetric quadrature checks."""
from pathlib import Path
import csv,json,hashlib,math,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(r'E:\Projects\SMALL-PUNCH');P=R/'run/run_050/artifacts/private';F=R/'run/run_046/artifacts/private/freeze'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def rows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvsave(p,rs):
 with p.open('x',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)

def quadrature(xy):
    """Full CAX4 2x2 quadrature: signed Jacobian; physical 360deg volume, m^3."""
    out=[]
    for xi,eta in [(-1/math.sqrt(3),-1/math.sqrt(3)),(1/math.sqrt(3),-1/math.sqrt(3)),(1/math.sqrt(3),1/math.sqrt(3)),(-1/math.sqrt(3),1/math.sqrt(3))]:
        N=np.array([(1-xi)*(1-eta),(1+xi)*(1-eta),(1+xi)*(1+eta),(1-xi)*(1+eta)])/4
        dN=np.array([[-(1-eta),-(1-xi)],[(1-eta),-(1+xi)],[(1+eta),(1+xi)],[-(1+eta),(1-xi)]])/4
        jac=xy.T@dN;det=float(np.linalg.det(jac));r,z=N@xy
        assert det>0 and r>=0
        out.append({'r':float(r),'z':float(z),'detJ':det,'volume':float(2*math.pi*r*det)})
    return out

def specimen_mesh(text):
    nodes={};els={};part=False;mode=None
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('**'):continue
        if line.lower().startswith('*part'):
            part='part_specimen' in line.lower();mode=None;continue
        if line.lower().startswith('*end part'):part=False;mode=None;continue
        if not part:continue
        if line.startswith('*'):
            mode='node' if line.lower()=='*node' else 'element' if line.lower().startswith('*element, type=cax4') else None;continue
        a=[s.strip() for s in line.split(',') if s.strip()]
        if mode=='node':nodes[int(a[0])]=[float(a[1]),float(a[2])]
        elif mode=='element':els[int(a[0])]=[int(v) for v in a[1:]]
    assert nodes and els and all(len(e)==4 for e in els.values())
    return nodes,els

def main():
    manifest=read(F/'frozen_manifest.json');checked=[]
    for v in manifest['files']:
        assert sha(R/v['path'])==v['sha256'];checked.append({'path':v['path'],'sha256':v['sha256']})
    scope=read(R/'run/run_049/artifacts/private/analysis.json');p_cond=scope['conditional_tensile_uniform_plastic_limit']
    summary={'frozen_manifest_files_verified':len(checked),'frozen_sources':checked,'conditional_uniaxial_plastic_marker':p_cond,'conditional_marker_basis':'source-confirmed uniform log-total endpoint .10 minus endpoint stress/E210; not a verified universal PEEQ validity limit; retain run048 NOT_EVALUABLE','per_candidate':{},'no_fit_or_new_table':True}
    tables={};true={};samples=[]
    for pid in ['D01','I08']:
        par=read(F/f'{pid}_parameters.json');table=rows(F/f'{pid}_abaqus_yield_stress_plastic_strain.csv');cur=rows(F/f'{pid}_true_total_curve.csv')
        p=np.array([float(v['equivalent_plastic_strain']) for v in table]);s=np.array([float(v['yield_stress_pa']) for v in table]);assert p[0]==0 and np.all(np.diff(p)>0) and np.all(np.diff(s)>0)
        tables[pid]=(p,s);true[pid]=(np.array([float(v['true_total_strain']) for v in cur]),np.array([float(v['true_stress_pa']) for v in cur]))
        summary['per_candidate'][pid]={'sigma_y_mpa':par['sigma_y_mpa'],'n':par['n'],'table_plastic_range':[float(p[0]),float(p[-1])],'table_rows':len(table),'saved_peeq_max':par['max_saved_peeq'],'remaining_table_margin':float(p[-1]-par['max_saved_peeq']),'max_peeq_within_table':bool(par['max_saved_peeq']<p[-1]),'physics':'stored isotropic J2 equivalent-plastic-strain index is not a measured tensile log-total strain; table coverage does not establish physical validation'}
    for pp in [0,.01,.05,p_cond,.1,.2,.3,.5,.6114587783813477,.6537371873855591,.9]:
        sd=float(np.interp(pp,*tables['D01']))/1e6;si=float(np.interp(pp,*tables['I08']))/1e6
        samples.append({'plastic_index':pp,'D01_frozen_table_stress_MPa':sd,'I08_frozen_table_stress_MPa':si,'I08_minus_D01_MPa':si-sd,'difference_over_D01':(si-sd)/sd,'source':'frozen deployed table linear interpolation, no fit','experimental_status':'no claim of a universal validated strain domain'})
    csvsave(P/'frozen_table_scope_samples.csv',samples);save(P/'frozen_material_scope.json',summary)
    fig,ax=plt.subplots(1,2,figsize=(12,4.6))
    for pid in ['D01','I08']:
        ep,ss=true[pid];ax[0].plot(ep,ss/1e6,label=pid)
        p,s=tables[pid];ax[1].plot(p,s/1e6,'o-',ms=2,label=f'{pid} frozen table')
        v=summary['per_candidate'][pid]['saved_peeq_max'];ax[1].axvline(v,linestyle=':',label=f'{pid} max saved PEEQ={v:.3f}')
    ax[0].axvspan(0,.1,color='grey',alpha=.15,label='source-confirmed uniform total-strain extent')
    ax[0].set(xlim=(0,.9),xlabel='Predicted true total uniaxial strain',ylabel='True stress (MPa)',title='Frozen predictions; .10 is not PEEQ=.10')
    ax[1].axvline(p_cond,color='black',ls='--',label='conditional uniaxial p marker, not universal cutoff')
    ax[1].set(xlim=(0,.9),xlabel='Equivalent plastic strain table coordinate',ylabel='Yield stress (MPa)',title='Stored mathematical coverage vs FE demand')
    for a in ax:a.legend(fontsize=7);a.grid(alpha=.25)
    fig.tight_layout();fig.savefig(P/'frozen_material_range_comparison.png',dpi=170);plt.close(fig)
    nodes,els=specimen_mesh((R/'run/run_043/artifacts/candidates/SPIO_R043_V_D01_M00125/SPIO_R043_V_D01_M00125.inp').read_text())
    integrated=sum(v['volume'] for e in els.values() for v in quadrature(np.array([nodes[k] for k in e])))
    exact=math.pi*.005**2*.0005
    rectangle=np.array([[.001,0],[.005,0],[.005,.0005],[.001,.0005]])
    annular=sum(v['volume'] for v in quadrature(rectangle));annular_exact=math.pi*(.005**2-.001**2)*.0005
    scaled=rectangle*np.array([1.02,.98]);vol2=sum(v['volume'] for v in quadrature(scaled));expected2=annular*1.02**2*.98
    checks={'annular_rectangle_axisymmetric_volume':abs(annular/annular_exact-1)<1e-12,'uniform_deformation_volume_scaling':abs(vol2/expected2-1)<1e-12,'specimen_reference_matches_physical_disc':abs(integrated/exact-1)<1e-6,'not_cross_section_area':not math.isclose(integrated,.005*.0005,rel_tol=.01)}
    assert all(checks.values())
    save(P/'main_quadrature_verification.json',{'checks':checks,'nodes':len(nodes),'elements':len(els),'element_type':'CAX4','full_integration_points_per_element':4,'integrated_reference_volume_m3':integrated,'analytic_disc_volume_m3':exact,'relative_volume_error':integrated/exact-1,'formula':'sum 2*pi*r*det(J)*w_xi*w_eta; positive-J and r>=0 asserted','scope':'independent MAIN reference geometry and affine-volume verification only; actual ODB IP mapping must be separately checked'})
    print(json.dumps({'frozen_files_checked':len(checked),'actual_elements':len(els),'reference_volume_m3':integrated,'checks':checks,'sample_stresses':samples[4:7]}))
if __name__=='__main__':main()
