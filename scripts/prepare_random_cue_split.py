#!/usr/bin/env python3
"""Assign only original-train connected groups to a new train/dev/test split."""
import csv, hashlib, json, random
from collections import Counter, defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/manifests/compphish_v4_splits.csv'
OUT=ROOT/'data/manifests/compphish_v4_random_cue_splits.csv'
REPORT=ROOT/'data/manifests/compphish_v4_random_cue_split_stats.json'
SEED=8675309
FRACTIONS={'train':.60,'development':.20,'test':.20}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 rows=list(csv.DictReader(SOURCE.open()))
 pool=[r for r in rows if r['split']=='train' and r['included_primary']=='1']
 groups=defaultdict(list)
 for r in pool: groups[r['group_id']].append(r)
 if len(groups)!=4955 or len(pool)!=9214: raise ValueError('Unexpected eligible pool')
 totals=Counter(r['label'] for r in pool)
 targets={s:{l:totals[l]*f for l in ('0','1')} for s,f in FRACTIONS.items()}
 best=None
 for trial in range(64):
  rng=random.Random(SEED+trial); tie={g:rng.random() for g in groups}
  order=sorted(groups,key=lambda g:(-len(groups[g]),tie[g],g))
  have={s:Counter() for s in FRACTIONS}; assignment={}
  for g in order:
   c=Counter(r['label'] for r in groups[g])
   costs={s:sum((((have[s][l]+c[l]-targets[s][l])/totals[l])**2)-(((have[s][l]-targets[s][l])/totals[l])**2) for l in ('0','1')) for s in FRACTIONS}
   m=min(costs.values()); choices=[s for s in FRACTIONS if abs(costs[s]-m)<1e-15]
   selected=rng.choice(choices); assignment[g]=selected;have[selected].update(c)
  score=sum(((have[s][l]-targets[s][l])/totals[l])**2 for s in FRACTIONS for l in ('0','1'))
  if best is None or score<best[0]: best=(score,trial,assignment)
 assignment=best[2]
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with OUT.open('w',newline='') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['serial_number','group_id','new_split','label'])
  for r in sorted(pool,key=lambda r:(int(r['serial_number']),r['serial_number'])):w.writerow([r['serial_number'],r['group_id'],assignment[r['group_id']],r['label']])
 summary={'status':'group-only candidate split; pilot/test outcomes not evaluated','seed':SEED,'greedy_trials':64,'selected_trial':best[1],'source_split_sha256':sha(SOURCE),'membership_sha256':sha(OUT),'source_pool_groups':len(groups),'source_pool_rows':len(pool),'source_final_groups_excluded':len({r['group_id'] for r in rows if r['split']!='train'}),'splits':{}}
 for s in FRACTIONS:
  gs={g for g,v in groups.items() if assignment[g]==s}; rr=[r for g in gs for r in groups[g]]
  summary['splits'][s]={'groups':len(gs),'rows':len(rr),'phishing':sum(r['label']=='1' for r in rr),'legitimate':sum(r['label']=='0' for r in rr),'mixed_label_groups':sum(len({x['label'] for x in groups[g]})>1 for g in gs)}
 REPORT.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
