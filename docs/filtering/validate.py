#!/usr/bin/env python3
"""Validate inactive stages in a fresh copy and network namespace. Never plan/apply."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from test_filtering import HERE, ROOT, STAGES, apply_stage, copy_stack

TOFU_SHA256 = 'b6cb308bd699c8b53882319986f339eeaa44f925a68f12d5b0a14e6caceedf23'
PROVIDER_SHA256 = '58bbac53de7ab857503c833ae5049915c2f015f72bf7b6aec99e889dd68684e1'
PROVIDER = ROOT / 'tofu/stalwart/.terraform/providers/registry.opentofu.org/tahacodes/stalwart/0.2.3/linux_amd64'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def namespace(kind):
    return os.readlink('/proc/self/ns/' + kind)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tofu', type=Path, default=Path('/tmp/tofu-runner-qualified-tofu'))
    parser.add_argument('--provider-dir', type=Path, default=PROVIDER,
                        help='Already installed tahacodes/stalwart 0.2.3 linux_amd64 directory')
    parser.add_argument('--isolated', nargs=3, help=argparse.SUPPRESS)
    args = parser.parse_args()
    tofu = args.tofu.resolve()
    if digest(tofu) != TOFU_SHA256:
        raise SystemExit('Refusing unqualified OpenTofu binary; expected controller-extracted 1.12.1')
    if digest(args.provider_dir.resolve() / 'terraform-provider-stalwart_v0.2.3') != PROVIDER_SHA256:
        raise SystemExit('Refusing a provider other than the qualified 0.2.3 release binary')
    if args.isolated is None:
        work = Path(tempfile.mkdtemp(prefix='company-filtering-validate-'))
        command = ['unshare', '-Urn', sys.executable, '-B', str(Path(__file__).resolve()),
                   '--tofu', str(tofu), '--provider-dir', str(args.provider_dir.resolve()),
                   '--isolated', str(work), namespace('net'), namespace('user')]
        print('Validation evidence:', work, flush=True)
        with (work / 'run.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        print('Exit:', result.returncode, flush=True)
        return result.returncode
    work = Path(args.isolated[0])
    if work.parent != Path('/tmp') or not work.name.startswith('company-filtering-validate-'):
        raise SystemExit('Unsafe temporary path')
    if namespace('net') == args.isolated[1] or namespace('user') == args.isolated[2]:
        raise SystemExit('Validation requires separate network and user namespaces')
    subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True, timeout=5)
    stack = copy_stack(work)
    mirror = work / 'mirror'
    shutil.copytree(args.provider_dir.resolve(), mirror / 'registry.opentofu.org/tahacodes/stalwart/0.2.3/linux_amd64')
    cli = work / 'tofurc'
    cli.write_text('provider_installation {\n  filesystem_mirror {\n'
                   f'    path = "{mirror}"\n'
                   '    include = ["registry.opentofu.org/tahacodes/stalwart"]\n  }\n}\n')
    home = work / 'home'
    home.mkdir()
    # No inherited tokens, CLI credentials, backend settings or provider env.
    env = {'PATH': os.environ['PATH'], 'HOME': str(home), 'TF_IN_AUTOMATION': '1',
           'TF_INPUT': '0', 'TF_CLI_CONFIG_FILE': str(cli), 'TF_DATA_DIR': str(work / 'data'),
           'TF_VAR_stalwart_endpoint': 'http://127.0.0.1:1', 'CHECKPOINT_DISABLE': '1'}
    report = {'tofuSha256': digest(tofu), 'providerVersion': '0.2.3', 'stages': {},
              'providerSha256': digest(args.provider_dir.resolve() / 'terraform-provider-stalwart_v0.2.3'),
              'sourceFiles': {p.name: digest(p) for p in stack.iterdir()},
              'patchSha256': {name: digest(HERE / 'stages' / name) for name in STAGES},
              'netNamespace': namespace('net'), 'userNamespace': namespace('user')}

    def run(*arguments):
        if arguments[0] not in ('version', 'init', 'fmt', 'validate'):
            raise AssertionError('Forbidden OpenTofu operation')
        print('tofu', *arguments, flush=True)
        result = subprocess.run([str(tofu), *arguments], cwd=stack, env=env,
                                capture_output=True, text=True, timeout=45)
        print(result.stdout, result.stderr, flush=True)
        result.check_returncode()
        return result.stdout

    try:
        version = json.loads(run('version', '-json'))['terraform_version']
        if version != '1.12.1':
            raise AssertionError('Unexpected qualified controller version')
        report['tofuVersion'] = version
        run('init', '-backend=false', '-get=false', '-input=false', '-lockfile=readonly', '-no-color')
        for stage in STAGES:
            apply_stage(work, stage)
            run('fmt', '-check', '-no-color')
            run('validate', '-no-color')
            report['stages'][stage] = 'PASS'
        report['status'] = 'PASS'
    finally:
        (work / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
