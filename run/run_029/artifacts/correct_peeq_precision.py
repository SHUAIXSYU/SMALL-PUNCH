"""Preserve initial CLI-rounded comparison; bind final PEEQ to ODB JSON precision."""
import hashlib,json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];P=ROOT/'run/run_029/artifacts/private'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
original=P/'comparison/frozen_comparison.json';exact=P/'comparison/frozen_comparison_exact.json'
assert not exact.exists()
x=read(original);odb=read(P/'odb/result.json');v=odb['max_peeq'];old=x['peeq']['V01'];limit=x['peeq']['threshold']
assert abs(v-x['peeq']['candidate'])<1e-14
x['peeq'].update(candidate=v,delta=v-old,absolute_delta=abs(v-old),delta_pass=abs(v-old)<=limit,within_table=v<=x['peeq']['material_table_upper'])
x['checks']['saved_peeq_delta']=x['peeq']['delta_pass'];x['checks']['saved_peeq_within_table']=x['peeq']['within_table']
x['all_quantitative_pass']=all(x['checks'].values())
x['precision_provenance']={'at':datetime.now().astimezone().isoformat(),'original_comparison_sha256':sha(original),'original_cli_peeq':read(original)['peeq']['candidate'],'exact_odb_peeq':v,'difference':v-read(original)['peeq']['candidate'],'reason':'PowerShell CLI numeric argument rounded last bit; final PEEQ read directly from registered ODB result JSON. FD metrics and frozen thresholds unchanged.'}
exact.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
print(json.dumps({'exact_peeq':v,'absolute_delta':x['peeq']['absolute_delta'],'all_quantitative_pass':x['all_quantitative_pass']}))
