#!/usr/bin/env python3
"""Development-only clustered precision projection for the matched cue contrast."""
import csv, json
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
from train_baseline_detectors import sha256

ROOT=Path(__file__).resolve().parents[1]
SEED=20261125
REPLICATES=10000
ADJUSTED_INTERVAL=.975
MIN_GROUPS=200
MAX_PROJECTED_HALF_WIDTH=.08

def main():
    pilot=json.loads((ROOT/'data/manifests/compphish_v4_step8_pilot.json').read_text())
    log=ROOT/pilot['selected_log_path']
    if sha256(log)!=pilot['selected_log_sha256']:
        raise ValueError('Step 8 local log hash mismatch')
    with log.open(newline='',encoding='utf-8') as stream:
        rows=list(csv.DictReader(stream))
    result={'scope':'development only; conditional projection if final matched-group composition resembles development',
            'bootstrap_seed':SEED,'replicates':REPLICATES,'cluster_unit':'connected_group',
            'adjusted_interval_coverage':ADJUSTED_INTERVAL,'two_confirmatory_model_contrasts':True,
            'minimum_matched_groups':MIN_GROUPS,'maximum_projected_half_width':MAX_PROJECTED_HALF_WIDTH,
            'equivalence_margin_absolute_risk_difference':.05,'models':{}}
    for model in ('logistic_regression','gradient_boosting'):
        matched=[r for r in rows if r['model']==model and r['M_family_success']!='']
        grouped=defaultdict(list)
        for r in matched:
            grouped[r['group_id']].append(int(r['M_family_success'])-int(r['S_success']))
        ids=sorted(grouped)
        sums=np.array([sum(grouped[g]) for g in ids],dtype=float)
        sizes=np.array([len(grouped[g]) for g in ids],dtype=float)
        estimate=float(sums.sum()/sizes.sum())
        rng=np.random.default_rng(SEED+(0 if model=='logistic_regression' else 1))
        indexes=rng.integers(0,len(ids),size=(REPLICATES,len(ids)))
        draws=sums[indexes].sum(axis=1)/sizes[indexes].sum(axis=1)
        alpha=(1-ADJUSTED_INTERVAL)/2
        ci=[float(v) for v in np.quantile(draws,[alpha,1-alpha])]
        half_width=max(estimate-ci[0],ci[1]-estimate)
        discordance=Counter(int(r['M_family_success'])-int(r['S_success']) for r in matched)
        result['models'][model]={'matched_rows':len(matched),'matched_groups':len(ids),'paired_difference':estimate,
            'discordant_M_only':discordance[1],'discordant_S_only':discordance[-1],
            'development_cluster_bootstrap_adjusted_interval':ci,
            'projected_half_width_same_size_groups':half_width,
            'projection_gate_passed':len(ids)>=MIN_GROUPS and half_width<=MAX_PROJECTED_HALF_WIDTH,
            'equivalence_at_margin_from_development_interval':ci[0]>-.05 and ci[1]<.05}
    result['projection_gate_passed_both']=all(x['projection_gate_passed'] for x in result['models'].values())
    output=ROOT/'data/manifests/compphish_v4_step9_precision.json'
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result['models'],indent=2))

if __name__=='__main__':main()
