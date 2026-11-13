"""Compile controlled fixtures, recover them, and compare behavior.

The target executables are analyzed statically. Only the fixture functions and
their recovered counterparts are executed, with local deterministic stubs.
Run from any directory with the same Python used to build the extensions:
    python validation/run_matrix.py --output .perf/matrix_current
"""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = (
    ('fixture_core_control', 'compare_core_fixture.py', 'control_behavior.json'),
    ('fixture_tuple_control', 'compare_tuple_fixture.py', 'tuple_behavior.json'),
    ('fixture_unpack_control', 'compare_unpack_fixture.py', 'unpack_behavior.json'),
    ('fixture_general_dispatch', 'compare_general_fixture.py', 'fixture_behavior.json'),
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, log_path, timeout, env=None, cwd=None):
    try:
        process = subprocess.run(args, cwd=cwd or ROOT, capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=timeout,
                                 env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(str(exc), encoding='utf-8')
        return {'exit_code': None, 'error': str(exc)}
    log_path.write_text(process.stdout + process.stderr, encoding='utf-8')
    return {'exit_code': process.returncode}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--target-python', default=sys.executable,
                        help='Python interpreter used to compile the fixture')
    parser.add_argument('--nuitka-source', type=Path,
                        help='optional Nuitka checkout added only to the compiler environment')
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error('--output must be a new or empty directory; choose a fresh path for each run')
    out.mkdir(parents=True, exist_ok=True)
    compiler_env = os.environ.copy()
    if args.nuitka_source:
        compiler_env['PYTHONPATH'] = str(args.nuitka_source.resolve()) + (
            os.pathsep + compiler_env['PYTHONPATH'] if compiler_env.get('PYTHONPATH') else '')
    version = subprocess.run([args.target_python, '-m', 'nuitka', '--version'], cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', errors='replace',
                             env=compiler_env)
    report = {'python': sys.version, 'platform': platform.platform(),
              'nuitka_version': version.stdout.strip(), 'target_python': args.target_python,
              'nuitka_source': str(args.nuitka_source.resolve()) if args.nuitka_source else None,
              'decompiler_sha256': sha256(ROOT / 'nuitka_decompiler.py'),
              'fixtures': [], 'status': 'partial'}
    for name, comparator, filename in FIXTURES:
        started = time.monotonic()
        fixture = ROOT / 'validation' / 'fixtures' / (name + '.py')
        build_dir, recovered = out / name / 'build', out / name / 'recovered'
        build_dir.mkdir(parents=True, exist_ok=True)
        recovered.mkdir(parents=True, exist_ok=True)
        record = {'name': name, 'source_sha256': sha256(fixture),
                  'comparator_sha256': sha256(ROOT / 'validation' / comparator),
                  'status': 'failed'}
        record['compile'] = run([args.target_python, '-m', 'nuitka', '--module', str(fixture),
                                 '--output-dir=' + str(build_dir), '--assume-yes-for-downloads'],
                                out / name / 'compile.log', args.timeout, env=compiler_env,
                                cwd=build_dir)
        candidates = list(build_dir.glob(name + '.*.pyd')) + list(build_dir.glob(name + '.*.so'))
        if record['compile']['exit_code'] == 0 and len(candidates) == 1:
            binary = candidates[0]
            record['binary_sha256'] = sha256(binary)
            record['recover'] = run([sys.executable, str(ROOT / 'nuitka_decompiler.py'),
                                     '--ndx', str(binary), '-o', str(recovered)],
                                    out / name / 'recover.log', args.timeout)
            if record['recover']['exit_code'] == 0:
                record['compare'] = run([sys.executable, str(ROOT / 'validation' / comparator), str(recovered)],
                                        out / name / 'compare.log', args.timeout)
                comparison = recovered / filename
                if record['compare']['exit_code'] == 0 and comparison.is_file():
                    cases = json.loads(comparison.read_text(encoding='utf-8'))
                    record['cases'] = len(cases)
                    record['matched'] = sum(case.get('matches') is True for case in cases)
                    record['mismatched'] = record['cases'] - record['matched']
                    record['status'] = 'passed' if record['cases'] and not record['mismatched'] else 'partial'
                    record['comparison'] = str(comparison.relative_to(out))
        record['seconds'] = round(time.monotonic() - started, 2)
        report['fixtures'].append(record)
        print('%s: %s (%s/%s)' % (name, record['status'], record.get('matched', 0),
                                   record.get('cases', 0)), flush=True)
    if all(record['status'] == 'passed' for record in report['fixtures']):
        report['status'] = 'passed'
    (out / 'matrix.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report:', out / 'matrix.json')
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
