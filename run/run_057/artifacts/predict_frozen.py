"""Inference only. Use with the run057 frozen predictor directory; never fits models."""
from pathlib import Path
import argparse, csv, hashlib, json, sys
import numpy as np

def predict_file(bundle_dir, csv_path):
    bundle=Path(bundle_dir)
    manifest=json.loads((bundle/'package_manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path=bundle/item['path']
        if not path.resolve().is_relative_to(bundle.resolve()):raise ValueError('unsafe package path')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('frozen artifact hash mismatch: '+item['path'])
    sys.path.insert(0,str(bundle/'code'))
    from feature_core import extract, normalized_to_physical
    from inverse_baselines import predict_model, support
    from scipy.spatial import Delaunay
    frozen=json.loads((bundle/'frozen_FE_only_inverse_models.json').read_text())
    train=json.loads((bundle/'training_25.json').read_text())
    with Path(csv_path).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    feat,curve,diagnostics=extract([float(r['displacement_m']) for r in rows],[float(r['force_n']) for r in rows])
    targets=np.array(train['normalized_targets']);hull=Delaunay(targets);output={}
    for name in ['two_ridge','five_ridge','full_ridge']:
        spec=frozen['models'][name];m=spec['model'];q=curve if spec['input']=='full' else feat
        X=np.array(train['full241_N'] if spec['input']=='full' else train['features'])
        norm=predict_model(m,q)[0];phys=normalized_to_physical(norm[None,:])[0];domain=support(m,X,q)
        domain['nearest_train_id']=train['sample_ids'][domain.pop('nearest_train_index')]
        domain['outside_training_parameter_hull']=bool(hull.find_simplex(norm)<0)
        domain['outside_declared_parameter_bounds']=bool(np.any((norm<0)|(norm>1)))
        output[name]={'sigma_y_mpa':float(phys[0]),'n':float(phys[1]),'x':float(norm[0]),'y':float(norm[1]),'unclipped':True,'domain':domain}
    c=json.loads((bundle/'constant_I06.json').read_text())
    output['constant_I06_parameters']={k:c[k] for k in ['sigma_y_mpa','n','x','y']}
    return {'prediction_scope':'FE-only frozen local prospective model; not measured material truth','predictions':output,'feature_extraction':diagnostics,'no_training_or_tuning':True}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--bundle',required=True);ap.add_argument('--fd',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    value=predict_file(args.bundle,args.fd)
    with Path(args.output).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False)
