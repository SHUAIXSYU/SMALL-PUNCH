import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT/'run/run_048'
FREEZE = ROOT/'run/run_046/artifacts/private/freeze'
ZIP = ROOT/'run/run_046/artifacts/private/SP_InvOpt_run046_frozen_candidates.zip'
ORIGIN = ROOT/'references_private/508 RAW TENSILE TEST.opju'
EXTRACT = ROOT/'run/run_047/artifacts/private/origin_extract.json'
EXPECTED_ZIP='d439ef3ae696d9711aa3a3d4fa989f61710adf3cd9a73c9935b9432131dddc3a'
EXPECTED_ORIGIN='d5aad7f555a5c67e9198230f10578135425f7508f8214a73f7d8102c1c3dcd64'

def sha(b): return hashlib.sha256(b).hexdigest()
checks=[]
def check(name, ok, detail=None):
    checks.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail})

manifest=json.loads((FREEZE/'frozen_manifest.json').read_text(encoding='utf-8'))
expected={item['bundle_path']:item for item in manifest['files']}
check('zip_exists',ZIP.is_file())
if not ZIP.is_file(): raise SystemExit('BLOCKED_FREEZE_INTEGRITY')
check('zip_sha256',sha(ZIP.read_bytes())==EXPECTED_ZIP,sha(ZIP.read_bytes()))
with zipfile.ZipFile(ZIP) as z:
    infos=z.infolist(); names=[i.filename for i in infos]
    safe=all(not i.is_dir() and not i.filename.startswith('/') and '\\' not in i.filename
             and PurePosixPath(i.filename).name==i.filename
             and all(p not in ('','.','..') for p in PurePosixPath(i.filename).parts) for i in infos)
    check('safe_archive_paths',safe)
    check('unique_archive_names',len(names)==len(set(names)))
    check('bundle_set',set(names)==set(expected)|{'frozen_manifest.json'},len(names))
    check('all_crc',z.testzip() is None)
    check('bundled_manifest_equals_external',z.read('frozen_manifest.json')==(FREEZE/'frozen_manifest.json').read_bytes())
    for name,item in expected.items():
        data=z.read(name)
        check(name+':bundle',sha(data)==item['sha256'] and len(data)==item['bytes'])
        disk=ROOT/item['path']
        check(name+':external',disk.is_file() and sha(disk.read_bytes())==item['sha256'] and disk.stat().st_size==item['bytes'])

freeze_pass=all(c['status']=='PASS' for c in checks)
if not freeze_pass:
    result={'observed_at':datetime.now().astimezone().isoformat(),'status':'BLOCKED_FREEZE_INTEGRITY','checks':checks}
    out=RUN/'artifacts/private/input_integrity.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    raise SystemExit('BLOCKED_FREEZE_INTEGRITY')

# Original source and prior extraction identities are inspected only after freeze checks pass.
check('origin_file_sha256',ORIGIN.is_file() and sha(ORIGIN.read_bytes())==EXPECTED_ORIGIN,
      {'bytes':ORIGIN.stat().st_size,'sha256':sha(ORIGIN.read_bytes()),'mtime':datetime.fromtimestamp(ORIGIN.stat().st_mtime).astimezone().isoformat()})
ledger=json.loads((ROOT/'run/run_047/artifacts/private/evidence_manifest.json').read_text(encoding='utf-8'))
entry=next(i for i in ledger['items'] if i['path']=='run/run_047/artifacts/private/origin_extract.json')
check('run047_extract_sha256',sha(EXTRACT.read_bytes())==entry['sha256'],entry['sha256'])
data=json.loads(EXTRACT.read_text(encoding='utf-8'))
check('origin_extraction_structure',len(data['workbooks'])==1 and len(data['workbooks'][0]['sheets'])==1 and
      len(data['workbooks'][0]['sheets'][0]['data_columns'])==2 and
      all(len(col)==355 for col in data['workbooks'][0]['sheets'][0]['data_columns']))
out=RUN/'artifacts/private/input_integrity.json'
result={'observed_at':datetime.now().astimezone().isoformat(),
        'status':'PASS' if all(c['status']=='PASS' for c in checks) else 'BLOCKED_INPUT_IDENTITY',
        'checks':checks}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(result['status'],len(checks),out)
if result['status']!='PASS': raise SystemExit(2)
