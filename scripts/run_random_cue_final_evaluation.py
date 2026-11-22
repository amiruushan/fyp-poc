#!/usr/bin/env python3
"""One-time evaluation on the hash-frozen reserved test groups."""
import csv,hashlib,json,math,random
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np,joblib
from sklearn.metrics import average_precision_score,roc_auc_score,precision_score,recall_score
R=Path(__file__).resolve().parents[1];OUT=R/'data/manifests/compphish_v4_random_cue_final_results.json';SEED=20261124;BOOT=20261123;BUDGETS=(5,10,20,40)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def options(x,j,features,low,high):
 vals=[1.-x[j]] if features[j]['type']=='boolean' else [low[j],high[j]]
 return [v for v in vals if v!=x[j]]
def run(model,x,priority,features,low,high,threshold,q):
 order=list(range(len(features)))
 if priority is not None:order=[priority]+[j for j in order if j!=priority]
 used=1
 for j in order:
  for v in options(x,j,features,low,high):
   if used>=q:return 0,used
   z=x.copy();z[j]=v;used+=1
   if model.predict_proba(z.reshape(1,-1))[0,1]<threshold:return 1,used
 return 0,used
def ci(delta,groups,seed):
 by=defaultdict(list)
 for d,g in zip(delta,groups):by[g].append(int(d))
 ids=sorted(by);sums=np.array([sum(by[g]) for g in ids]);sizes=np.array([len(by[g]) for g in ids]);rng=np.random.default_rng(seed);idx=rng.integers(0,len(ids),(10000,len(ids)));draw=sums[idx].sum(1)/sizes[idx].sum(1);return [float(x) for x in np.quantile(draw,[.0125,.9875])]
def main():
 if OUT.exists():raise FileExistsError('Refuse to rerun/overwrite frozen new test results')
 freeze=json.loads((R/'data/manifests/compphish_v4_random_cue_freeze.json').read_text());cfg=R/'configs/random_cue_evaluation_frozen_v2.json';sp=R/'data/manifests/compphish_v4_random_cue_splits.csv'
 if freeze['status']!='frozen; test not evaluated' or sha(cfg)!=freeze['protocol_sha256'] or sha(sp)!=freeze['split_sha256']:raise ValueError('Frozen protocol or split hash mismatch')
 if sha(R/'data/manifests/compphish_v4_splits.csv')!=freeze['original_split_sha256'] or sha(Path(__file__))!=freeze['final_evaluator_sha256']:
  raise ValueError('Original split or final evaluator differs from the frozen artifacts')
 for path,key in [(R/'data/manifests/compphish_v4_feature_registry.json','registry_sha256'),(R/'data/manifests/compphish_v4_feature_matrix.json','matrix_manifest_sha256'),(R/'data/processed/compphish_v4_feature_matrix.csv','matrix_sha256'),(R/'data/manifests/compphish_v4_random_cue_development_pilot.json','pilot_sha256')]:
  if sha(path)!=freeze[key]:raise ValueError('Frozen input changed: '+str(path))
 memberships={r['serial_number']:r for r in csv.DictReader(sp.open())}; src={r['serial_number']:r for r in csv.DictReader((R/'data/manifests/compphish_v4_splits.csv').open())}
 testids={r['group_id'] for r in memberships.values() if r['new_split']=='test'}
 test_serials={serial for serial,r in memberships.items() if r['new_split']=='test'}
 if len(testids)!=1232 or any(src[s]['split']!='train' for s in test_serials):raise ValueError('Test groups overlap earlier evaluated partitions')
 reg=json.loads((R/'data/manifests/compphish_v4_feature_registry.json').read_text());features=reg['features'];names=[f['name'] for f in features]
 train=[];dev=[];test=[]
 for r in csv.DictReader((R/'data/processed/compphish_v4_feature_matrix.csv').open()):
  m=memberships.get(r['serial_number'])
  if not m:continue
  if m['new_split']=='train':train.append(r)
  elif m['new_split']=='development':dev.append(r)
  else:test.append(r)
 if len(train)!=8108 or len(dev)!=5405 or len(test)!=1842:raise ValueError('Split counts differ from frozen counts')
 Xtr=np.array([[float(r[n]) for n in names] for r in train]);low=np.quantile(Xtr,.05,axis=0);high=np.quantile(Xtr,.95,axis=0)
 for i,f in enumerate(features):
  if f['type'] in ('integer','boolean'):low[i]=math.ceil(low[i]);high[i]=math.floor(high[i])
  if f['type']=='boolean':low[i]=0;high[i]=1
 families=sorted({f['family'] for f in features});fi={f:[i for i,x in enumerate(features) if x['family']==f] for f in families};refs=np.array([np.median(Xtr[:,i]) if f['type']!='boolean' else Counter(Xtr[:,i].astype(int)).most_common(1)[0][0] for i,f in enumerate(features)])
 out={'stage':'one-time fresh-group-holdout evaluation','protocol_sha256':sha(cfg),'split_sha256':sha(sp),'freeze_manifest_sha256':sha(R/'data/manifests/compphish_v4_random_cue_freeze.json'),'test_groups':len(testids),'test_rows':len(test),'budget_grid':list(BUDGETS),'models':{}}
 for mi,name in enumerate(('logistic_regression','gradient_boosting')):
  fm=freeze['models'][name];model_path=R/fm['model_path']
  if sha(model_path)!=fm['model_sha256']:raise ValueError('Frozen model hash mismatch: '+name)
  model=joblib.load(model_path);X=np.array([[float(r[n]) for n in names] for r in test]);y=np.array([int(r['label']) for r in test]);scores=model.predict_proba(X)[:,1];thr=fm['threshold'];pred=scores>=thr
  starts=[i for i in range(len(y)) if y[i]==1 and pred[i]];records=[]
  for i in starts:
   row=test[i];fam=families[int(hashlib.sha256(f"{SEED}:{row['serial_number']}".encode()).hexdigest(),16)%len(families)];family=fi[fam];pool=[j for j in family if X[i,j]!=refs[j] and options(X[i],j,features,low,high)]
   if not pool:continue
   reductions={}
   for j in pool:
    z=X[i].copy();z[j]=refs[j];red=scores[i]-model.predict_proba(z.reshape(1,-1))[0,1]
    if red>1e-12:reductions[j]=red
   if not reductions:continue
   m=max(reductions,key=lambda j:(reductions[j],-j));rpool=[j for j in pool if j!=m]
   if not rpool:continue
   rng=random.Random(SEED+int(hashlib.sha256(row['serial_number'].encode()).hexdigest()[:16],16));randomj=rng.choice(rpool)
   records.append({'i':i,'group':memberships[row['serial_number']]['group_id'],'F':family[0],'R':randomj,'M':m})
  if not records:raise ValueError('No eligible matched test rows')
  vals={q:{a:[] for a in ('F','R','M')} for q in BUDGETS};costs={q:{a:[] for a in ('F','R','M')} for q in BUDGETS}
  for rec in records:
   for q in BUDGETS:
    for arm in ('F','R','M'):
     success,cost=run(model,X[rec['i']],rec[arm],features,low,high,thr,q);vals[q][arm].append(success);costs[q][arm].append(cost)
  primary={a:np.array(vals[5][a]) for a in ('F','R','M')};groups=[x['group'] for x in records];diffs={}
  for a,b in [('M','R'),('M','F')]:
   d=primary[a]-primary[b];diffs[a+'-'+b]={'difference':float(d.mean()),'interval_97_5':[float(x) for x in ci(d,groups,BOOT+mi)],'discordant_positive':int(np.sum(d==1)),'discordant_negative':int(np.sum(d==-1))}
  subset=[test[i] for i in starts]
  out['models'][name]={'detector':{'threshold':thr,'FPR':float(np.mean(pred[y==0])),'false_positives':int(np.sum(pred[y==0])),'benign':int(np.sum(y==0)),'recall':float(np.mean(pred[y==1])),'true_positives':int(np.sum(pred[y==1])),'phishing':int(np.sum(y==1)),'precision':float(precision_score(y,pred)),'roc_auc':float(roc_auc_score(y,scores)),'average_precision':float(average_precision_score(y,scores))},'initially_detected_phishing':len(starts),'matched_rows':len(records),'matched_groups':len(set(groups)),'coverage':len(records)/len(starts),'rates_by_query_budget':{str(q):{a:float(np.mean(vals[q][a])) for a in ('F','R','M')} for q in BUDGETS},'mean_queries_at_5':{a:float(np.mean(costs[5][a])) for a in ('F','R','M')},'paired_differences_at_5':diffs}
 out['test_opened_once']=True;OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
