#!/usr/bin/env python3
"""Verify frozen primary results from the local row log and build demo aggregate data."""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
DEMO=Path(__file__).resolve().parent
RESULT=ROOT/'data/manifests/compphish_v4_final_results.json'
FREEZE=ROOT/'data/manifests/compphish_v4_final_freeze.json'
N_REPLICATES=10000
SEED=20261123

def sha256(path:Path)->str:
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def close(a,b):return abs(a-b)<1e-12

def verify_primary(result:dict)->dict:
    log=ROOT/result['local_selected_log_path']
    if not log.exists():
        raise FileNotFoundError(f'Local final row log is missing: {log}. The browser demo remains viewable; reproduce the row log in an isolated copy of the frozen project before verifying.')
    if sha256(log)!=result['local_selected_log_sha256']:
        raise ValueError('Final row log hash differs from frozen result')
    with log.open(newline='',encoding='utf-8') as stream:rows=list(csv.DictReader(stream))
    output={}
    for name,offset in (('logistic_regression',0),('gradient_boosting',1)):
        expected=result['models'][name]
        matched=[r for r in rows if r['model']==name and r['M_family_success']!='']
        if len(matched)!=expected['matched_rows']:
            raise ValueError(f'Matched row count differs for {name}')
        groups=defaultdict(list)
        for row in matched:
            groups[row['group_id']].append(int(row['M_family_success'])-int(row['S_success']))
        keys=sorted(groups)
        if len(keys)!=expected['matched_groups']:
            raise ValueError(f'Matched group count differs for {name}')
        rates={arm:sum(int(row[arm+'_success']) for row in matched)/len(matched)
               for arm in ('V','S','M_family')}
        delta=rates['M_family']-rates['S']
        if not all(close(rates[arm],expected['matched_rates'][arm]) for arm in rates):
            raise ValueError(f'Paired rate differs for {name}')
        if not close(delta,expected['paired_M_family_minus_S']):
            raise ValueError(f'Paired risk difference differs for {name}')
        sums=np.array([sum(groups[k]) for k in keys]);sizes=np.array([len(groups[k]) for k in keys])
        rng=np.random.default_rng(SEED+offset)
        ids=rng.integers(0,len(keys),size=(N_REPLICATES,len(keys)))
        draws=sums[ids].sum(axis=1)/sizes[ids].sum(axis=1)
        interval=[float(x) for x in np.quantile(draws,[.0125,.9875])]
        if not all(close(a,b) for a,b in zip(interval,expected['paired_group_bootstrap_97_5'])):
            raise ValueError(f'Cluster bootstrap interval differs for {name}')
        output[name]={'matched_rows':len(matched),'matched_groups':len(keys),'rates':rates,
                      'risk_difference':delta,'adjusted_interval':interval,'passed':True}
    return output

def snapshot(result:dict,verified:dict|None)->dict:
    models={}
    for name,item in result['models'].items():
        models[name]={'detector':item['detector'],'detected_phishing':item['initially_detected_phishing'],
            'matched_rows':item['matched_rows'],'matched_groups':item['matched_groups'],
            'matched_rates':item['matched_rates'],'difference':item['paired_M_family_minus_S'],
            'interval':item['paired_group_bootstrap_97_5'],'all_start_rates':item['all_start_rates'],
            'global_cues':item['global_model_cue_count'],'two_cues':item['at_least_two_eligible_cues'],
            'budget_curve':item['full_matched_budget_curve'],
            'query_cost':result['query_cost_summary'][name],
            'discordance':item['matched_discordance']}
    return {'study':'CompPhish v4 | Frozen final evaluation','source_manifest_sha256':sha256(RESULT),
            'freeze_manifest_sha256':sha256(FREEZE),'source_checks':result['factual_audit']['feature_checks'],
            'source_failures':result['factual_audit']['failure_count'],'budget':result['budget'],
            'models':models,'reproduction':{'verified_from_local_log':verified is not None,
                'local_log_sha256':result['local_selected_log_sha256'],
                'checked_models':list(verified) if verified else []}}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--render-only',action='store_true',help='Build the static demo snapshot without the ignored row log')
    args=parser.parse_args()
    result=json.loads(RESULT.read_text())
    if not result['final_evaluation_run'] or result['freeze_manifest_sha256']!=sha256(FREEZE):
        raise ValueError('Final result/freeze relationship is invalid')
    verified=None if args.render_only else verify_primary(result)
    data=snapshot(result,verified)
    out=DEMO/'data.js'
    out.write_text('window.COMP_PHISH_DEMO = '+json.dumps(data,sort_keys=True,separators=(',',':'))+';\n',encoding='utf-8')
    print(json.dumps({'primary_result_verified':verified is not None,'models':verified,
                      'static_snapshot':str(out.relative_to(ROOT)),'source_manifest_sha256':data['source_manifest_sha256']},indent=2))

if __name__=='__main__':main()
