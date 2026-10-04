"""Lazy, fail-closed loading of a completed, provenance-validated ensemble."""
from pathlib import Path
import numpy as np
import torch
from scipy.special import expit, logit
from feature_extractor import ESMFeatureExtractor
from model_dual_task import SafeAMPDualNet
from research_utils import read_json, sha256

class ModelUnavailable(RuntimeError):
    pass

class ResearchRuntime:
    def __init__(self,run_dir=None):
        self.run_dir=Path(run_dir) if run_dir else None
        self.extractor=None;self.members=[];self.metadata={};self.error=None

    def load(self):
        if self.members:return self
        try:
            if self.run_dir is None:raise ModelUnavailable('No validated research run configured (SAFEAMP_RUN_DIR).')
            manifest=read_json(self.run_dir/'manifest.json')
            if manifest.get('status')!='completed' or manifest.get('dataset_manifest',{}).get('status')!='validated':
                raise ModelUnavailable('Research run or dataset did not pass validation.')
            if sha256(self.run_dir/'predictions.csv')!=manifest.get('predictions_sha256'):
                raise ModelUnavailable('Prediction artifact checksum mismatch.')
            checkpoints=manifest.get('checkpoints',[])
            if len(checkpoints)!=3 or {c['seed'] for c in checkpoints}!={11,23,42}:
                raise ModelUnavailable('Complete three-seed ensemble required.')
            for c in checkpoints:
                path=(self.run_dir/c['path']).resolve()
                if not path.is_relative_to(self.run_dir.resolve()) or sha256(path)!=c['sha256']:
                    raise ModelUnavailable('Model checkpoint checksum mismatch.')
            for module in ['feature_extractor.py','model_dual_task.py']:
                if manifest.get('code_hashes',{}).get(module)!=sha256(Path(__file__).parent/module):
                    raise ModelUnavailable('Feature or architecture implementation changed since training.')
            extractor=ESMFeatureExtractor()
            feature=manifest['features']
            esm_file=Path(torch.hub.get_dir())/'checkpoints/esm2_t6_8M_UR50D.pt'
            if (not extractor.real_esm_available or extractor.backend!=feature['backend']
                or extractor.feature_version!=feature['version'] or sha256(esm_file)!=feature['esm_sha256']):
                raise ModelUnavailable('Feature encoder provenance mismatch.')
            members=[]
            for c in checkpoints:
                ck=torch.load(self.run_dir/c['path'],map_location='cpu',weights_only=True)
                if ck['features']!=feature or ck['seed']!=c['seed']:
                    raise ModelUnavailable('Checkpoint metadata mismatch.')
                config=ck['config']
                if config!=manifest['config']:
                    raise ModelUnavailable('Checkpoint configuration differs from run manifest.')
                for prefix,size in [('esm',320),('phys',44)]:
                    mean,scale=np.asarray(ck[prefix+'_mean']),np.asarray(ck[prefix+'_scale'])
                    if mean.shape!=(size,) or scale.shape!=(size,) or not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale<=0).any():
                        raise ModelUnavailable('Invalid saved preprocessing parameters.')
                if len(ck['calibration'])!=2 or not all(np.isfinite([v['coefficient'],v['intercept']]).all() for v in ck['calibration']):
                    raise ModelUnavailable('Invalid saved calibration parameters.')
                model=SafeAMPDualNet(hidden_dim=config['hidden_dim'],dropout_rate=config['dropout'])
                model.load_state_dict(ck['state_dict'],strict=True);model.eval()
                if any(not torch.isfinite(p).all() for p in model.parameters()):
                    raise ModelUnavailable('Non-finite model parameters.')
                members.append((model,ck))
            self.members=members;self.extractor=extractor
            self.metadata={'run_id':self.run_dir.name,'backend':feature['backend'],'feature_version':feature['version'],
                           'seeds':[11,23,42],'score_type':'computational_ranking_score','clinical_validation':False,
                           'model_kind':'mean_of_three_calibrated_seed_predictions',
                           'amp_endpoint':'E. coli MIC <=32 vs >=128 ug/ml','hemo_endpoint':'Human erythrocyte HC50 <=100 vs >=250 ug/ml'}
            self.error=None
        except Exception as exc:
            self.error=str(exc);self.members=[];self.extractor=None
            raise ModelUnavailable(str(exc)) from exc
        return self

    def status(self):
        try:self.load()
        except ModelUnavailable:pass
        ready=bool(self.members)
        return {'status':'healthy' if ready else 'unavailable','reason':self.error,
                'esm_model':{'name':'ESM-2 8M','backend':self.metadata.get('backend','unavailable'),'status':'Loaded' if ready else 'Unavailable'},
                'dual_task_model':{'name':'SafeAMP-Dual research ensemble','weights_loaded':ready,'status':'Validated' if ready else 'Not validated'},
                'mutation_engine':{'name':'Exploratory scoring','status':'Ready' if ready else 'Disabled'},'provenance':self.metadata}

    def to(self,device):return self
    def eval(self):return self

    @torch.no_grad()
    def predict_probabilities(self,x_esm,x_phys):
        self.load()
        e=x_esm.detach().cpu().numpy();p=x_phys.detach().cpu().numpy();values=[]
        for model,ck in self.members:
            es=(e-np.asarray(ck['esm_mean']))/np.asarray(ck['esm_scale'])
            ph=(p-np.asarray(ck['phys_mean']))/np.asarray(ck['phys_scale'])
            a,h,_=model(torch.tensor(es,dtype=torch.float32),torch.tensor(ph,dtype=torch.float32))
            raw=np.column_stack([torch.sigmoid(a).numpy(),torch.sigmoid(h).numpy()])
            for t,c in enumerate(ck['calibration']):
                raw[:,t]=expit(c['coefficient']*logit(np.clip(raw[:,t],1e-6,1-1e-6))+c['intercept'])
            values.append(raw)
        mean=np.mean(values,axis=0)
        return mean[:,0],mean[:,1],mean[:,0]*(1-mean[:,1])
