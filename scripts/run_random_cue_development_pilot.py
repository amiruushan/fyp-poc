#!/usr/bin/env python3
"""Fit fresh detectors and evaluate cue selectors on new development groups only."""
import csv, hashlib, itertools, json, math, random
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
ROOT=Path(__file__).resolve().parents[1]
MATRIX=ROOT/'data/processed/compphish_v4_feature_matrix.csv'
SPLIT=ROOT/'data/manifests/compphish_v4_random_cue_splits.csv'
REG=ROOT/'data/manifests/compphish_v4_feature_registry.json'
SEED=20261124
BUDGETS=(5,10,20,40)
def load():
 split={r['serial_number']:r for r in csv.DictReader(SPLIT.open())}
 reg=json.loads(REG.read_text());features=reg['features'];names=[f['name'] for f in features]
 data={'train':[],'development':[]}
 for r in csv.DictReader(MATRIX.open()):
  s=split.get(r['serial_number'])
  if s and s['new_split'] in data and r['included_primary']=='1':data[s['new_split']].append({**r,'new_group':s['group_id']})
 return features,names,data
def make_models(seed):
 from sklearn.base import clone
 specs=[]
 for c in [.01,.1,1,10]: specs.append(('logistic_regression',{'C':c}))
 for d in [1,2,3]:
  for n in [100,200]: specs.append(('gradient_boosting',{'max_depth':d,'n_estimators':n}))
 return specs
def estimator(name,p):
 if name=='logistic_regression': return make_pipeline(StandardScaler(),LogisticRegression(C=p['C'],penalty='l2',solver='lbfgs',max_iter=2000,random_state=SEED))
 return GradientBoostingClassifier(max_depth=p['max_depth'],n_estimators=p['n_estimators'],learning_rate=.05,min_samples_leaf=20,subsample=1.0,random_state=SEED)
def choose_threshold(y,scores,target=.02):
 neg=np.sort(scores[y==0]); candidates=[float(np.nextafter(neg[-1],np.inf))]
 candidates.extend(float(v) for v in np.unique(neg[::-1]))
 valid=[]
 for t in candidates:
  fpr=float(np.mean(scores[y==0]>=t))
  if fpr<=target:valid.append((t,fpr))
 return min(valid,key=lambda z:z[0])
def options(x,j,features,low,high):
 spec=features[j]
 if spec['type']=='boolean': vals=[1.-x[j]]
 else: vals=[low[j],high[j]]
 return [v for v in vals if v!=x[j]]
def attack(model,x,priority,features,low,high,threshold,budget):
 order=list(range(len(features)))
 if priority is not None: order=[priority]+[i for i in order if i!=priority]
 used=1
 for j in order:
  for value in options(x,j,features,low,high):
   if used>=budget:return 0,used
   z=x.copy();z[j]=value;used+=1
   if model.predict_proba(z.reshape(1,-1))[0,1]<threshold:return 1,used
 return 0,used
def main():
 features,names,data=load();train=data['train'];dev=data['development']
 Xtr=np.array([[float(r[n]) for n in names] for r in train]);ytr=np.array([int(r['label']) for r in train])
 X=np.array([[float(r[n]) for n in names] for r in dev]);y=np.array([int(r['label']) for r in dev])
 if not train or not dev:raise ValueError('New train/development split is empty')
 if len(train)+len(dev)!=13513:raise ValueError('Unexpected non-test row count; possible test leakage')
 groups=np.array([r['new_group'] for r in dev])
 low=np.quantile(Xtr,.05,axis=0);high=np.quantile(Xtr,.95,axis=0)
 for i,f in enumerate(features):
  if f['type'] in ('integer','boolean'):low[i]=math.ceil(low[i]);high[i]=math.floor(high[i])
  if f['type']=='boolean':low[i]=0;high[i]=1
 families=sorted({f['family'] for f in features}); fi={fam:[i for i,f in enumerate(features) if f['family']==fam] for fam in families}
 refs=np.array([np.median(Xtr[:,i]) if f['type']!='boolean' else Counter(Xtr[:,i].astype(int)).most_common(1)[0][0] for i,f in enumerate(features)],float)
 split_stats=json.loads((ROOT/'data/manifests/compphish_v4_random_cue_split_stats.json').read_text())
 result={'scope':'development-only cue-selector pilot; test partition was not loaded','random_seed':SEED,'split_membership_sha256':split_stats['membership_sha256'],'split_counts':split_stats['splits'],'budget_grid':list(BUDGETS),'models':{}}
 for name in ['logistic_regression','gradient_boosting']:
  candidates=[]
  for modelname,params in make_models(SEED):
   if modelname!=name:continue
   model=estimator(name,params).fit(Xtr,ytr);score=model.predict_proba(X)[:,1]
   ap=float(__import__('sklearn.metrics').metrics.average_precision_score(y,score))
   candidates.append((ap,params,model,score))
  ap,params,model,scores=max(candidates,key=lambda a:a[0])
  threshold,fpr=choose_threshold(y,scores)
  starts=[i for i in range(len(y)) if y[i]==1 and scores[i]>=threshold]
  rec=[]
  for i in starts:
   fam=families[int(hashlib.sha256(f'{SEED}:{dev[i]["serial_number"]}'.encode()).hexdigest(),16)%len(families)]
   family=fi[fam];first=family[0]
   pool=[j for j in family if X[i,j]!=refs[j] and options(X[i],j,features,low,high)]
   if not pool:continue
   eligible=[]
   for j in pool:
    z=X[i].copy();z[j]=refs[j]
    reduction=scores[i]-model.predict_proba(z.reshape(1,-1))[0,1]
    if reduction>1e-12:eligible.append(j)
   if not eligible:continue
   m=max(eligible,key=lambda j:(scores[i]-model.predict_proba(np.where(np.arange(len(names))==j,refs,X[i]).reshape(1,-1))[0,1],-j))
   random_pool=[j for j in pool if j!=m]
   if not random_pool:continue
   rr=random.Random(SEED+int(hashlib.sha256(dev[i]['serial_number'].encode()).hexdigest()[:16],16))
   rand=rr.choice(random_pool)
   rec.append({'i':i,'group':groups[i],'F':first,'R':rand,'M':m,'collision_MR':rand==m})
  arms=['F','R','M']; curves={}
  for q in BUDGETS:
   vals={a:[] for a in arms}
   for row in rec:
    for a in arms:
     vals[a].append(attack(model,X[row['i']],row[a],features,low,high,threshold,q)[0])
   curves[str(q)]={a:float(np.mean(v)) for a,v in vals.items()}
  primary={a:[] for a in arms}
  for row in rec:
   for a in arms: primary[a].append(attack(model,X[row['i']],row[a],features,low,high,threshold,5)[0])
  diffs={}
  for a,b in [('M','R'),('M','F')]:
   delta=np.array(primary[a])-np.array(primary[b]); by=defaultdict(list)
   for row,d in zip(rec,delta):by[row['group']].append(int(d))
   keys=list(by);sums=np.array([sum(by[k]) for k in keys]);sizes=np.array([len(by[k]) for k in keys]);rng=np.random.default_rng(SEED+(0 if name=='logistic_regression' else 1));idx=rng.integers(0,len(keys),(10000,len(keys)));draw=sums[idx].sum(1)/sizes[idx].sum(1)
   diffs[a+'-'+b]={'difference':float(delta.mean()),'adjusted_97_5_interval':[float(v) for v in np.quantile(draw,[.0125,.9875])],'discordant_positive':int(np.sum(delta==1)),'discordant_negative':int(np.sum(delta==-1))}
  result['models'][name]={'selected_params':params,'development_average_precision':ap,'threshold':threshold,'development_benign_fpr':fpr,'initially_detected_phishing':len(starts),'matched_rows':len(rec),'matched_groups':len({r['group'] for r in rec}),'coverage':len(rec)/len(starts) if starts else 0,'M_equals_R_fraction':float(np.mean([r['collision_MR'] for r in rec])),'rates_by_query_budget':curves,'paired_differences':diffs}
 out=ROOT/'data/manifests/compphish_v4_random_cue_development_pilot.json';out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
