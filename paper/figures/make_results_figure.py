"""Render the frozen final matched-cue rates and paired intervals."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[2]
results = json.loads((root / 'data/manifests/compphish_v4_final_results.json').read_text())
models = [('logistic_regression', 'Logistic regression'), ('gradient_boosting', 'Gradient boosting')]
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.8, 2.7), gridspec_kw={'width_ratios': [1.28, 1]})
colors = {'V': '#7a8793', 'S': '#1f77b4', 'M_family': '#c44e52'}
for row, (key, label) in enumerate(models):
    m = results['models'][key]
    y = 1 - row
    for j, arm in enumerate(('V', 'S', 'M_family')):
        ax1.barh(y + (j-1)*0.22, m['matched_rates'][arm]*100, height=0.18,
                 color=colors[arm], label=arm if row == 0 else None)
    lo, hi = m['paired_group_bootstrap_97_5']
    delta = m['paired_M_family_minus_S']
    ax2.errorbar(delta*100, y, xerr=[[100*(delta-lo)], [100*(hi-delta)]],
                 fmt='o', color='#303030', capsize=4, markersize=5)
    ax2.annotate(f'n={m["matched_rows"]}, groups={m["matched_groups"]}',
                 (delta*100, y), xytext=(0, 12), textcoords='offset points',
                 ha='center', fontsize=8)
ax1.set_yticks([1, 0], [v for _,v in models]); ax1.set_xlim(0, 100)
ax1.set_xlabel('Bypass among matched starts (%)')
ax1.legend(ncol=3, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.23), fontsize=8)
ax1.spines[['top','right']].set_visible(False)
ax2.set_yticks([1,0], ['', '']); ax2.set_xlim(0, 75)
ax2.set_xlabel('Paired M-family minus S (points)')
ax2.axvline(0, color='#888888', linewidth=.8)
ax2.spines[['top','right']].set_visible(False)
fig.tight_layout(pad=1.1)
out = Path(__file__).with_name('frozen_matched_results.pdf')
fig.savefig(out, bbox_inches='tight')
print(out)
