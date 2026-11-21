#!/usr/bin/env python3
"""Offline, bounded feature-space cue/attack pilot on development rows only."""
from __future__ import annotations
import csv, hashlib, itertools, json, math, zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
import joblib, numpy as np
from train_baseline_detectors import sha256
from validate_feature_registry import independent_values, version_checks
import tldextract

ROOT=Path(__file__).resolve().parents[1]
BUDGETS=(5,10,20,40)
CHANGE_LIMITS=(1,2,3,4,5)
SAMPLE_TOL=1e-9


def load_inputs():
    reg=json.loads((ROOT/'data/manifests/compphish_v4_feature_registry.json').read_text())
    protocol=json.loads((ROOT/'configs/experiment_protocol_v2.json').read_text())
    baseline=json.loads((ROOT/'data/manifests/compphish_v4_baselines.json').read_text())
    manifest=json.loads((ROOT/'data/manifests/compphish_v4_feature_matrix.json').read_text())
    matrix=ROOT/'data/processed/compphish_v4_feature_matrix.csv'
    if sha256(matrix)!=manifest['output_sha256'] or sha256(matrix)!=baseline['matrix_sha256']:
        raise ValueError('Feature matrix hash mismatch')
    if protocol['final_access_allowed'] is not False:
        raise ValueError('Final split is not sealed')
    names=[f['name'] for f in reg['features']]
    if names!=manifest['feature_columns']:
        raise ValueError('Feature registry mismatch')
    rows={'train':[],'development':[]}
    with matrix.open(newline='',encoding='utf-8') as stream:
        for row in csv.DictReader(stream):
            if row['split'] in rows and row['included_primary']=='1':
                rows[row['split']].append(row)
    return reg,protocol,baseline,rows


def audit_source_facts(reg,dev):
    wanted={r['serial_number'] for r in dev}
    by_serial={r['serial_number']:r for r in dev}
    extractor=tldextract.TLDExtract(cache_dir=None,suffix_list_urls=(),fallback_to_snapshot=True,include_psl_private_domains=False)
    observed={}
    with zipfile.ZipFile(ROOT/'data/raw/compphish_v4/All_HTML.zip') as archive:
        for info in archive.infolist():
            serial=PurePosixPath(info.filename).stem
            if serial in wanted:
                row=by_serial[serial]
                content=archive.read(info)
                if hashlib.sha256(content).hexdigest()!=row['html_sha256']:
                    raise ValueError(f'HTML hash mismatch for {serial}')
                observed[serial]=independent_values(row['url'],content.decode('utf-8'),extractor)
    if set(observed)!=wanted:
        raise ValueError('Missing HTML for factual audit')
    failures=Counter()
    for serial,row in by_serial.items():
        for feature in reg['features']:
            name=feature['name']
            if abs(float(row[name])-float(observed[serial][name]))>SAMPLE_TOL:
                failures[name]+=1
    return {'sample_rows':len(wanted),'feature_checks':len(wanted)*len(reg['features']),
            'failure_count':sum(failures.values()),'failures_by_feature':dict(failures),
            'method':'Independent recomputation of every development row against archived URL/HTML and Step 4 matrix; pinned offline parser'}


def grammar(train,reg):
    names=[f['name'] for f in reg['features']]
    X=np.array([[float(r[n]) for n in names] for r in train])
    specs=[]
    for i,f in enumerate(reg['features']):
        column=X[:,i]
        low,high=np.quantile(column,[.05,.95])
        if f['type'] in ('integer','boolean'):
            low,high=math.ceil(low),math.floor(high)
        if f['type']=='boolean':
            low,high=0,1
        specs.append({'name':f['name'],'type':f['type'],'low':float(low),'high':float(high),
                      'family':f['family']})
    return specs,X


def options(x,spec):
    if spec['type']=='boolean':
        values=[1.0-x if x in (0,1) else x]
    else:
        values=[spec['low'],spec['high']]
    return [v for v in values if v!=x and spec['low']<=v<=spec['high']]


def candidates(x,specs,priority,max_queries):
    indices=list(range(len(specs)))
    if priority is not None:
        indices=[priority]+[i for i in indices if i!=priority]
    opt={i:options(x[i],specs[i]) for i in indices}
    proposed=[];changes=[];seen=set()
    for size in CHANGE_LIMITS:
        for combo in itertools.combinations(indices,size):
            if any(not opt[i] for i in combo): continue
            for values in itertools.product(*(opt[i] for i in combo)):
                y=x.copy()
                for i,value in zip(combo,values): y[i]=value
                key=y.tobytes()
                if key in seen:continue
                seen.add(key);proposed.append(y);changes.append(size)
                if len(proposed)==max_queries-1:return np.array(proposed),changes
    return np.array(proposed),changes


def arm_curve(model,x,specs,priority,threshold):
    vectors,changes=candidates(x,specs,priority,max(BUDGETS))
    if len(vectors): verdicts=model.predict_proba(vectors)[:,1]<threshold
    else: verdicts=[]
    curve={}
    for limit,q in itertools.product(CHANGE_LIMITS,BUDGETS):
        used=0;success=False;cost=1
        for flip,nchanges in zip(verdicts,changes):
            if nchanges>limit:continue
            if used==q-1:break
            used+=1;cost+=1
            if flip:success=True;break
        curve[f'{limit}:{q}']={'success':int(success),'queries':cost}
    return curve


def clustered_pilot_interval(records,key,seed):
    by_group={}
    for record in records:
        by_group.setdefault(record['group'],[]).append(record['M_family'][key]['success']-record['S'][key]['success'])
    groups=sorted(by_group)
    if not groups:return None
    rng=np.random.default_rng(seed)
    draws=[]
    for _ in range(2000):
        sampled=rng.integers(0,len(groups),len(groups))
        values=[value for index in sampled for value in by_group[groups[index]]]
        draws.append(sum(values)/len(values))
    return [float(v) for v in np.quantile(draws,[.025,.975])]


def main():
    version_checks()
    reg,protocol,baseline,rows=load_inputs()
    audit=audit_source_facts(reg,rows['development'])
    if audit['failure_count']:
        raise ValueError(f"Factual audit failed: {audit['failures_by_feature']}")
    specs,X_train=grammar(rows['train'],reg)
    names=[s['name'] for s in specs]
    families=sorted(set(s['family'] for s in specs))
    family_indices={family:[i for i,s in enumerate(specs) if s['family']==family] for family in families}
    references=np.array([float(np.median(X_train[:,i])) if s['type']!='boolean' else float(np.bincount(X_train[:,i].astype(int)).argmax()) for i,s in enumerate(specs)])
    X_dev=np.array([[float(r[n]) for n in names] for r in rows['development']])
    y_dev=np.array([int(r['label']) for r in rows['development']])
    if len(X_dev)!=2303:raise ValueError('Unexpected development count')
    log_path=ROOT/'data/processed/step8_pilot_selected_log.csv'
    summary={'scope':'development only; abstract bounded feature-space relaxation, no website edits',
             'factual_audit':audit,'grammar':{'candidate_values':'train-only 5th and 95th percentiles for numeric; binary toggle; exact baseline vector with up to 5 changed coordinates',
             'features':specs,'dependency_rule':'Independent coordinate changes are an abstract feature-space relaxation; they are not asserted to map to a valid URL or HTML page.',
             'query_accounting':'Initial binary verdict plus each candidate prediction; rejected candidates are skipped and counted separately as invalid proposals, which are zero under this grammar.'},
             'knowledge_conditions':'K0 and K2 are operationally identical in this pilot because the fixed search does not consume semantic definitions; no knowledge interaction is claimed.',
             'budget_grid':{'changes':list(CHANGE_LIMITS),'queries':list(BUDGETS)},'models':{}}
    selected_logs=[]
    for family in ('logistic_regression','gradient_boosting'):
        frozen=protocol['frozen_models_and_thresholds'][family]
        model_path=ROOT/'data/processed/models'/f'{family}.joblib'
        if sha256(model_path)!=frozen['model_sha256']:raise ValueError('Frozen model hash mismatch')
        model=joblib.load(model_path)
        threshold=frozen['threshold']
        start_scores=model.predict_proba(X_dev)[:,1]
        starts=[i for i in range(len(X_dev)) if y_dev[i]==1 and start_scores[i]>=threshold]
        records=[]
        for index in starts:
            x=X_dev[index];row=rows['development'][index]
            selected_family=families[int(hashlib.sha256(f"{protocol['seed']}:{row['serial_number']}".encode()).hexdigest(),16)%len(families)]
            s=family_indices[selected_family][0]
            eligible=[]
            for j in range(len(specs)):
                if x[j]==references[j]:continue
                z=x.copy();z[j]=references[j]
                reduction=start_scores[index]-model.predict_proba(z.reshape(1,-1))[0,1]
                if reduction>1e-12:eligible.append((j,reduction))
            m_global=max(eligible,key=lambda item:(item[1],-item[0]))[0] if eligible else None
            matching=[item for item in eligible if item[0] in family_indices[selected_family] and item[0]!=s]
            m_family=max(matching,key=lambda item:(item[1],-item[0]))[0] if matching else None
            record={'serial':row['serial_number'],'group':row['group_id'],'family':selected_family,
                    's':s,'m_family':m_family,'m_global':m_global,'eligible_count':len(eligible),
                    'V':arm_curve(model,x,specs,None,threshold),
                    'S':arm_curve(model,x,specs,s,threshold),
                    'M_family':arm_curve(model,x,specs,m_family,threshold) if m_family is not None else None,
                    'M_global':arm_curve(model,x,specs,m_global,threshold) if m_global is not None else None}
            records.append(record)
        eligible_records=[r for r in records if r['M_family'] is not None]
        grid=[]
        for changes,q in itertools.product(CHANGE_LIMITS,BUDGETS):
            key=f'{changes}:{q}'
            if eligible_records:
                rates={arm:sum(r[arm][key]['success'] for r in eligible_records)/len(eligible_records) for arm in ('V','S','M_family')}
                pooled=sum(rates.values())/3
            else:rates={arm:None for arm in ('V','S','M_family')};pooled=None
            grid.append({'changes':changes,'queries':q,'eligible_n':len(eligible_records),'pooled_success':pooled,'rates':rates})
        qualifying=[p for p in grid if p['pooled_success'] is not None and .1<=p['pooled_success']<=.9]
        selected=min(qualifying,key=lambda p:(abs(p['pooled_success']-.5),p['changes'],p['queries'])) if qualifying else None
        if selected:
            key=f"{selected['changes']}:{selected['queries']}"
            for r in records:
                log_row={'model':family,'serial_number':r['serial'],'group_id':r['group'],'preassigned_family':r['family'],
                    's_feature':names[r['s']],'m_family_feature':names[r['m_family']] if r['m_family'] is not None else '',
                    'm_global_feature':names[r['m_global']] if r['m_global'] is not None else '',
                    'eligible_cue_count':r['eligible_count']}
                for arm in ('V','S','M_family','M_global'):
                    log_row[arm+'_success']=r[arm][key]['success'] if r[arm] else ''
                    log_row[arm+'_queries']=r[arm][key]['queries'] if r[arm] else ''
                selected_logs.append(log_row)
            all_start_rates={
                'V':sum(r['V'][key]['success'] for r in records)/len(records),
                'S':sum(r['S'][key]['success'] for r in records)/len(records),
                'M_global_with_V_fallback':sum((r['M_global'] or r['V'])[key]['success'] for r in records)/len(records),
            }
            mean_queries={arm:sum((r[arm] or r['V'])[key]['queries'] for r in records)/len(records)
                          for arm in ('V','S','M_family','M_global')}
        else:
            all_start_rates=None;mean_queries=None
        summary['models'][family]={'initially_detected_phishing':len(records),'phishing_total':int(sum(y_dev)),
            'preassigned_family_counts':dict(Counter(r['family'] for r in records)),
            'global_model_cue_count':sum(r['m_global'] is not None for r in records),
            'at_least_two_eligible_model_cues':sum(r['eligible_count']>=2 for r in records),
            'matched_distinct_cue_count':len(eligible_records),
            'matched_distinct_cue_groups':len({r['group'] for r in eligible_records}),
            'matched_exclusion_by_family':dict(Counter(r['family'] for r in records if r['m_family'] is None)),
            'grid':grid,'proposed_operating_point':selected,
            'all_start_rates_at_proposed_point':all_start_rates,
            'all_start_mean_queries_at_proposed_point':mean_queries,
            'selected_paired_difference_M_family_minus_S':(selected['rates']['M_family']-selected['rates']['S']) if selected else None,
            'selected_difference_group_bootstrap_95_pilot':clustered_pilot_interval(eligible_records,f"{selected['changes']}:{selected['queries']}",20261124) if selected else None}
    log_path.parent.mkdir(parents=True,exist_ok=True)
    if selected_logs:
        with log_path.open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(selected_logs[0]),lineterminator='\n');writer.writeheader();writer.writerows(selected_logs)
        summary['selected_log_sha256']=sha256(log_path)
    summary['selected_log_path']=str(log_path.relative_to(ROOT))
    out=ROOT/'data/manifests/compphish_v4_step8_pilot.json'
    out.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps({m:{k:v for k,v in x.items() if k in ('initially_detected_phishing','matched_distinct_cue_count','matched_distinct_cue_groups','proposed_operating_point','selected_paired_difference_M_family_minus_S')} for m,x in summary['models'].items()},indent=2))

if __name__=='__main__':main()
