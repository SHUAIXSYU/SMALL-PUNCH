import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'run/run_047'
FREEZE = ROOT / 'run/run_046/artifacts/private/freeze'
ZIP = ROOT / 'run/run_046/artifacts/private/SP_InvOpt_run046_frozen_candidates.zip'
EXPECTED_ZIP = 'd439ef3ae696d9711aa3a3d4fa989f61710adf3cd9a73c9935b9432131dddc3a'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    manifest = json.loads((FREEZE / 'frozen_manifest.json').read_text(encoding='utf-8'))
    expected = {x['bundle_path']: x for x in manifest['files']}
    findings = []
    def check(name, ok, detail=None):
        findings.append({'check': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})
    check('zip_exists', ZIP.is_file())
    if not ZIP.is_file():
        raise SystemExit('BLOCKED_FREEZE_INTEGRITY: ZIP absent')
    zip_bytes = ZIP.read_bytes()
    check('zip_sha256', sha(zip_bytes) == EXPECTED_ZIP, sha(zip_bytes))
    with zipfile.ZipFile(ZIP) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        safe = all(not i.is_dir() and not i.filename.startswith('/') and '\\' not in i.filename
                   and all(p not in ('', '.', '..') for p in PurePosixPath(i.filename).parts)
                   and PurePosixPath(i.filename).name == i.filename for i in infos)
        check('safe_flat_paths', safe)
        check('unique_names', len(names) == len(set(names)))
        check('manifest_set_equals_zip_set_with_self', set(names) == set(expected) | {'frozen_manifest.json'}, {'zip_count': len(names), 'manifest_payload_count': len(expected)})
        check('all_crc', z.testzip() is None)
        check('bundled_manifest_equals_external', z.read('frozen_manifest.json') == (FREEZE / 'frozen_manifest.json').read_bytes())
        for name, item in expected.items():
            if name not in names:
                check(f'{name}:exists', False)
                continue
            data = z.read(name)
            check(f'{name}:bundle_sha256_size', sha(data) == item['sha256'] and len(data) == item['bytes'],
                  {'sha256': sha(data), 'bytes': len(data)})
            disk = ROOT / item['path']
            check(f'{name}:external_sha256_size', disk.is_file() and sha(disk.read_bytes()) == item['sha256'] and disk.stat().st_size == item['bytes'])
    report = {'status': 'PASS' if all(f['status']=='PASS' for f in findings) else 'BLOCKED_FREEZE_INTEGRITY',
              'zip_path': str(ZIP.relative_to(ROOT)).replace('\\','/'), 'zip_sha256': sha(zip_bytes),
              'manifest_path': 'run/run_046/artifacts/private/freeze/frozen_manifest.json',
              'checks': findings}
    out = RUN / 'artifacts/private/freeze_integrity.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(report['status'], len(findings), out)
    if report['status'] != 'PASS':
        raise SystemExit(2)

if __name__ == '__main__':
    main()
