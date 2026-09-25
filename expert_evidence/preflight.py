"""Read-only package preflight. Never imports task code or starts training."""

import argparse
import ast
import hashlib
import json
import shlex
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / 'workspace/harbor_task'
AGENT = TASK / 'environment'
TESTS = TASK / 'tests'
VERIFIER = TESTS / 'verifier_env'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def copy_sources(dockerfile, context):
    for line in dockerfile.read_text().splitlines():
        stripped = line.strip()
        if not stripped.startswith('COPY '):
            continue
        fields = shlex.split(stripped)
        sources = fields[1:-1]
        if any(part.startswith('--') for part in sources):
            raise ValueError(f'Unsupported COPY flag in {dockerfile}: {stripped}')
        for source in sources:
            path = (context / source).resolve()
            if not path.is_relative_to(context.resolve()) or not path.exists():
                raise ValueError(f'COPY source outside or missing from context: {source}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    checks = []

    def check(name, condition, detail):
        checks.append(dict(name=name, passed=bool(condition), detail=detail))

    config = tomllib.loads((TASK / 'task.toml').read_text())
    protocol = json.loads((AGENT / 'public_assets/protocol.json').read_text())
    manifest = json.loads((AGENT / 'public_assets/manifest.json').read_text())
    check('harbor_mode', config['verifier']['environment_mode'] == 'separate',
          'Harbor verifier must use a separate container')
    check('artifact_boundary', config.get('artifacts') == [dict(
        source='/workspace/solution/method.py', destination='submitted_method.py')],
          'Only method.py is declared; test.sh rejects nonempty convention artifacts')
    check('resource_contract', config['environment']['gpus'] == 1 and
          config['environment']['network_mode'] == 'no-network' and
          config['verifier']['user'] == 'root',
          'One GPU, no runtime network, root verifier')
    check('seed_contract', protocol['seeds'] == [42],
          'One predeclared seed for training and formal evaluation')
    check('agent_starter',
          'COPY starter/method.py /workspace/solution/method.py' in
          (AGENT / 'Dockerfile').read_text(),
          'Agent image initializes its candidate from the public R-GCN starter')
    check('oracle_reference', digest(TASK / 'solution/method.py') ==
          digest(ROOT / 'workspace/reference/method.py'),
          'Private Oracle method matches the expert Reference')
    check('oracle_no_argument_entry', '${1:-' in (TASK / 'solution/solve.sh').read_text(),
          'Harbor Oracle can invoke solve.sh with no positional arguments')

    for name in ('instruction.md',):
        check('agent_' + name, digest(TASK / name) == digest(AGENT / name),
              'Agent receives the task instruction')
        check('verifier_' + name, digest(TASK / name) == digest(VERIFIER / name),
              'Verifier instruction mirror matches')
    for name in ('method.py', 'solve.sh'):
        check('verifier_starter_' + name,
              digest(AGENT / 'starter' / name) == digest(VERIFIER / 'starter' / name),
              'Starter mirror matches')
    check('requirements_mirror', digest(AGENT / 'requirements.txt') ==
          digest(VERIFIER / 'requirements.txt'), 'Agent and Verifier dependencies match')
    check('agent_dockerfile_mirror', digest(AGENT / 'Dockerfile') ==
          digest(VERIFIER / 'agent_Dockerfile'), 'Verifier contract copy matches Agent Dockerfile')

    public_runner = ('train_eval.py', 'data.py', 'security.py', 'score.py')
    for name in public_runner:
        expected = digest(TESTS / name)
        check('runner_' + name,
              all(digest(path / name) == expected for path in
                  (AGENT / 'public_runner', VERIFIER / 'public_runner')),
              'Agent and Verifier public runner mirrors match the trusted source')

    asset_root = AGENT / 'public_assets'
    for source in sorted(asset_root.rglob('*')):
        if source.is_file():
            target = VERIFIER / 'public_assets' / source.relative_to(asset_root)
            check('asset_' + source.relative_to(asset_root).as_posix(),
                  target.is_file() and digest(source) == digest(target),
                  'Public asset has an identical Verifier copy')

    train = manifest['train_file']
    files = [train, *manifest['test_files']]
    check('dataset_manifest', len(files) == 25 and len(manifest['test_files']) == 24 and
          {(item['k'], item['b']) for item in manifest['test_files']} ==
          {(k, b) for k in range(2, 10) for b in range(1, 4)},
          'One train CSV and all 24 paper benchmark groups')
    for item in files:
        filename = item['file']
        agent_path = asset_root / 'data' / filename
        path = agent_path if item is train else TESTS / 'benchmark_data' / filename
        check('hash_' + filename, path.is_file() and digest(path) == item['sha256'],
              'Original CSV matches frozen SHA-256')
        if item is not train:
            check('upstream_hash_' + filename,
                  digest(ROOT / 'evaluation_assets/data' / filename) == item['sha256'],
                  'Verifier copy matches the expert source CSV')
    check('agent_excludes_tests', not any((AGENT / 'public_assets/data').glob('test_*.csv')),
          'Agent image context has no test CSV')
    check('reference_outside_task', not (TASK / 'reference').exists() and
          (ROOT / 'workspace/reference/method.py').is_file(),
          'Reference is outside both Harbor build contexts')

    for context in (AGENT, TESTS):
        dockerfile = context / 'Dockerfile'
        try:
            copy_sources(dockerfile, context)
            valid = True
        except ValueError as error:
            valid = False
            detail = str(error)
        else:
            detail = 'All local COPY sources exist inside their native context'
        check('docker_context_' + context.name, valid, detail)
        check('no_context_symlink_escape_' + context.name,
              all(path.resolve().is_relative_to(context.resolve()) for path in context.rglob('*')),
              'Build context contains no symlink escaping its root')

    for source in [*TASK.rglob('*.py'), *ROOT.glob('expert_evidence/*.py')]:
        try:
            ast.parse(source.read_text(), filename=str(source))
            valid = True
        except (SyntaxError, UnicodeError):
            valid = False
        check('syntax_' + source.relative_to(ROOT).as_posix(), valid,
              'Python syntax parses without executing imports')

    pending = []
    if not (TESTS / 'anchors.json').is_file():
        pending.append('measured Baseline/Reference anchors and paired GPU evidence')
    if not (ROOT / 'expert_evidence/trajectory_codex.json').is_file():
        pending.append('two real Agent research trajectories')
    pending.append('single-seed protocol cannot establish tutorial 3-sigma randomness gate')
    pending.append('GPU image build, permission probe, full Harbor Trial, resource and 12h checks')
    report = dict(status='STATIC_READY' if all(item['passed'] for item in checks) else 'STATIC_FAILED',
                  scope='Read-only file/schema/syntax inspection; no model execution or experiment',
                  checks=checks, pending_runtime_evidence=pending)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered)
    print(json.dumps(dict(status=report['status'], checked=len(checks),
                          failed=[item['name'] for item in checks if not item['passed']],
                          pending_runtime_evidence=pending), ensure_ascii=False, indent=2))
    if report['status'] != 'STATIC_READY':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
