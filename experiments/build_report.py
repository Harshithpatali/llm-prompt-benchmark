"""Build a transparent Markdown research report from a benchmark result."""
import json
from pathlib import Path

def main():
    files=sorted(Path('results').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    if not files: raise SystemExit('No result JSON found')
    data=json.loads(files[0].read_text(encoding='utf-8'))
    meta=data.get('metadata',{}); results=data.get('results',[])
    if not results: raise SystemExit('Result artifact has no strategy results')
    lines=['# LLM Prompt Benchmark — Experimental Results','',
      f"- Provider: {meta.get('provider','unknown')}",
      f"- Model: {meta.get('model','unknown')}",
      f"- Evaluation rows: {len(meta.get('test_ids',[]))}",
      f"- Training rows: {meta.get('train_rows','unknown')}",
      f"- Random seed: {meta.get('seed','unknown')}",
      f"- Run timestamp (UTC): {meta.get('timestamp_utc','unknown')}",'',
      '## Strategy comparison','',
      '| Strategy | Exact match | Micro F1 | Precision | Recall | JSON validity | Mean latency (ms) | Failed requests |',
      '|---|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(m,k):
        v=m.get(k); return '—' if v is None else f'{v:.3f}'
    for item in results:
        m=item.get('metrics',{})
        vals=[item.get('strategy','unknown')]+[fmt(m,k) for k in ['overall','micro_f1','micro_precision','micro_recall','json_validity_rate','latency_mean_ms','request_failure_rate']]
        lines.append('| '+' | '.join(vals)+' |')
    fields=['brand','color','product_type','style','material','model_number']
    lines += ['', '## Attribute-level F1','', '| Strategy | '+' | '.join(fields)+' |', '|---|'+'---:|'*len(fields)]
    for item in results:
        attrs=item.get('metrics',{}).get('per_attribute',{})
        lines.append('| '+item.get('strategy','unknown')+' | '+' | '.join(f"{attrs.get(k,{}).get('f1',0):.3f}" for k in fields)+' |')
    comps=data.get('paired_comparisons_vs_zero_shot',{})
    lines += ['', '## Paired comparisons against zero-shot','', '| Strategy | Mean exact-match difference | 95% bootstrap CI | Sign-test p-value | Wins / losses / ties |', '|---|---:|---:|---:|---:|']
    if comps:
        for name,c in comps.items():
            b=c.get('paired_bootstrap',{}); s=c.get('paired_sign_test',{})
            ci=f"[{b.get('ci_lower',float('nan')):.3f}, {b.get('ci_upper',float('nan')):.3f}]"
            lines.append(f"| {name} | {b.get('mean_difference',float('nan')):.3f} | {ci} | {s.get('p_value',float('nan')):.4f} | {s.get('wins',0)} / {s.get('losses',0)} / {s.get('ties',0)} |")
    else: lines.append('| No zero-shot baseline included | — | — | — | — |')
    lines += ['', '## Interpretation and limitations','',
      '- Exact match requires all six attributes to match; interpret it alongside attribute-level F1.',
      '- Paired confidence intervals compare strategies on the same held-out records.',
      '- The paired sign test is two-sided and excludes ties.',
      '- Unsupported-attribute rate is a lexical evidence heuristic, not semantic fact verification.',
      '- API request failures and provider rate limits can affect effective sample size; inspect raw rows.',
      '- Results apply to this dataset split, model, provider and configuration; they do not establish universal superiority.',
      '', f'Raw run artifact: results/{files[0].name}', '']
    Path('reports').mkdir(exist_ok=True)
    out=Path('reports')/(files[0].stem+'_report.md')
    out.write_text('\n'.join(lines),encoding='utf-8')
    print(out)

if __name__=='__main__': main()
