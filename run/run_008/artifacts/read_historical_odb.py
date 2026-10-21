"""Abaqus Python read-only interface regression; no candidate-solve claim."""
import argparse,hashlib,json,sys
from pathlib import Path
from odbAccess import openOdb

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser(); p.add_argument('--odb',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    source=Path(a.odb).resolve(); before=sha(source); odb=openOdb(path=str(source),readOnly=True)
    try:
        step_name='Step_Punch_Displacement'; region_name='Node ASM_SPT.1'
        if step_name not in odb.steps: raise RuntimeError('historical step missing')
        step=odb.steps[step_name]
        if region_name not in step.historyRegions: raise RuntimeError('historical punch RP history region missing')
        region=step.historyRegions[region_name]; required=('U2','RF2')
        if not all(name in region.historyOutputs for name in required): raise RuntimeError('required history outputs missing')
        u=region.historyOutputs['U2'].data; rf=region.historyOutputs['RF2'].data
        if len(u)!=181 or len(rf)!=181 or [x[0] for x in u]!=[x[0] for x in rf]: raise RuntimeError('history sample count/time synchronization differs from run_005 regression contract')
        result={'status':'PASS_INTERFACE_ONLY','role':'ODB','odb_read_only':True,'source_relative_path':'CAE/Models/Sanity/Job-1.odb','source_sha256_before':before,'source_sha256_after':None,'step':step_name,'history_region':region_name,'outputs':{'U2':{'description':region.historyOutputs['U2'].description,'samples':len(u)},'RF2':{'description':region.historyOutputs['RF2'].description,'samples':len(rf)}},'time_synchronized':True,'candidate_material_solve':'NOT_PERFORMED','interpretation':'Historical Job-1 ODB verifies only the ODB reader interface; it is not the run_008 candidate response.'}
    finally: odb.close()
    result['source_sha256_after']=sha(source)
    if result['source_sha256_after']!=before: raise RuntimeError('source ODB hash changed during read-only interface test')
    out=Path(a.output); out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
