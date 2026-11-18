"""MAIN independent comparison of actual ODB table digests to frozen INPs."""
import json,hashlib,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'run/run_022/artifacts/private'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
result=[]
for p in read(ROOT/'run/run_020/artifacts/prepared_batch.json')['points']:
    ex=read(OUT/'extraction'/p['point_id']/'odb_extraction.json');inp=ROOT/p['inp_path'];assert sha(inp)==p['inp_sha256']
    assert ex['status']=='PASS' and ex['odb']['isReadOnly'] and ex['diagnostic_data']['jobStatus']=='JOB_STATUS_COMPLETED_SUCCESSFULLY'
    assert Path(ex['job_data']['name']).stem==p['job_name']
    checks={}
    for keyword,key in [('Elastic','elastic'),('Plastic','plastic')]:
        text=inp.read_text();m=re.search(r'(?im)^\*'+keyword+r'\s*$',text);assert m
        lines=text[m.end():].strip().splitlines();table=[]
        for line in lines:
            if line.startswith('*'):break
            if line.strip():table.append([float(z) for z in line.split(',')])
        digest=hashlib.sha256(json.dumps(table,sort_keys=True).encode()).hexdigest()
        actual=ex['material_summary']['Q200N01'][key]
        assert digest==actual['table_sha256'] and len(table)==actual['row_count']
        checks[key]=dict(rows=len(table),sha256=digest,exact_numeric_match=True)
    assert ex['source_sha256_before']==ex['source_sha256_after']==sha(ROOT/p['expected_odb'])
    result.append(dict(point=p['point_id'],input_sha256=p['inp_sha256'],odb_sha256=ex['source_sha256_after'],tables=checks))
with (OUT/'main_material_identity.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
print(json.dumps(dict(points=len(result),all_actual_materials_match=True)))
