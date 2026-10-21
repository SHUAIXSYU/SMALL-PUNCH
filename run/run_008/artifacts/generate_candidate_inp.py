"""Create a fresh candidate INP from the historical Job-1 INP without touching it."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from inverse.hollomon import generate_hollomon_table
SOURCE=ROOT/'CAE'/'Models'/'Sanity'/'Job-1.inp'
JOB='SPIO_R008_Q200_N010_Candidate'
OUT=ROOT/'run'/'run_008'/'artifacts'/'candidate_inp'/JOB
PRIVATE=ROOT/'run'/'run_008'/'artifacts'/'private'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def main():
    if OUT.exists(): raise SystemExit('REFUSE_EXISTING_OUTPUT')
    if not SOURCE.is_file(): raise SystemExit('SOURCE_INP_MISSING')
    raw=SOURCE.read_text(encoding='utf-8-sig'); lines=raw.splitlines(keepends=True)
    materials=[i for i,line in enumerate(lines) if re.match(r'^\*Material\s*,\s*name\s*=\s*Q200N01\s*$',line.strip(),re.I)]
    if len(materials)!=1: raise SystemExit(f'EXPECTED_ONE_SOURCE_MATERIAL_BLOCK; found={len(materials)}')
    start=next((i for i in range(materials[0]+1,len(lines)) if lines[i].strip().lower()=='*plastic'),None)
    if start is None: raise SystemExit('SOURCE_PLASTIC_BLOCK_MISSING')
    end=next((i for i in range(start+1,len(lines)) if lines[i].lstrip().startswith('*')),len(lines))
    table=generate_hollomon_table(200.0,0.1,max_plastic_strain=0.9)
    block=table.abaqus_plastic_text()
    if not block.endswith('\n'): block+='\n'
    new=''.join(lines[:start])+block+''.join(lines[end:])
    OUT.mkdir(parents=True)
    target=OUT/f'{JOB}.inp'
    target.write_text(new,encoding='utf-8',newline='\n')
    PRIVATE.mkdir(parents=True,exist_ok=True)
    audit={'source_relative_path':'CAE/Models/Sanity/Job-1.inp','source_sha256':sha(SOURCE),'source_context':'Historical Job-1 input; CAE save-to-INP equivalence is UNKNOWN','source_license':'SMALL-PUNCH owner-provided project input; reuse limited to this project-local candidate','processing':'Read source bytes only; replace Q200N01 *Plastic block with inverse.hollomon candidate rows; preserve remaining historical input text; write fresh uniquely named INP in isolated directory','generator':'inverse/hollomon.py candidate-true-total-hollomon-v1','parameters':{'E_Pa':210000000000.0,'nu':0.3,'sigma_y_MPa':200.0,'n':0.1,'max_plastic_strain':0.9},'output_relative_path':str(target.relative_to(ROOT)).replace('\\','/'),'output_sha256':sha(target),'rows':len(table.rows),'physical_validation':'NOT_PERFORMED'}
    (PRIVATE/'candidate_source_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
