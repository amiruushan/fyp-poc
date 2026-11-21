#!/usr/bin/env python3
"""Evaluate the frozen CompPhish protocol once on the untouched final split."""
from __future__ import annotations
import csv,hashlib,itertools,json
from collections import Counter,defaultdict
from pathlib import Path
import joblib,numpy as np
from sklearn.metrics import average_precision_score,precision_score,recall_score,roc_auc_score
from train_baseline_detectors import sha256,wilson
from validate_feature_registry import version_checks
from run_step8_development_pilot import audit_source_facts,grammar,arm_curve

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'data/manifests/compphish_v4_final_results.json'
BUDGETS=(5,10,20,40)
CHANGES=(1,2,3,4,5)

def interval(records,key,seed):
    grouped=defaultdict(list)
    for r in records:grouped[r['group']].append(r['M_family'][key]['success']-r['S'][key]['success'])
    names=sorted(grouped)
    if not names:return None
    sums=np.array([sum(grouped[n]) for n in names]);sizes=np.array([len(grouped[n]) for n in names])
    rng=np.random.default_rng(seed)
    ids=rng.integers(0,len(names),size=(10000,len(names)))
    draws=sums[ids].sum(axis=1)/sizes[ids].sum(axis=1)
    return [float(x) for x in np.quantile(draws,[.0125,.9875])]

def check_freeze(freeze):
    if freeze['final_evaluation_run'] is not False or freeze['final_split_unsealed'] is not False:
        raise ValueError('Unexpected freeze status')
    for name,item in freeze['artifacts'].items():
        if sha256(ROOT/item['path'])!=item['sha256']:
            raise ValueError(f'Frozen artifact differs: {name}')

def main():
    if OUTPUT.exists():
        raise FileExistsError('Final result manifest already exists; refuse a second run')
    version_checks()
    freeze=json.loads((ROOT/'data/manifests/compphish_v4_final_freeze.json').read_text())
    check_freeze(freeze)
    protocol=json.loads((ROOT/'configs/experiment_protocol_v3.json').read_text())
    attack=json.loads((ROOT/'configs/attack_pilot_v1.json').read_text())
    baseline=json.loads((ROOT/'data/manifests/compphish_v4_baselines.json').read_text())
    registry=json.loads((ROOT/'data/manifests/compphish_v4_feature_registry.json').read_text())
    manifest=json.loads((ROOT/'data/manifests/compphish_v4_feature_matrix.json').read_text())
    if protocol['confirmatory_knowledge']!=['K0'] or protocol['confirmatory_budget']!=freeze['budget']:
        raise ValueError('Protocol differs from freeze')
    if sha256(ROOT/'scripts/run_step8_development_pilot.py')!=attack['script_sha256']:
        raise ValueError('Frozen attack search script changed')
    if sha256(ROOT/'data/processed/compphish_v4_feature_matrix.csv')!=manifest['output_sha256']:
        raise ValueError('Matrix changed')
    names=[f['name'] for f in registry['features']]
    if names!=manifest['feature_columns']:raise ValueError('Feature order changed')
    rows={'train':[],'final':[]}
    with (ROOT/'data/processed/compphish_v4_feature_matrix.csv').open(newline='',encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if row['split'] in rows and row['included_primary']=='1':rows[row['split']].append(row)
    if len(rows['train'])!=9214 or len(rows['final'])!=2303:raise ValueError('Unexpected split sizes')
    factual=audit_source_facts(registry,rows['final'])
    factual['method']='Independent pinned offline recomputation of all final records against archived URL/HTML and frozen matrix'
    if factual['failure_count']:raise ValueError('Final source fidelity check failed')
    specs,X_train=grammar(rows['train'],registry)
    if specs!=attack['grammar']['features']:raise ValueError('Feature grammar changed')
    X=np.array([[float(r[n]) for n in names] for r in rows['final']]);y=np.array([int(r['label']) for r in rows['final']])
    references=np.array([float(np.median(X_train[:,i])) if s['type']!='boolean' else float(np.bincount(X_train[:,i].astype(int)).argmax()) for i,s in enumerate(specs)])
    families=sorted({s['family'] for s in specs})
    family_indices={family:[i for i,s in enumerate(specs) if s['family']==family] for family in families}
    selected=f"{freeze['budget']['changed_coordinates']}:{freeze['budget']['total_binary_queries']}"
    all_log=[];model_results={}
    for model_name in freeze['confirmatory_detectors']:
        frozen=protocol['frozen_models_and_thresholds'][model_name]
        model_path=ROOT/'data/processed/models'/f'{model_name}.joblib'
        if sha256(model_path)!=frozen['model_sha256']:raise ValueError('Model differs from freeze')
        model=joblib.load(model_path)
        threshold=frozen['threshold'];scores=model.predict_proba(X)[:,1];predicted=scores>=threshold
        benign=int(np.count_nonzero(y==0));phishing=int(np.count_nonzero(y==1));fp=int(np.count_nonzero(predicted&(y==0)))
        detector={'rows':len(y),'phishing':phishing,'benign':benign,'threshold':threshold,
            'false_positives':fp,'false_positive_rate':fp/benign,'false_positive_rate_wilson_95':wilson(fp,benign),
            'recall':float(recall_score(y,predicted)),'precision':float(precision_score(y,predicted,zero_division=0)),
            'roc_auc':float(roc_auc_score(y,scores)),'average_precision':float(average_precision_score(y,scores))}
        starts=[i for i in range(len(X)) if y[i]==1 and predicted[i]]
        records=[]
        for i in starts:
            row=rows['final'][i];x=X[i]
            family=families[int(hashlib.sha256(f"{protocol['seed']}:{row['serial_number']}".encode()).hexdigest(),16)%len(families)]
            s=family_indices[family][0]
            eligible=[]
            for j in range(len(specs)):
                if x[j]==references[j]:continue
                z=x.copy();z[j]=references[j]
                reduction=scores[i]-model.predict_proba(z.reshape(1,-1))[0,1]
                if reduction>1e-12:eligible.append((j,reduction))
            m_global=max(eligible,key=lambda a:(a[1],-a[0]))[0] if eligible else None
            matching=[a for a in eligible if a[0] in family_indices[family] and a[0]!=s]
            m_family=max(matching,key=lambda a:(a[1],-a[0]))[0] if matching else None
            record={'serial':row['serial_number'],'group':row['group_id'],'family':family,'S_feature':names[s],
                'M_family_feature':names[m_family] if m_family is not None else '',
                'M_global_feature':names[m_global] if m_global is not None else '',
                'eligible_cue_count':len(eligible),
                'V':arm_curve(model,x,specs,None,threshold),'S':arm_curve(model,x,specs,s,threshold),
                'M_family':arm_curve(model,x,specs,m_family,threshold) if m_family is not None else None,
                'M_global':arm_curve(model,x,specs,m_global,threshold) if m_global is not None else None}
            for arm in ('V','S','M_family','M_global'):
                if record[arm]:
                    for change,q in itertools.product(CHANGES,BUDGETS):
                        if not 1<=record[arm][f'{change}:{q}']['queries']<=q:raise ValueError('Query cap broken')
            records.append(record)
            all_log.append({'model':model_name,'serial_number':record['serial'],'group_id':record['group'],'family':family,
                'S_feature':record['S_feature'],'M_family_feature':record['M_family_feature'],
                'M_global_feature':record['M_global_feature'],'eligible_cue_count':len(eligible),
                **{arm+'_success':record[arm][selected]['success'] if record[arm] else '' for arm in ('V','S','M_family','M_global')},
                **{arm+'_queries':record[arm][selected]['queries'] if record[arm] else '' for arm in ('V','S','M_family','M_global')}})
        matched=[r for r in records if r['M_family'] is not None]
        if not matched:raise ValueError('No eligible matched pairs')
        curve=[]
        for change,q in itertools.product(CHANGES,BUDGETS):
            key=f'{change}:{q}'
            curve.append({'changed_coordinates':change,'total_queries':q,'matched_rows':len(matched),
                'V_rate':sum(r['V'][key]['success'] for r in matched)/len(matched),
                'S_rate':sum(r['S'][key]['success'] for r in matched)/len(matched),
                'M_family_rate':sum(r['M_family'][key]['success'] for r in matched)/len(matched)})
        rates={arm:sum(r[arm][selected]['success'] for r in matched)/len(matched) for arm in ('V','S','M_family')}
        diff=rates['M_family']-rates['S']
        ci=interval(matched,selected,protocol['bootstrap']['seed']+(0 if model_name=='logistic_regression' else 1))
        margin=protocol['equivalence_margin_absolute_risk_difference']
        conclusion='positive paired difference' if ci[0]>0 else ('negative paired difference' if ci[1]<0 else ('equivalent within margin' if ci[0]>-margin and ci[1]<margin else 'inconclusive'))
        all_start={'V':sum(r['V'][selected]['success'] for r in records)/len(records),
            'S':sum(r['S'][selected]['success'] for r in records)/len(records),
            'M_global_with_V_fallback':sum((r['M_global'] or r['V'])[selected]['success'] for r in records)/len(records)}
        model_results[model_name]={'detector':detector,'initially_detected_phishing':len(records),
            'global_model_cue_count':sum(r['M_global'] is not None for r in records),
            'at_least_two_eligible_cues':sum(r['eligible_cue_count']>=2 for r in records),
            'matched_rows':len(matched),'matched_groups':len({r['group'] for r in matched}),
            'matched_rates':rates,'paired_M_family_minus_S':diff,'paired_group_bootstrap_97_5':ci,
            'confirmatory_conclusion':conclusion,'all_start_rates':all_start,
            'matched_discordance':dict(Counter(r['M_family'][selected]['success']-r['S'][selected]['success'] for r in matched)),
            'full_matched_budget_curve':curve}
    log=ROOT/'data/processed/step11_final_selected_log.csv'
    with log.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(all_log[0]),lineterminator='\n');writer.writeheader();writer.writerows(all_log)
    result={'dataset':'CompPhish v4','stage':'Step 11 one-time frozen final evaluation','final_evaluation_run':True,
        'factual_audit':factual,'budget':freeze['budget'],'confirmatory_knowledge':['K0'],
        'confidence_interval':'97.5% two-sided connected-group bootstrap, 10000 replicates per detector, Bonferroni for two primary contrasts',
        'models':model_results,'freeze_manifest_sha256':sha256(ROOT/'data/manifests/compphish_v4_final_freeze.json'),
        'local_selected_log_path':str(log.relative_to(ROOT)),'local_selected_log_sha256':sha256(log),
        'scope_limit':'Abstract feature-vector flips only; no valid website edits or operational phishing evasion established'}
    OUTPUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({m:{'detector':v['detector'],'matched_rows':v['matched_rows'],'matched_groups':v['matched_groups'],
        'paired_M_family_minus_S':v['paired_M_family_minus_S'],'paired_group_bootstrap_97_5':v['paired_group_bootstrap_97_5'],
        'confirmatory_conclusion':v['confirmatory_conclusion']} for m,v in model_results.items()},indent=2))

if __name__=='__main__':main()
