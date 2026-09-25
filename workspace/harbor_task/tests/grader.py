"""Run full paired-seed protocol. Anchors are trusted deployment inputs."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from data import write_json,sha
from security import check_method
from score import score
TASK=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--method',type=Path,default=TASK/'solution/method.py')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--anchors',type=Path,required=True)
    p.add_argument('--data',type=Path,default=TASK/'environment/public_assets/data');p.add_argument('--test-data',type=Path,default=Path('/opt/benchmark/data'));a=p.parse_args()
    cfg=json.loads((TASK/'environment/public_assets/protocol.json').read_text())
    anchors=json.loads(a.anchors.read_text())
    if anchors['protocol_sha256']!=sha(TASK/'environment/public_assets/protocol.json'):raise ValueError('Stale anchors')
    if anchors['manifest_sha256']!=sha(TASK/'environment/public_assets/manifest.json'):raise ValueError('Stale dataset anchors')
    if anchors['seeds']!=cfg['seeds']:raise ValueError('Anchor seed mismatch')
    check_method(a.method);a.output.mkdir(parents=True,exist_ok=False)
    results=[]
    for seed in cfg['seeds']:
        out=a.output/f'seed_{seed}'
        with (a.output/f'seed_{seed}.log').open('w') as f:
            subprocess.run([sys.executable,str(TASK/'tests/train_eval.py'),'--method',str(a.method.resolve()),'--output',str(out.resolve()),'--seed',str(seed),'--data',str(a.data.resolve()),'--test-data',str(a.test_data.resolve())],check=True,stdout=f,stderr=subprocess.STDOUT,timeout=7200)
        r=json.loads((out/'result.json').read_text())
        if r['status']!='complete' or len(r['per_test'])!=24:raise ValueError('Incomplete benchmark')
        results.append(r)
    acc=sum(r['all24_macro_accuracy'] for r in results)/len(results)
    report=dict(accuracy=acc,score=score(acc,anchors['baseline_all24_mean']),seeds=cfg['seeds'],per_seed=results)
    write_json(a.output/'metrics.json',report);print(json.dumps({'accuracy':acc,'score':report['score']}))
if __name__=='__main__':main()
