"""Package one actual training seed without inventing missing measurements."""
import argparse
from datetime import datetime
import json
import math
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / 'workspace/harbor_task'
from evidence_io import sha, write_json


def rel(path):
    return str(path.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=('baseline', 'reference'), required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--method', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--reload', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--reload-log', type=Path, required=True)
    parser.add_argument('--started-at', required=True)
    parser.add_argument('--ended-at', required=True)
    parser.add_argument('--exit-code', type=int, required=True)
    args = parser.parse_args()
    run, reload = args.run.resolve(), args.reload.resolve()
    run.mkdir(parents=True, exist_ok=True)
    if args.log.exists():
        shutil.move(str(args.log), str(run / 'run.log'))
    cfg = json.loads((TASK / 'environment/public_assets/protocol.json').read_text())
    manifest = TASK / 'environment/public_assets/manifest.json'
    method_hash = sha(args.method)
    common = dict(schema_version='autoresearch-run.v2',
                  status='COMPLETE' if args.exit_code == 0 else 'INVALID',
                  role=args.role, seed=args.seed, task_type='model_training',
                  method=dict(name=args.role, source=rel(args.method.resolve()), sha256=method_hash,
                              trainer_sha256=sha(TASK / 'tests/train_eval.py'),
                              data_loader_sha256=sha(TASK / 'tests/data.py')),
                  protocol=dict(name='tob242-rcc8-v2', protocol_sha256=sha(TASK / 'environment/public_assets/protocol.json'),
                                manifest_sha256=sha(manifest), metric='all24_macro_accuracy', direction='maximize',
                                seeds=cfg['seeds'], test_groups=24, parameter_limit=cfg['max_parameters']),
                  training=dict(epochs=cfg['epochs'], batch_size=cfg['batch_size'], optimizer=cfg['optimizer'],
                                lr=cfg['lr'], weight_decay=cfg['weight_decay'], checkpoint_rule=cfg['checkpoint_rule']),
                  execution=dict(command=['python', rel(TASK / 'tests/train_eval.py'), '--method', rel(args.method.resolve()),
                                          '--seed', str(args.seed), '--output', rel(run)],
                                 started_at=args.started_at, ended_at=args.ended_at,
                                 exit_code=args.exit_code,
                                 elapsed_seconds=(datetime.fromisoformat(args.ended_at.replace('Z','+00:00'))-
                                                  datetime.fromisoformat(args.started_at.replace('Z','+00:00'))).total_seconds()),
                  metrics={}, quality_gate={}, artifacts={})
    if args.exit_code:
        raw = run / 'result.json'
        if raw.is_file():
            shutil.move(str(raw), str(run / 'trainer_result.json'))
        if args.reload_log.exists():
            shutil.move(str(args.reload_log), str(run / 'reload_failed.log'))
        common['quality_gate'] = dict(passed=False, reason='Training or reload exited nonzero; inspect original logs')
        common['artifacts'] = dict(run_log=rel(run / 'run.log') if (run / 'run.log').is_file() else None,
                                   trainer_result=rel(run / 'trainer_result.json') if (run / 'trainer_result.json').is_file() else None,
                                   reload_log=rel(run / 'reload_failed.log') if (run / 'reload_failed.log').is_file() else None)
        write_json(run / 'result.json', common)
        return
    original = json.loads((run / 'result.json').read_text())
    reloaded = json.loads((reload / 'result.json').read_text())
    provenance = json.loads((run / 'provenance.json').read_text())
    if original['status'] != 'complete' or len(original['per_test']) != 24:
        raise ValueError('Incomplete formal training result')
    if not args.reload_log.is_file() or args.reload_log.stat().st_size == 0:
        raise ValueError('Missing independent reload log')
    if reloaded['status'] != 'complete' or not reloaded['independent_reload']:
        raise ValueError('Independent reload did not complete')
    if original['per_test'] != reloaded['per_test'] or original['checkpoint_sha256'] != reloaded['checkpoint_sha256']:
        raise ValueError('Reload predictions or checkpoint hash differ')
    if provenance['method_sha256'] != method_hash or provenance['parameters'] > cfg['max_parameters']:
        raise ValueError('Method or parameter quality gate failed')
    if not all(math.isfinite(original[key]) for key in ('all24_macro_accuracy', 'ood15_macro_accuracy')):
        raise ValueError('Nonfinite benchmark metric')
    model_dir = run / 'model'
    model_dir.mkdir(exist_ok=False)
    shutil.move(str(run / 'best.pt'), str(model_dir / 'model.pt'))
    if args.reload_log.exists():
        shutil.move(str(args.reload_log), str(model_dir / 'reload.log'))
    shutil.copy2(reload / 'result.json', model_dir / 'reload_result.json')
    artifact = dict(model_path=rel(model_dir / 'model.pt'), format='torch-state-dict-checkpoint',
                    size_bytes=(model_dir / 'model.pt').stat().st_size, sha256=sha(model_dir / 'model.pt'),
                    role=args.role, seed=args.seed, method_sha256=method_hash,
                    source_result=rel(run / 'result.json'), independent_reload_passed=True,
                    reload_result=rel(model_dir / 'reload_result.json'))
    write_json(model_dir / 'artifact.json', artifact)
    shutil.move(str(run / 'result.json'), str(run / 'trainer_result.json'))
    common['training']['elapsed_seconds'] = original['elapsed_seconds']
    common['metrics'] = dict(all24_macro_accuracy=original['all24_macro_accuracy'],
                             ood15_macro_accuracy=original['ood15_macro_accuracy'],
                             best_val_accuracy=original['best_val_accuracy'], best_epoch=original['best_epoch'],
                             per_test=original['per_test'], peak_gpu_bytes=original['peak_gpu_bytes'])
    common['quality_gate'] = dict(passed=True, complete_groups=24, within_parameter_limit=True,
                                  independent_reload_passed=True)
    common['artifacts'] = dict(run_log=rel(run / 'run.log'), trainer_result=rel(run / 'trainer_result.json'),
                               model=artifact['model_path'], model_artifact=rel(model_dir / 'artifact.json'),
                               reload_log=rel(model_dir / 'reload.log'),
                               reload_result=artifact['reload_result'])
    write_json(run / 'result.json', common)
    shutil.rmtree(reload)


if __name__ == '__main__':
    main()
