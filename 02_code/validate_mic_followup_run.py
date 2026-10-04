"""Compare frozen metric columns and independently retain confusion counts.

The frozen training entry and model artifacts remain byte-for-byte unchanged.
"""
import argparse
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import train_mic_followup_baseline as frozen
from research_utils import ROOT, read_json, sha256, utc_now, write_json
from validate_mic_three_fold_run import independent_metrics

DECLARED={'n','positive','negative','AUPRC','AUROC','MCC_at_0_5',
          'balanced_accuracy_at_0_5','accuracy_at_0_5'}


def declared_metrics(y,scores):
    full=independent_metrics(y,scores)
    return {name:value for name,value in full.items() if name in DECLARED}


def validate(run,output,protocol,freeze):
    run,protocol,freeze=(Path(p).resolve() for p in (run,protocol,freeze))
    output=Path(output).resolve()
    raw=output.with_name(output.stem+'_declared_metrics.json')
    if output.exists() or raw.exists():raise FileExistsError('Validation output already exists')
    with patch.object(frozen,'independent_metrics',declared_metrics):
        verified=frozen.validate(Path(run),raw,Path(protocol),Path(freeze))
    rows=pd.read_csv(Path(run)/'oof_predictions.csv',float_precision='round_trip')
    counts=[]
    for name,part in rows.groupby('model',sort=True):
        full=independent_metrics(part.observed_label.to_numpy(),part.probability.to_numpy())
        counts.append({'model':name,**{key:full[key] for key in ('TP','FP','TN','FN')}})
    result={**verified,'generated_at':utc_now(),'confusion_counts':counts,
            'independent_validator':Path(__file__).relative_to(ROOT).as_posix(),
            'metric_schema_resolution':'Compare all frozen declared numeric columns; independently report confusion counts absent from the training schema.',
            'declared_metrics_validation':raw.relative_to(ROOT).as_posix(),
            'inputs':{**verified['inputs'],raw.relative_to(ROOT).as_posix():sha256(raw),
                      Path(__file__).relative_to(ROOT).as_posix():sha256(Path(__file__))}}
    write_json(output,result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','output','protocol','freeze'):parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    import json
    print(json.dumps(validate(args.run,args.output,args.protocol,args.freeze),ensure_ascii=False,indent=2))
