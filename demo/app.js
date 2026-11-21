(() => {
  const data = window.COMP_PHISH_DEMO;
  if (!data || !data.models) {
    document.querySelector('main').innerHTML = '<div class="shell"><h1>Demo data is missing</h1><p>Run <code>python3 demo/reproduce.py</code> from the repository root.</p></div>';
    return;
  }
  const labels = {logistic_regression: 'Logistic regression', gradient_boosting: 'Boosted trees'};
  const color = {V: '#8ea7b0', S: '#e3b778', M_family: '#63e1cb'};
  const pct = (v, digits = 1) => `${(v * 100).toFixed(digits)}%`;
  const points = (v) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)} pts`;
  const safe = (number) => Number.isFinite(number) ? number : 0;

  function resultCard(name) {
    const m = data.models[name];
    const delta = m.matched_rates.M_family - m.matched_rates.S;
    const rows = [
      ['V', 'Verdict', m.matched_rates.V],
      ['S', 'Matched fact', m.matched_rates.S],
      ['M_family', 'Model cue', m.matched_rates.M_family]
    ].map(([key, label, value]) => `<div class="rate-row"><span>${label}</span><div class="track"><div class="fill fill-${key === 'M_family' ? 'm' : key.toLowerCase()}" style="width:${safe(value) * 100}%"></div></div><b>${pct(value)}</b></div>`).join('');
    return `<article class="result-card"><div class="result-top"><span class="result-kicker">${name === 'logistic_regression' ? 'LINEAR DETECTOR' : 'TREE DETECTOR'}</span><span class="result-tag">Final result</span></div><h3>${labels[name]}</h3><div class="delta">${points(delta)} <span>M − S</span></div><p class="interval">Adjusted 97.5% interval · ${points(m.interval[0])} to ${points(m.interval[1])}</p><div>${rows}</div><div class="card-bottom"><span>${m.matched_rows} paired starts</span><span>${m.matched_groups} connected groups</span></div></article>`;
  }
  document.getElementById('resultCards').innerHTML = ['logistic_regression', 'gradient_boosting'].map(resultCard).join('');

  const modelButtons = [...document.querySelectorAll('[data-model]')];
  const changesSelect = document.getElementById('changesSelect');
  let selectedModel = 'logistic_regression';
  function chartSVG(curve) {
    const width = 720, height = 310, left = 49, right = 24, top = 14, bottom = 39;
    const x = (q) => left + (q - 5) / 35 * (width - left - right);
    const y = (v) => top + (1 - v) * (height - top - bottom);
    const ticks = [0, .25, .5, .75, 1];
    const grid = ticks.map(t => `<line x1="${left}" y1="${y(t)}" x2="${width-right}" y2="${y(t)}" stroke="#31515d" stroke-dasharray="3 5"/><text x="${left-9}" y="${y(t)+4}" text-anchor="end" fill="#9db8be" font-size="12">${Math.round(t*100)}%</text>`).join('');
    const xTicks = curve.map(p => `<text x="${x(p.total_queries)}" y="${height-9}" text-anchor="middle" fill="#9db8be" font-size="12">${p.total_queries}</text>`).join('');
    const paths = [['V','V_rate'],['S','S_rate'],['M_family','M_family_rate']].map(([name, field]) => {
      const route = curve.map((p,i) => `${i ? 'L' : 'M'} ${x(p.total_queries)} ${y(p[field])}`).join(' ');
      const circles = curve.map(p => `<circle cx="${x(p.total_queries)}" cy="${y(p[field])}" r="5" fill="${color[name]}" stroke="#102d39" stroke-width="2"><title>${name === 'M_family' ? 'Model cue' : name === 'S' ? 'Matched fact' : 'Verdict'}: ${pct(p[field])} at ${p.total_queries} queries</title></circle>`).join('');
      return `<path d="${route}" fill="none" stroke="${color[name]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${circles}`;
    }).join('');
    return `<svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">${grid}${xTicks}${paths}</svg>`;
  }
  function updateExplorer() {
    const limit = Number(changesSelect.value);
    const m = data.models[selectedModel];
    const curve = m.budget_curve.filter(p => p.changed_coordinates === limit).sort((a,b) => a.total_queries - b.total_queries);
    document.getElementById('chartTitle').textContent = `${labels[selectedModel]} · ${limit} ${limit === 1 ? 'coordinate' : 'coordinates'}`;
    document.getElementById('budgetChart').innerHTML = chartSVG(curve);
    document.getElementById('budgetChart').setAttribute('aria-label', `${labels[selectedModel]} with ${limit} changed coordinates. Verdict, matched-fact, and model-cue rates across 5, 10, 20, and 40 queries.`);
    const tableRows = curve.map(p => `<tr class="${limit === 1 && p.total_queries === 5 ? 'selected' : ''}"><td>${p.total_queries}</td><td>${pct(p.V_rate)}</td><td>${pct(p.S_rate)}</td><td>${pct(p.M_family_rate)}</td></tr>`).join('');
    document.getElementById('budgetTable').innerHTML = `<table class="budget-table"><caption class="sr-only">Matched bypass rate by query budget</caption><thead><tr><th>Queries</th><th>V</th><th>S</th><th>M</th></tr></thead><tbody>${tableRows}</tbody></table>`;
  }
  modelButtons.forEach(button => button.addEventListener('click', () => {
    selectedModel = button.dataset.model;
    modelButtons.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    updateExplorer();
  }));
  changesSelect.addEventListener('change', updateExplorer);
  updateExplorer();

  document.getElementById('manifestHash').textContent = `Manifest · ${data.source_manifest_sha256.slice(0, 12)}…`;
  document.getElementById('recalcButton').addEventListener('click', () => {
    const checks = Object.entries(data.models).map(([name,m]) => {
      const recalculated = m.matched_rates.M_family - m.matched_rates.S;
      return {name, recalculated, passed: Math.abs(recalculated - m.difference) < 1e-12};
    });
    const passed = checks.every(c => c.passed);
    const output = document.getElementById('recalcOutput');
    output.classList.toggle('pass', passed);
    output.textContent = passed
      ? `Arithmetic matches the frozen manifest: logistic ${points(checks[0].recalculated)}, boosted trees ${points(checks[1].recalculated)}. Use the Python verifier for the clustered intervals.`
      : 'At least one displayed risk difference did not match the frozen manifest.';
  });
  document.getElementById('copyCommand').addEventListener('click', async (event) => {
    try {
      await navigator.clipboard.writeText('python3 demo/reproduce.py');
      event.target.textContent = 'Copied';
      setTimeout(() => { event.target.textContent = 'Copy'; }, 1800);
    } catch (_) { event.target.textContent = 'Copy manually'; }
  });
})();
