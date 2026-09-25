"""Trusted single-seed grader; candidate code runs without access to labels."""
import argparse
import hashlib
import json
import os
import pwd
import select
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from data import read_rows, sha, verify, write_json
from score import score
from security import check_method

TASK = Path('/workspace') if Path('/workspace/environment/public_assets').is_dir() else Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
ASSETS = TASK / 'environment/public_assets'


def candidate_command(user, *args):
    command = [sys.executable, *map(str, args)]
    return ['runuser', '-u', user, '--', *command] if user else command


def isolated_accuracy(worker, rows, batch_size, timeout_seconds):
    correct = 0
    predictions = bytearray()
    for begin in range(0, len(rows), batch_size):
        batch = rows[begin:begin + batch_size]
        inputs = [{key: row[key] for key in ('edges', 'rels', 'query', 'n')} for row in batch]
        worker.stdin.write(json.dumps(inputs, separators=(',', ':')) + '\n')
        worker.stdin.flush()
        ready, _, _ = select.select([worker.stdout], [], [], timeout_seconds)
        if not ready:
            raise TimeoutError('Inference worker did not respond')
        line = worker.stdout.readline()
        if not line:
            raise RuntimeError('Inference worker exited before returning predictions')
        pred = json.loads(line)
        if not isinstance(pred, list) or len(pred) != len(batch) or any(type(x) is not int or not 0 <= x < 8 for x in pred):
            raise ValueError('Invalid prediction response')
        correct += sum(int(p == row['label']) for p, row in zip(pred, batch))
        predictions.extend(pred)
    return dict(correct=correct, total=len(rows), accuracy=correct / len(rows),
                predictions_sha256=hashlib.sha256(predictions).hexdigest())


def run_isolated(seed, cfg, manifest, args):
    out = args.output / f'seed_{seed}'
    with (args.output / f'seed_{seed}.log').open('w') as log:
        subprocess.run(candidate_command(args.candidate_user, TESTS / 'train_eval.py',
                                         '--method', args.method.resolve(), '--output', out.resolve(),
                                         '--seed', seed, '--data', args.data.resolve(), '--public-dev'),
                       check=True, stdout=log, stderr=subprocess.STDOUT,
                       timeout=cfg['per_seed_timeout_seconds'])
    training = json.loads((out / 'result.json').read_text())
    if training['status'] != 'public-dev' or training['seed'] != seed:
        raise ValueError('Incomplete training stage')
    provenance = json.loads((out / 'provenance.json').read_text())
    if provenance['method_sha256'] != sha(args.method) or provenance['parameters'] > cfg['max_parameters']:
        raise ValueError('Method or parameter provenance mismatch')
    if sha(out / 'best.pt') != training['checkpoint_sha256']:
        raise ValueError('Training checkpoint hash mismatch')
    with tempfile.TemporaryDirectory(prefix='tob242-checked-') as temporary:
        protected = Path(temporary)
        os.chmod(protected, 0o755)
        checkpoint = protected / 'model.pt'
        shutil.copy2(out / 'best.pt', checkpoint)
        os.chmod(checkpoint, 0o444)
        if sha(checkpoint) != training['checkpoint_sha256']:
            raise ValueError('Protected checkpoint copy mismatch')
        with (args.output / f'seed_{seed}_inference.log').open('w') as log:
            worker = subprocess.Popen(candidate_command(args.candidate_user, TESTS / 'inference_worker.py',
                                                         '--method', args.method.resolve(), '--checkpoint', checkpoint,
                                                         '--num-steps', cfg['num_steps']),
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                      text=True, bufsize=1)
            tests = []
            try:
                for item in manifest['test_files']:
                    rows = read_rows(args.test_data / item['file'])
                    result = isolated_accuracy(worker, rows, cfg['eval_batch_size'], 180)
                    tests.append({**item, **result})
                    print('TEST', json.dumps(dict(file=item['file'], accuracy=result['accuracy'])), flush=True)
                worker.stdin.close()
                if worker.wait(timeout=60) != 0:
                    raise RuntimeError('Inference worker failed')
            finally:
                if worker.poll() is None:
                    worker.kill()
                    worker.wait()
    ood = [item['accuracy'] for item in tests if item['k'] >= 5]
    result = dict(status='complete', seed=seed, best_epoch=training['best_epoch'],
                  best_val_accuracy=training['best_val_accuracy'],
                  all24_macro_accuracy=statistics.mean(item['accuracy'] for item in tests),
                  ood15_macro_accuracy=statistics.mean(ood),
                  checkpoint_sha256=training['checkpoint_sha256'],
                  training_result='result.json', per_test=tests)
    write_json(out / 'formal_result.json', result)
    return result


def run_trusted(seed, cfg, args):
    out = args.output / f'seed_{seed}'
    with (args.output / f'seed_{seed}.log').open('w') as log:
        subprocess.run(candidate_command(None, TESTS / 'train_eval.py', '--method', args.method.resolve(),
                                         '--output', out.resolve(), '--seed', seed, '--data', args.data.resolve(),
                                         '--test-data', args.test_data.resolve()),
                       check=True, stdout=log, stderr=subprocess.STDOUT,
                       timeout=cfg['per_seed_timeout_seconds'])
    return json.loads((out / 'result.json').read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--method', type=Path, default=TASK / 'solution/method.py')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--anchors', type=Path, required=True)
    parser.add_argument('--data', type=Path, default=ASSETS / 'data')
    parser.add_argument('--test-data', type=Path, default=TESTS / 'benchmark_data')
    parser.add_argument('--candidate-user', help='Run untrusted model code as this lower-privilege user')
    parser.add_argument('--reward-file', type=Path, help='Write the trusted final scalar atomically')
    args = parser.parse_args()
    cfg = json.loads((ASSETS / 'protocol.json').read_text())
    if cfg['seeds'] != [42]:
        raise ValueError('This grader requires the frozen single-seed protocol')
    manifest = json.loads((ASSETS / 'manifest.json').read_text())
    anchors = json.loads(args.anchors.read_text())
    if anchors['protocol_sha256'] != sha(ASSETS / 'protocol.json'):
        raise ValueError('Stale protocol anchors')
    if anchors['manifest_sha256'] != sha(ASSETS / 'manifest.json'):
        raise ValueError('Stale dataset anchors')
    if anchors['seeds'] != cfg['seeds']:
        raise ValueError('Anchor seed mismatch')
    verify(args.data, args.test_data, manifest)
    check_method(args.method)
    method_digest = sha(args.method)
    if args.candidate_user:
        if os.geteuid() != 0 or args.candidate_user == 'root':
            raise PermissionError('Isolated grading requires root verifier and a non-root candidate user')
        candidate = pwd.getpwnam(args.candidate_user)
        method_stat = args.method.stat()
        method_parent_stat = args.method.parent.stat()
        if (method_stat.st_uid != 0 or method_parent_stat.st_uid != 0 or
                (method_stat.st_mode & 0o222) or (method_parent_stat.st_mode & 0o222)):
            raise PermissionError('Submitted method and its directory must be root-owned and read-only')
        test_dir = args.test_data.resolve()
        if not test_dir.is_relative_to(TESTS.resolve()):
            raise ValueError('Isolated test data must be inside the verifier tests directory')
        if test_dir.stat().st_uid != 0 or (test_dir.stat().st_mode & 0o077):
            raise PermissionError('Benchmark data directory must be root-only')
    args.output.mkdir(parents=True, exist_ok=False)
    if args.candidate_user:
        os.chown(args.output, candidate.pw_uid, candidate.pw_gid)
    results = []
    start = time.monotonic()
    for seed in cfg['seeds']:
        if sha(args.method) != method_digest:
            raise ValueError('Method changed during evaluation')
        result = run_isolated(seed, cfg, manifest, args) if args.candidate_user else run_trusted(seed, cfg, args)
        if sha(args.method) != method_digest:
            raise ValueError('Method changed during evaluation')
        if result['status'] != 'complete' or len(result['per_test']) != len(manifest['test_files']):
            raise ValueError('Incomplete benchmark')
        results.append(result)
    groups = []
    for index, item in enumerate(manifest['test_files']):
        records = [result['per_test'][index] for result in results]
        if any(record['file'] != item['file'] or record['total'] != item['rows'] for record in records):
            raise ValueError('Test group mismatch: ' + item['file'])
        groups.append(dict(file=item['file'], k=item['k'], b=item['b'],
                           accuracy=records[0]['accuracy']))
    accuracy = statistics.mean(result['all24_macro_accuracy'] for result in results)
    report = dict(accuracy=accuracy, score=score(accuracy, anchors['baseline_all24_accuracy']),
                  seeds=cfg['seeds'],
                  ood15_macro_accuracy=statistics.mean(result['ood15_macro_accuracy'] for result in results),
                  per_group=groups, per_seed=results, method_sha256=method_digest,
                  elapsed_seconds=time.monotonic() - start)
    write_json(args.output / 'metrics.json', report)
    if args.reward_file:
        args.reward_file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=args.reward_file.parent,
                                         prefix='.reward-', delete=False) as stream:
            temp_name = stream.name
            stream.write(f"{report['score']:.17g}\n")
        os.replace(temp_name, args.reward_file)
    print(json.dumps(dict(accuracy=accuracy, score=report['score'])), flush=True)


if __name__ == '__main__':
    main()
