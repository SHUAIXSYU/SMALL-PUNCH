"""Revalidate and package the existing all-25-point final predictors, never retune."""
from common import *
import shutil, zipfile
import numpy as np
from scipy.spatial import ConvexHull
sys.path[:0]=[str(R/'run/run_055/artifacts'),str(R)]
from feature_core import physical_to_normalized
from inverse_baselines import fit_model, predict_model, inner_cache, tune

def main():
    c=read(R/'run/run_056/artifacts/private/prospective_design_contract.json');f=c['frozen_models']
    assert sha(R/f['frozen_inverse_models_path'])==f['frozen_inverse_models_sha256']
    for key in ['feature_implementation','inverse_implementation','model_protocol','training_data_identity']:
        assert sha(R/f[key+'_path'])==f[key+'_sha256']
    models=read(R/f['frozen_inverse_models_path']);identity=read(R/f['training_data_identity_path'])
    old=R/'run/run_055/artifacts/private';arr=read(old/'feature_arrays.json');inv=read(old/'sample_inventory.json')
    assert sha(old/'feature_arrays.json')==identity['feature_array_sha256']
    assert sha(old/'sample_inventory.json')==identity['inventory_sha256']
    ids=arr['primary_ids'];assert ids==models['training_ids']==f['training_ids'] and len(ids)==len(set(ids))==25
    X=np.array([arr['features'][i] for i in ids]);F=np.array([arr['curves'][i] for i in ids]);T=np.array([arr['targets'][i] for i in ids]);Y=physical_to_normalized(T)
    assert len(set(map(tuple,T)))==25 and X.shape==(25,17) and F.shape==(25,241)
    assert not models['experiment_used_for_fit_or_selection'] and models['no_material_or_Hollomon_refitting']
    checks=[]
    for name in ['two_ridge','five_ridge','full_ridge']:
        spec=models['models'][name];m=spec['model'];D=F if spec['input']=='full' else X
        assert m['training_N']==25 and m['lambda']==spec['selection']['lambda']
        # Verify the frozen all-data selection and refit; no new model is chosen or substituted.
        existing_selection=tune(inner_cache(D,Y),[m['columns']])
        assert existing_selection['lambda']==m['lambda']
        regenerated=fit_model(D,Y,'ridge',m['columns'],m['lambda'])
        for field in ['mean','scale','coefficients','target_intercept']:
            np.testing.assert_allclose(regenerated[field],m[field],rtol=2e-12,atol=2e-12)
        z=(D[:,m['columns']]-np.array(m['mean']))/np.array(m['scale'])
        u,s,vt=np.linalg.svd(z,full_matrices=False)
        coef=vt.T@((s/(s*s+25*m['lambda']))[:,None]*(u.T@(Y-Y.mean(0))))
        independent=z@coef+Y.mean(0);frozen=predict_model(m,D)
        np.testing.assert_allclose(independent,frozen,rtol=1e-10,atol=1e-10)
        checks.append({'model':name,'input':spec['input'],'feature_columns':m['columns'],'lambda':m['lambda'],'all_25_refit_matches_original':True,'training_only_LOO_selection_matches':True,'independent_SVD_max_normalized_prediction_difference':float(np.max(abs(independent-frozen))),'future_inputs_used':False})
    directory=P/'frozen_predictor';directory.mkdir(exist_ok=False)
    (directory/'code').mkdir()
    copies={f['frozen_inverse_models_path']:'frozen_FE_only_inverse_models.json',f['feature_implementation_path']:'code/feature_core.py',f['inverse_implementation_path']:'code/inverse_baselines.py',f['model_protocol_path']:'run055_feature_protocol.md',f['training_data_identity_path']:'run055_cv_protocol_identity.json','run/run_055/artifacts/run_nested_cv.py':'code/run055_training_provenance.py','run/run_057/artifacts/predict_frozen.py':'predict_frozen.py'}
    for src,dst in copies.items():shutil.copyfile(R/src,directory/dst)
    hull=ConvexHull(Y)
    training={'version':'run057-frozen-25-training-data-v1','sample_ids':ids,'targets_MPa_n':T.tolist(),'normalized_targets':Y.tolist(),'feature_names':arr['names'],'features':X.tolist(),'grid_m':arr['grid_m'],'full241_N':F.tolist(),'records':[v for v in inv['records'] if v['sample_id'] in ids],'source_full_arrays_path':rel(old/'feature_arrays.json'),'source_full_arrays_sha256':sha(old/'feature_arrays.json'),'source_inventory_sha256':sha(old/'sample_inventory.json'),'unique_parameter_count':25,'CV_predictions_are_not_training_samples':True,'domain':{'declared_sigma_MPa':[150,1000],'declared_n':[.02,.5],'observed_sigma_MPa':[float(T[:,0].min()),float(T[:,0].max())],'observed_n':[float(T[:,1].min()),float(T[:,1].max())],'normalized_parameter_hull_equations':hull.equations.tolist(),'no_full_domain_material_accuracy_claim':True}}
    save(directory/'training_25.json',training)
    b=c['baseline'];save(directory/'constant_I06.json',{'version':'run056-preregistered-constant-baseline','sigma_y_mpa':b['sigma_y_mpa'],'n':b['n'],'x':c['parameter_normalization']['center_x'],'y':c['parameter_normalization']['center_y'],'no_fit':True,'local_normalized_RMSE_under_four_frozen_targets':2**-.5})
    metadata={'version':'run057-frozen-prospective-predictors-v1','frozen_at':now(),'authority':'byte-for-byte unchanged run055 final all-25-point models, as bound by run056; not outer-fold predictors concatenated','original_models_sha256':f['frozen_inverse_models_sha256'],'training_N':25,'training_data_sha256':sha(directory/'training_25.json'),'primary_models':['two_ridge','five_ridge','full_ridge','constant_I06_parameters'],'secondary_models':'unchanged other run055 models retained; no later model selection','verification':checks,'training_rule':'final all-25 fit after training-only LOO selection from fixed lambda grid; no future four-point results exist or used','parameter_coordinates':c['parameter_normalization'],'prediction_rule':'native FD linear interpolation; original means/scales/coefficients/intercepts; physical inverse transform; raw un-clipped; explicit domain flags','future_evaluation_contract':rel(R/'run/run_056/artifacts/private/prospective_design_contract.json'),'future_evaluation_contract_sha256':sha(R/'run/run_056/artifacts/private/prospective_design_contract.json'),'git_HEAD_of_training_snapshot_context':git('rev-parse','HEAD'),'uncommitted_code_identity_is_file_hash_not_HEAD_alone':True}
    save(directory/'predictor_contract.json',metadata)
    write(directory/'README.md','# Frozen prospective FE parameter predictors\n\nThe unchanged run055 final model is authoritative. Each Ridge was fitted on the same 25 unique physical parameter groups, after training-only selection. The 250 outer predictions are not 250 training samples. No candidate FE result is used here.\n\nPrimary inputs: two loads F(.15), F(.90); five features F(.15), F(.30), F(.60), F(.90), Wtotal; and full241. Constant I06 baseline is untrained. Original means, scales, lambda, coefficients and target intercepts are in frozen_FE_only_inverse_models.json. Output is unclipped MPa and n, with normalized coordinates and support flags. No retraining or calibration before Study B completes.\n\nRun predict_frozen.py using the existing torch-gpu interpreter, --bundle this directory, --fd a verified displacement_m/force_n CSV, --output a new private JSON. Loading validates every manifest hash. Package is private FE research data, not a validated material identification formula.\n')
    entries=[{'path':p.relative_to(directory).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(directory.rglob('*')) if p.is_file()]
    save(directory/'package_manifest.json',{'version':'run057-predictor-package-v1','files':entries,'original_model_sha256':f['frozen_inverse_models_sha256'],'no_future_FE_results_used':True})
    package=P/'SPIO_run057_frozen_predictors.zip'
    with zipfile.ZipFile(package,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(directory.rglob('*')):
            if p.is_file():
                info=zipfile.ZipInfo(p.relative_to(directory).as_posix(),date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(package) as z:
        assert z.testzip() is None
        for item in entries:assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
    save(P/'predictor_freeze_receipt.json',{'frozen_at':now(),'training_N':25,'original_model_sha256':f['frozen_inverse_models_sha256'],'packaged_model_identical':sha(directory/'frozen_FE_only_inverse_models.json')==f['frozen_inverse_models_sha256'],'training_25_sha256':sha(directory/'training_25.json'),'checks':checks,'package_path':rel(package),'package_sha256':sha(package),'manifest_sha256':sha(directory/'package_manifest.json'),'future_FE_observed':0,'new_selection_or_changed_model':False})
    print(json.dumps({'frozen_models':4,'training_unique_parameters':25,'original_model_sha256_unchanged':True,'final_lambda':{x['model']:x['lambda'] for x in checks},'package_sha256':sha(package)}))

if __name__=='__main__':main()
