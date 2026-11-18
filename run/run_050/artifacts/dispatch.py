"""MAIN dispatch of existing D01/I08 ODB read-only spatial research."""
from pathlib import Path
import sys,json,hashlib,subprocess
from datetime import datetime
R=Path(r'E:\Projects\SMALL-PUNCH');RUN=R/'run/run_050';P=RUN/'artifacts/private';sys.path.insert(0,str(R))
from agenthub_sp_invopt.hub import Hub
def now():return datetime.now().astimezone().isoformat()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=R,text=True).strip()
start={'at':now(),'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('remote','-v'),'working_tree':git('status','--short'),'python':sys.executable}
save(RUN/'checkpoints/start.json',start)
protected={p:sha(R/p) for p in ['run/run_046/artifacts/private/SP_InvOpt_run046_frozen_candidates.zip','run/run_048/artifacts/private/independent_reassessment_report.md','run/run_049/artifacts/private/scientific_assessment.md','inverse/hollomon.py']}
save(P/'protected_before.json',protected)
h=Hub(R/'agenthub_sp_invopt/runtime/sp_invopt.sqlite3',lease_seconds=14400);identity=h.register('MAIN','codex-main-run050-high-plasticity')
main=h.create_task(identity['agent_id'],'MAIN','high_plasticity_scientific_assessment',{'run':'run_050','scope':'existing spatial/energy evidence; frozen material curves and minimum fixture uncertainty research; no new FE, fit or INP','formal_independent_validation':'NOT_EVALUABLE_UNCHANGED'},'run050-main-v1');lease=h.claim(main['task_id'],identity,'run050-main-claim-v1')
points=[]
for q in read(R/'run/run_043/artifacts/prepared_batch.json')['points']:
 result=read(R/f"run/run_045/artifacts/private/odb/{q['point_id']}/result.json")
 assert sha(R/q['inp_path'])==q['inp_sha256']
 points.append({**q,'odb_path':q['expected_odb'],'odb_sha256':result['odb_sha256'],'queue_id':result['queue_id'],'completed_result_path':f"run/run_045/artifacts/private/odb/{q['point_id']}/result.json"})
payload={'run_id':'run_050','scope':'READ_ONLY_EXISTING_ODB_SPATIAL_ENERGY','points':points,'output_dir':'run/run_050/artifacts/private/odb','comparison_displacements_mm':[0.3,0.6,0.9,1.2],'peeq_thresholds':[0.1,0.3,0.5],
 'requirements':['verify original INP/ODB full hashes and successful source identities; no original changes','actual element CAX4: verify axisymmetric integration/IP map; use IVOL if available, otherwise explicitly reconstruct reference/current 2*pi*r*detJ 2x2 Gauss weights from coordinates and U and validate total reference volume and node/IP ordering; never substitute area for volume','export actual IP coordinates/PEEQ/weights at nearest saved frame to each target; record exact displacement and tolerance, no invented interpolation field','map whole specimen PEEQ and threshold regions; full specimen denominator, distinguish reference vs current volume fractions and integration-point classification vs exact threshold interface','quantify radial/thickness distribution and distinguish central contact/bending/support ring; no load contribution claims from maximum or volume fraction','inventory available energy fields/history; direct local plastic dissipation only if saved; otherwise a clearly labeled reconstructed estimate only if actual stress/PEEQ/time/volume evidence supports J2 plastic work and check summed estimate against ALLPD. Save limits, error and attribution convention; never call it exact or RF2 share','compare contact CPRESS/COPEN footprint and FD at sampled stages; global energy balance available; no smoothing, fits or changes','save structured result.json, CSVs, figures/provenance; register small artifacts and message MAIN through existing Hub; finish ODB task NOT_EVALUATED or WARNING'],
 'boundaries':['no solver or datacheck, enqueue, retry or new input','do not inspect raw or old leaked tensile analyses; MAIN will use released run048/049 limitations','do not modify global Run index/status/MAIN report; own output subtree only','no infrastructure changes or dependency installs','do not imply equivalent plastic strain equals true total uniaxial strain'],
 'expected_return':'spatial_energy_result.json with source hashes, physical volume definitions, energy attribution strength, contact and limitations'}
odb=h.create_task(identity['agent_id'],'ODB','readonly_high_plasticity_spatial_energy_analysis',payload,'run050-odb-spatial-energy-v1')
h.message(odb['task_id'],identity['agent_id'],'ODB',{'request_file':'run/run_050/artifacts/odb_task_payload.json','task_id':odb['task_id'],'read_only':True,'real_codex_session_required':True},'run050-odb-dispatch-v1')
save(RUN/'artifacts/odb_task_payload.json',payload);save(P/'hub_session.json',{'identity':identity,'main_task_id':main['task_id'],'lease':lease,'odb_task_id':odb['task_id']})
save(RUN/'run.json',{'schema_version':'1.0','run_id':'run_050','stage':'High plastic strain spatial evidence and model-discrepancy research','objective':'real ODB spatial/energy extraction; frozen constitutive extrapolation and fixture uncertainty design','status':'RUNNING','start_time':start['at'],'end_time':None,'python_interpreter':sys.executable,'git_branch':start['branch'],'git_head':start['head'],'inputs':[{'path':'run/run_050/artifacts/odb_task_payload.json','role':'bounded existing ODB identities and read-only scope'}],'outputs':[],'validation':[],'errors':[]})
print(json.dumps({'run':'run_050','main_task_id':main['task_id'],'odb_task_id':odb['task_id'],'payload':'run/run_050/artifacts/odb_task_payload.json'}))
