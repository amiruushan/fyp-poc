#!/usr/bin/env python3
"""Keep the previously reserved new test groups fixed; repartition all other groups."""
import csv,hashlib,json,random
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/manifests/compphish_v4_splits.csv'; PREVIOUS=ROOT/'data/manifests/compphish_v4_random_cue_splits.csv'
OUT=PREVIOUS; REPORT=ROOT/'data/manifests/compphish_v4_random_cue_split_stats.json'
SEED=8675311; TRIALS=64; FRACTIONS={'train':.60,'development':.40}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 original=list(csv.DictReader(SOURCE.open())); old=list(csv.DictReader(PREVIOUS.open()))
 test_groups={r['group_id'] for r in old if r['new_split']=='test'}
 rows=[r for r in original if r['included_primary']=='1']
 groups=defaultdict(list)
 for r in rows:groups[r['group_id']].append(r)
 if len(test_groups)!=1232 or not test_groups.issubset(groups):raise ValueError('Reserved test group set is missing or changed')
 if any(r['split']!='train' for r in original if r['group_id'] in test_groups):raise ValueError('Test group was not from the previously unevaluated original-train pool')
 remaining={g:v for g,v in groups.items() if g not in test_groups}; total=Counter(r['label'] for v in remaining.values() for r in v)
 target={s:{l:total[l]*f for l in ('0','1')} for s,f in FRACTIONS.items()};best=None
 for trial in range(TRIALS):
  rng=random.Random(SEED+trial);tie={g:rng.random() for g in remaining};order=sorted(remaining,key=lambda g:(-len(remaining[g]),tie[g],g));have={s:Counter() for s in FRACTIONS};ass={}
  for g in order:
   c=Counter(r['label'] for r in remaining[g]);cost={s:sum(((have[s][l]+c[l]-target[s][l])/total[l])**2-((have[s][l]-target[s][l])/total[l])**2 for l in ('0','1')) for s in FRACTIONS};m=min(cost.values());choices=[s for s in FRACTIONS if abs(cost[s]-m)<1e-15];s=rng.choice(choices);ass[g]=s;have[s].update(c)
  score=sum(((have[s][l]-target[s][l])/total[l])**2 for s in FRACTIONS for l in ('0','1'))
  if best is None or score<best[0]:best=(score,trial,ass)
 assignment={g:('test' if g in test_groups else best[2][g]) for g in groups}
 with OUT.open('w',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['serial_number','group_id','new_split','label'])
  for r in sorted(rows,key=lambda r:(int(r['serial_number']),r['serial_number'])):w.writerow([r['serial_number'],r['group_id'],assignment[r['group_id']],r['label']])
 report={'status':'revised development allocation; reserved test group IDs preserved; test outcomes not accessed','seed':SEED,'trials':TRIALS,'selected_trial':best[1],'source_split_sha256':sha(SOURCE),'previous_membership_sha256':hashlib.sha256(('\n'.join(sorted(test_groups))).encode()).hexdigest(),'membership_sha256':sha(OUT),'previously_unattacked_pool_groups':len(groups),'reserved_test_groups':len(test_groups),'training_development_pool_groups':len(remaining),'training_development_pool_rows':sum(map(len,remaining.values())),'splits':{}}
 for s in ('train','development','test'):
  gs={g for g in groups if assignment[g]==s};rr=[r for g in gs for r in groups[g]];report['splits'][s]={'groups':len(gs),'rows':len(rr),'phishing':sum(r['label']=='1' for r in rr),'legitimate':sum(r['label']=='0' for r in rr),'mixed_label_groups':sum(len({x['label'] for x in groups[g]})>1 for g in gs)}
 REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
