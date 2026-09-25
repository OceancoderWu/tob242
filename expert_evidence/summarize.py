import json,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/harbor_task/tests'))
from data import sha,write_json
from score import score
assets=ROOT/'workspace/harbor_task/environment/public_assets';cfg=json.loads((assets/'protocol.json').read_text());summary={}
for method in ['baseline','reference']:
 results=[]
 for seed in cfg['seeds']:
  run=ROOT/f'optimization_evidence/{method}_runs/seed_{seed}'
  r=json.loads((run/'result.json').read_text());reload=json.loads(Path(str(run)+'_reload/result.json').read_text())
  assert r['status']=='complete' and len(r['per_test'])==24
  assert reload['independent_reload'] and r['per_test']==reload['per_test']
  assert r['checkpoint_sha256']==reload['checkpoint_sha256']==sha(run/'best.pt')
  other=ROOT/f'optimization_evidence/baseline_runs/seed_{seed}/split.json'
  assert sha(run/'split.json')==sha(other)
  results.append(r)
 values=[r['all24_macro_accuracy'] for r in results]
 summary[method]=dict(mean=statistics.mean(values),sample_std=statistics.stdev(values),two_sigma_population=2*statistics.pstdev(values),ood15_mean=statistics.mean(r['ood15_macro_accuracy'] for r in results),per_seed=results,
                       per_group=[dict(k=x['k'],b=x['b'],mean=statistics.mean(r['per_test'][i]['accuracy'] for r in results),two_sigma=2*statistics.pstdev(r['per_test'][i]['accuracy'] for r in results)) for i,x in enumerate(results[0]['per_test'])])
b=summary['baseline'];r=summary['reference'];s=score(r['mean'],b['mean'])
summary['reference_score']=s;summary['acceptance']=dict(reference_score_in_required_range=.15<=s<=.8,gain_ge_three_baseline_std=r['mean']-b['mean']>=3*b['sample_std'],paired_seeds=cfg['seeds'],checkpoint_reloads_passed=True)
write_json(ROOT/'optimization_evidence/comparison_summary.json',summary)
write_json(ROOT/'optimization_evidence/anchors.json',dict(baseline_all24_mean=b['mean'],seeds=cfg['seeds'],protocol_sha256=sha(assets/'protocol.json'),manifest_sha256=sha(assets/'manifest.json')))
print(json.dumps({m:{k:v for k,v in summary[m].items() if k not in ['per_seed','per_group']} for m in ['baseline','reference']},indent=2));print('Reference score:',s)
