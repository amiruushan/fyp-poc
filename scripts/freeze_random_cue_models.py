#!/usr/bin/env python3
"""Fit selected fresh models on new train groups and freeze thresholds/artifacts."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score
import joblib
R=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 split={r['serial_number']:r for r in csv.DictReader((R/'data/manifests/compphish_v4_random_cue_splits.csv').open())}
 reg=json.loads((R/'data/manifests/compphish_v4_feature_registry.json').read_text());names=[f['name'] for f in reg['features']]
 rows={'train':[],'development':[]}
 for r in csv.DictReader((R/'data/processed/compphish_v4_feature_matrix.csv').open()):
  s=split.get(r['serial_number']);
  if s and s['new_split'] in rows: rows[s['new_split']].append(r)
 if len(rows['train'])!=8108 or len(rows['development'])!=5405: raise ValueError('Fresh train/dev row counts differ from the recorded allocation')
 Xtr=np.array([[float(r[n]) for n in names] for r in rows['train']]);ytr=np.array([int(r['label']) for r in rows['train']]);X=np.array([[float(r[n]) for n in names] for r in rows['development']]);y=np.array([int(r['label']) for r in rows['development']])
 specs={'logistic_regression':(make_pipeline(StandardScaler(),LogisticRegression(C=10,solver='lbfgs',max_iter=2000,random_state=20261124)),{'C':10}),'gradient_boosting':(GradientBoostingClassifier(max_depth=3,n_estimators=200,learning_rate=.05,min_samples_leaf=20,subsample=1.0,random_state=20261124),{'max_depth':3,'n_estimators':200})}
 out=R/'data/processed/random_cue_models';out.mkdir(parents=True,exist_ok=True);summary={}
 for name,(model,params) in specs.items():
  model.fit(Xtr,ytr);scores=model.predict_proba(X)[:,1];neg=np.sort(scores[y==0]);candidates=[float(np.nextafter(neg[-1],np.inf)),*map(float,np.unique(neg[::-1]))];threshold=min(t for t in candidates if np.mean(scores[y==0]>=t)<=.02);fpr=float(np.mean(scores[y==0]>=threshold));ap=float(average_precision_score(y,scores));path=out/(name+'.joblib');joblib.dump(model,path)
  summary[name]={'params':params,'threshold':threshold,'development_fpr':fpr,'development_recall':float(np.mean(scores[y==1]>=threshold)),'development_average_precision':ap,'model_path':str(path.relative_to(R)),'model_sha256':sha(path)}
 pilot=json.loads((R/'data/manifests/compphish_v4_random_cue_development_pilot.json').read_text())
 for name in specs:
  if abs(summary[name]['threshold']-pilot['models'][name]['threshold'])>1e-12:raise ValueError('Threshold differs from development pilot')
  if abs(summary[name]['development_average_precision']-pilot['models'][name]['development_average_precision'])>1e-12:raise ValueError('AP differs from development pilot')
 cfg=json.loads((R/'configs/random_cue_evaluation_frozen_v2.json').read_text());cfg['split_sha256']=sha(R/'data/manifests/compphish_v4_random_cue_splits.csv');(R/'configs/random_cue_evaluation_frozen_v2.json').write_text(json.dumps(cfg,indent=2)+'\n')
 manifest={'status':'frozen; test not evaluated','split_sha256':cfg['split_sha256'],'original_split_sha256':sha(R/'data/manifests/compphish_v4_splits.csv'),'protocol_sha256':sha(R/'configs/random_cue_evaluation_frozen_v2.json'),'registry_sha256':sha(R/'data/manifests/compphish_v4_feature_registry.json'),'matrix_manifest_sha256':sha(R/'data/manifests/compphish_v4_feature_matrix.json'),'matrix_sha256':sha(R/'data/processed/compphish_v4_feature_matrix.csv'),'pilot_sha256':sha(R/'data/manifests/compphish_v4_random_cue_development_pilot.json'),'models':summary,'test_group_count':1232,'train_rows':len(rows['train']),'development_rows':len(rows['development']),'freeze_script_sha256':sha(Path(__file__)),'final_evaluator_sha256':sha(R/'scripts/run_random_cue_final_evaluation.py')}
 (R/'data/manifests/compphish_v4_random_cue_freeze.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n');print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
