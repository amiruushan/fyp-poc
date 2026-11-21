#!/usr/bin/env python3
"""One-time frozen implementation check on the method-validation split."""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
import joblib,numpy as np
from train_baseline_detectors import sha256
from validate_feature_registry import version_checks
from run_step8_development_pilot import audit_source_facts,grammar,arm_curve

ROOT=Path(__file__).resolve().parents[1]


def group_interval(rows,seed):
    grouped=defaultdict(list)
    for r in rows:grouped[r['group_id']].append(r['M_family_success']-r['S_success'])
    keys=sorted(grouped)
    if not keys:return None
    sums=np.array([sum(grouped[k]) for k in keys]);sizes=np.array([len(grouped[k]) for k in keys])
    rng=np.random.default_rng(seed)
    indexes=rng.integers(0,len(keys),size=(10000,len(keys)))
    draws=sums[indexes].sum(axis=1)/sizes[indexes].sum(axis=1)
    return [float(x) for x in np.quantile(draws,[.0125,.9875])]


def self_check():
    class Model:
        def predict_proba(self,X):
            X=np.asarray(X)
            p=np.clip(X[:,0],0,1)
            return np.stack((1-p,p),axis=1)
    specs=[{'type':'float','low':0.,'high':1.},{'type':'boolean','low':0.,'high':1.}]
    curve=arm_curve(Model(),np.array([.8,0.]),specs,0,.5)
    assert curve['1:5']['success']==1 and 1<curve['1:5']['queries']<=5
    print('Synthetic method-runner self-check passed; no dataset files opened.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--self-check',action='store_true',help='Synthetic check only; opens no dataset')
    parser.add_argument('--ethics-record',type=Path,help='Local record of supervisor acceptance covering this PoC and local processing')
    args=parser.parse_args()
    if args.self_check:
        self_check();return
    if args.ethics_record is None:
        parser.error('--ethics-record is required for a real method-validation run')
    ethics=json.loads(args.ethics_record.read_text())
    if not(ethics.get('supervisor_accepted_class_1_for_this_poc') and ethics.get('local_dataset_processing_permitted')):
        raise ValueError('The supplied ethics record does not cover this method-validation run')
    version_checks()
    protocol=json.loads((ROOT/'configs/experiment_protocol_v3.json').read_text())
    attack=json.loads((ROOT/'configs/attack_pilot_v1.json').read_text())
    baseline=json.loads((ROOT/'data/manifests/compphish_v4_baselines.json').read_text())
    manifest=json.loads((ROOT/'data/manifests/compphish_v4_feature_matrix.json').read_text())
    registry=json.loads((ROOT/'data/manifests/compphish_v4_feature_registry.json').read_text())
    if protocol['final_access_allowed'] is not False or protocol['confirmatory_knowledge']!=['K0']:
        raise ValueError('Unexpected final access or knowledge protocol')
    if protocol['confirmatory_budget']!={'changed_coordinates':1,'total_binary_queries':5}:
        raise ValueError('Confirmatory budget differs from frozen pilot')
    if sha256(ROOT/'scripts/run_step8_development_pilot.py')!=attack['script_sha256']:
        raise ValueError('Frozen Step 8 pilot script hash differs')
    matrix=ROOT/'data/processed/compphish_v4_feature_matrix.csv'
    if sha256(matrix)!=baseline['matrix_sha256'] or sha256(matrix)!=manifest['output_sha256']:
        raise ValueError('Feature matrix hash differs')
    names=[f['name'] for f in registry['features']]
    if names!=manifest['feature_columns']:raise ValueError('Feature order mismatch')
    rows={'train':[],'method_validation':[]}
    with matrix.open(newline='',encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if row['split'] in rows and row['included_primary']=='1':rows[row['split']].append(row)
    if len(rows['train'])!=9214 or len(rows['method_validation'])!=1535:
        raise ValueError('Unexpected train/method row counts')
    factual=audit_source_facts(registry,rows['method_validation'])
    if factual['failure_count']:raise ValueError('Method factual audit failed')
    specs,X_train=grammar(rows['train'],registry)
    if specs!=attack['grammar']['features']:raise ValueError('Train-derived grammar differs from pilot')
    X=np.array([[float(r[n]) for n in names] for r in rows['method_validation']])
    y=np.array([int(r['label']) for r in rows['method_validation']])
    references=np.array([float(np.median(X_train[:,i])) if s['type']!='boolean' else float(np.bincount(X_train[:,i].astype(int)).argmax()) for i,s in enumerate(specs)])
    families=sorted({s['family'] for s in specs})
    family_indices={family:[i for i,s in enumerate(specs) if s['family']==family] for family in families}
    key='1:5';model_summaries={};selected_log=[]
    for model_name in ('logistic_regression','gradient_boosting'):
        frozen=protocol['frozen_models_and_thresholds'][model_name]
        model_path=ROOT/'data/processed/models'/f'{model_name}.joblib'
        if sha256(model_path)!=frozen['model_sha256']:raise ValueError('Frozen model hash mismatch')
        model=joblib.load(model_path)
        threshold=frozen['threshold'];scores=model.predict_proba(X)[:,1]
        starts=[i for i in range(len(X)) if y[i]==1 and scores[i]>=threshold]
        log=[]
        for i in starts:
            row=rows['method_validation'][i];x=X[i]
            family=families[int(hashlib.sha256(f"{protocol['seed']}:{row['serial_number']}".encode()).hexdigest(),16)%len(families)]
            s=family_indices[family][0]
            eligible=[]
            for j in range(len(specs)):
                if x[j]==references[j]:continue
                z=x.copy();z[j]=references[j]
                reduction=scores[i]-model.predict_proba(z.reshape(1,-1))[0,1]
                if reduction>1e-12:eligible.append((j,reduction))
            matching=[a for a in eligible if a[0] in family_indices[family] and a[0]!=s]
            m=max(matching,key=lambda a:(a[1],-a[0]))[0] if matching else None
            v_result=arm_curve(model,x,specs,None,threshold)[key]
            s_result=arm_curve(model,x,specs,s,threshold)[key]
            m_result=arm_curve(model,x,specs,m,threshold)[key] if m is not None else None
            for result in (v_result,s_result,m_result):
                if result and not(1<=result['queries']<=5):raise ValueError('Query accounting exceeds frozen cap')
            record={'model':model_name,'serial_number':row['serial_number'],'group_id':row['group_id'],
                'preassigned_family':family,'S_feature':names[s],'M_family_feature':names[m] if m is not None else '',
                'V_success':v_result['success'],'V_queries':v_result['queries'],
                'S_success':s_result['success'],'S_queries':s_result['queries'],
                'M_family_success':m_result['success'] if m_result else '',
                'M_family_queries':m_result['queries'] if m_result else ''}
            log.append(record);selected_log.append(record)
        matched=[r for r in log if r['M_family_success']!='']
        interval=group_interval(matched,protocol['bootstrap']['seed']+(0 if model_name=='logistic_regression' else 1))
        model_summaries[model_name]={'initially_detected_phishing':len(starts),'phishing_total':int(sum(y)),
            'matched_rows':len(matched),'matched_groups':len({r['group_id'] for r in matched}),
            'matched_V_rate':sum(r['V_success'] for r in matched)/len(matched) if matched else None,
            'matched_S_rate':sum(r['S_success'] for r in matched)/len(matched) if matched else None,
            'matched_M_family_rate':sum(r['M_family_success'] for r in matched)/len(matched) if matched else None,
            'paired_M_minus_S':sum(r['M_family_success']-r['S_success'] for r in matched)/len(matched) if matched else None,
            'paired_cluster_bootstrap_97_5':interval,
            'discordance':dict(Counter(r['M_family_success']-r['S_success'] for r in matched))}
    log_path=ROOT/'data/processed/step10_method_validation_log.csv'
    with log_path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(selected_log[0]),lineterminator='\n');writer.writeheader();writer.writerows(selected_log)
    result={'stage':'Step 10 frozen method-validation implementation check','method_split_only':True,
        'factual_audit':factual,'budget':protocol['confirmatory_budget'],'models':model_summaries,
        'method_validation_passed':True,'final_split_evaluated':False,
        'protocol_sha256':sha256(ROOT/'configs/experiment_protocol_v3.json'),
        'attack_script_sha256':attack['script_sha256'],'matrix_sha256':baseline['matrix_sha256'],
        'local_log_path':str(log_path.relative_to(ROOT)),'local_log_sha256':sha256(log_path),
        'ethics_status':'User reports supervisor accepted Class 1 for this PoC and local dataset processing; declaration not independently inspected.'}
    out=ROOT/'data/manifests/compphish_v4_method_validation.json'
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'factual_checks':factual['feature_checks'],'method_validation_passed':True,'models':model_summaries},indent=2))

if __name__=='__main__':main()
