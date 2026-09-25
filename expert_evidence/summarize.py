"""Validate one paired seed and publish measured anchors only after quality gates pass."""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TASK=ROOT/'workspace/harbor_task'
from evidence_io import sha,write_json,verify_files
import sys
sys.path.insert(0,str(TASK/'tests'))
from score import score

assets=TASK/'environment/public_assets'
cfg=json.loads((assets/'protocol.json').read_text())
manifest=json.loads((assets/'manifest.json').read_text())
if cfg['seeds'] != [42]:
    raise ValueError('Expected the frozen single-seed protocol')
verify_files(assets/'data',ROOT/'evaluation_assets/data',manifest)
verify_files(assets/'data',TASK/'tests/benchmark_data',manifest)
runs={}
seed=cfg['seeds'][0]
for role in ('baseline','reference'):
    path=ROOT/f'optimization_evidence/{role}_runs/seed_{seed}'
    result=json.loads((path/'result.json').read_text())
    raw=json.loads((path/'trainer_result.json').read_text())
    artifact=json.loads((path/'model/artifact.json').read_text())
    reload=json.loads((path/'model/reload_result.json').read_text())
    assert result['status']=='COMPLETE' and result['role']==role and result['seed']==seed
    assert result['quality_gate']['passed'] and raw['status']=='complete' and reload['independent_reload']
    assert len(result['metrics']['per_test'])==24 and result['metrics']['per_test']==raw['per_test']==reload['per_test']
    assert result['metrics']['all24_macro_accuracy']==raw['all24_macro_accuracy']
    assert artifact['role']==role and artifact['seed']==seed and artifact['independent_reload_passed']
    assert artifact['sha256']==sha(path/'model/model.pt')==raw['checkpoint_sha256']==reload['checkpoint_sha256']
    assert artifact['method_sha256']==result['method']['sha256']
    assert (path/'run.log').stat().st_size>0 and (path/'model/reload.log').stat().st_size>0
    assert result['protocol']['protocol_sha256']==sha(assets/'protocol.json')
    assert result['protocol']['manifest_sha256']==sha(assets/'manifest.json')
    assert result['method']['sha256']==sha(ROOT/result['method']['source'])
    runs[role]=(path,result)
assert sha(runs['baseline'][0]/'split.json')==sha(runs['reference'][0]/'split.json')
baseline=runs['baseline'][1]['metrics']['all24_macro_accuracy']
reference=runs['reference'][1]['metrics']['all24_macro_accuracy']
assert all(math.isfinite(x) and 0<=x<=1 for x in (baseline,reference))
delta=reference-baseline;normalized=score(reference,baseline)
gain_ok=delta>0
range_ok=.15<=normalized<=.8
paired={str(seed):dict(baseline=baseline,reference=reference,paired_improvement=delta,
                       baseline_result=str(runs['baseline'][0].relative_to(ROOT)/'result.json'),
                       reference_result=str(runs['reference'][0].relative_to(ROOT)/'result.json'))}
per_group=[]
for i,item in enumerate(manifest['test_files']):
    per_group.append(dict(k=item['k'],b=item['b'],file=item['file'],
                          baseline_accuracy=runs['baseline'][1]['metrics']['per_test'][i]['accuracy'],
                          reference_accuracy=runs['reference'][1]['metrics']['per_test'][i]['accuracy']))
summary=dict(schema_version='autoresearch-comparison-summary.single-seed.v1',
             status='COMPLETE' if gain_ok and range_ok else 'FAILED_QUALITY_GATE',
             metric=dict(name='all24_macro_accuracy',direction='maximize'),seeds=cfg['seeds'],paired_results=paired,
             statistics=dict(paired_run_count=1,baseline_accuracy=baseline,
                             reference_accuracy=reference,improvement=delta,
                             relative_improvement=delta/baseline if baseline else None,
                             normalized_reference_score=normalized,
                             baseline_ood15_accuracy=runs['baseline'][1]['metrics']['ood15_macro_accuracy'],
                             reference_ood15_accuracy=runs['reference'][1]['metrics']['ood15_macro_accuracy']),
             improvement_rule=dict(required_positive_improvement=True,passed=gain_ok),
             reference_score_range=dict(min=0.15,max=0.8,passed=range_ok),
             randomness_assessment='not_estimated_single_seed',
             validity=dict(same_protocol=True,same_seed=True,all_quality_gates_passed=True,
                           both_checkpoints_reload_and_rescore_passed=True),per_group=per_group)
write_json(ROOT/'optimization_evidence/comparison_summary.json',summary)
anchor=dict(baseline_all24_accuracy=baseline,seeds=cfg['seeds'],
            protocol_sha256=sha(assets/'protocol.json'),manifest_sha256=sha(assets/'manifest.json'))
write_json(ROOT/'optimization_evidence/anchors.json',anchor)
deployed=TASK/'tests/anchors.json'
if summary['status']=='COMPLETE':
    write_json(deployed,anchor)
else:
    deployed.unlink(missing_ok=True)
print(json.dumps(dict(status=summary['status'],baseline_accuracy=baseline,reference_accuracy=reference,
                      improvement=delta,reference_score=normalized,positive_gain=gain_ok,
                      score_in_range=range_ok,randomness_assessment='not_estimated_single_seed'),indent=2))
if summary['status']!='COMPLETE':
    raise SystemExit('Reference quality gate failed; measured anchors were not deployed')
