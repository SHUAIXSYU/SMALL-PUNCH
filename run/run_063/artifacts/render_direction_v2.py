"""Layout-only visual QA addendum; original registered figure/evidence remain unchanged."""
from common63 import *
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from agenthub_sp_invopt.hub import Hub

def main():
 d=read(P/'verified_local_data.json');directions=read(P/'direction_analysis.json');v=read(P/'view_SVD_comparison.json')['views']['full241'];h=.025
 fig,ax=plt.subplots(1,2,figsize=(12,6));fig.subplots_adjust(left=.075,right=.97,bottom=.25,top=.89,wspace=.31)
 for rec,color in zip(d['records'],['k','tab:blue','tab:blue','tab:orange','tab:orange']):
  q=np.array(rec['coordinate'])-np.array(directions['center_xy']);ax[0].scatter(*q,color=color,zorder=4);ax[0].annotate(rec['sample_id'],q,xytext=(4,5),textcoords='offset points',fontsize=9)
 ax[0].plot([h,0,-h,0,h],[0,h,0,-h,0],'k:',label='Convex hull: actual axis FE samples')
 for vec,label,color in [(directions['weak_xy'],'Weak direction: linearized prediction','tab:red'),(directions['strong_xy'],'Strong direction: linearized prediction','tab:green')]:
  vec=np.array(vec);ax[0].arrow(0,0,*(h*vec),color=color,width=.0003,length_includes_head=True,label=label)
  for sign in [-1,1]:ax[0].scatter(*(sign*h*vec),facecolors='none',edgecolors=color,s=65)
 ax[0].set(xlim=(-.032,.032),ylim=(-.032,.032),xlabel='Normalized delta x (log yield stress)',ylabel='Normalized delta y (n)',title='Actual FE versus conceptual mixed directions',aspect='equal')
 xx,yy=np.meshgrid(np.linspace(-.03,.03,201),np.linspace(-.03,.03,201));J=np.array(v['J']);G=J.T@J;z=1428.9*np.sqrt(G[0,0]*xx**2+2*G[0,1]*xx*yy+G[1,1]*yy**2)
 c=ax[1].contour(xx,yy,z,levels=[.4326779144080392,1.,3.092632613282926,10.,20.]);ax[1].clabel(c,inline=True,fmt='%.2g N',fontsize=8);ax[1].set(xlabel='Normalized delta x',ylabel='Normalized delta y',title='Equal predicted response RMS; NOT confidence',aspect='equal')
 for a in ax:a.grid(alpha=.2);a.tick_params(labelsize=8);a.set_title(a.get_title(),fontsize=10,pad=12)
 handles,labels=ax[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.025),ncol=3,fontsize=8,frameon=False)
 output=P/'parameter_compensation_local_v2.png';fig.savefig(output,dpi=180);plt.close(fig)
 add={'at':now(),'scope':'layout-only visual QA; restore title/legend margins, no numerical or scientific change','original_figure_path':rel(P/'parameter_compensation_local.png'),'original_figure_sha256':sha(P/'parameter_compensation_local.png'),'preferred_figure_path':rel(output),'preferred_figure_sha256':sha(output),'original_report_sha256':sha(P/'scientific_report.md'),'original_evidence_manifest_sha256':sha(P/'evidence_manifest.json'),'original_registered_artifacts_unchanged':True}
 save(P/'visual_qa_addendum.json',add)
 actor=read(P/'hub_identity_lease.json')['identity'];hub=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3');task=hub.create_task(actor['agent_id'],'MAIN','record_layout_only_visual_QA',{'run':'run_063','addendum_path':rel(P/'visual_qa_addendum.json'),'addendum_sha256':sha(P/'visual_qa_addendum.json'),'no_new_science_or_FE':True},'run063-visual-QA-v1',depends=('f6637bee-b6c8-4532-b11d-ad4191d5cffa',));lease=hub.claim(task['task_id'],actor,'run063-visual-QA-claim-v1')
 arts=[]
 for p in [Path(__file__),output,P/'visual_qa_addendum.json']:
  r=hub.artifact(task['task_id'],actor['agent_id'],p,{'run':'run_063','scope':'layout-only rendering fix; original artifacts retained'},version='run063-visual-QA-v1');arts.append({'path':rel(p),'sha256':r['sha256']})
 hub.finish(lease,add,evidence_state='RECORDED',science_state='NOT_EVALUATED');assert hub.verify_chain();save(P/'visual_qa_hub_receipt.json',{'task_id':task['task_id'],'registered':arts,'audit_chain_valid':True})
 save(A/'visual_qa_manifest.json',{'files':arts+[{'path':rel(P/'visual_qa_hub_receipt.json'),'sha256':sha(P/'visual_qa_hub_receipt.json')}]})
 j=read(RUN/'run.json');save(RUN/'checkpoints/run_before_visual_QA.json',j);j['outputs'].append({'path':rel(A/'visual_qa_manifest.json'),'role':'layout-only QA addendum; no science change','sha256':sha(A/'visual_qa_manifest.json')});temp=RUN/'run.json.qa.tmp';write(temp,json.dumps(j,ensure_ascii=False,indent=2)+'\n');read(temp);temp.replace(RUN/'run.json')
 print(json.dumps({'preferred_figure':rel(output),'sha256':sha(output),'science_unchanged':True,'Hub_QA_task':task['task_id']}))
if __name__=='__main__':main()
