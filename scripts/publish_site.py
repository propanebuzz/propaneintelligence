"""Publish only dashboard export files, using verified repository-specific credentials."""
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.export_site import export, ROOT

FILES = ['docs/index.html', 'docs/snapshot.js']


def git(*args, **kwargs):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True, text=True, **kwargs).stdout


def verify_access():
    if git('remote', 'get-url', 'origin').strip() != 'https://github.com/propanebuzz/propaneintelligence.git':
        raise RuntimeError('Unexpected publish repository')
    if git('branch', '--show-current').strip() != 'main':
        raise RuntimeError('Publishing requires the main checkout')
    answer = git('credential', 'fill', input='protocol=https\nhost=github.com\npath=propanebuzz/propaneintelligence.git\nusername=propanebuzz\n\n')
    credentials = dict(line.split('=', 1) for line in answer.splitlines() if '=' in line)
    headers = {'Authorization': 'Bearer ' + credentials['password'], 'Accept': 'application/vnd.github+json'}
    def get(path):
        with urlopen(Request('https://api.github.com/' + path, headers=headers), timeout=30) as response:
            return json.load(response)
    if get('user')['login'] != 'propanebuzz' or not get('repos/propanebuzz/propaneintelligence')['permissions']['push']:
        raise RuntimeError('Publishing identity or write access mismatch')


def recoverable_publish():
    return (git('rev-list', '--count', 'origin/main..HEAD').strip() == '1'
            and git('rev-list', '--count', 'HEAD..origin/main').strip() == '0'
            and git('log', '-1', '--format=%s').strip() == 'Refresh validated propane dashboard snapshot'
            and set(git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').splitlines()) <= set(FILES))


def publish():
    verify_access()
    if git('status', '--porcelain', '--untracked-files=no').strip():
        raise RuntimeError('Checkout has pending changes; publish requires review')
    git('fetch', 'origin', 'main')
    if git('rev-parse', 'HEAD').strip() != git('rev-parse', 'origin/main').strip():
        if not recoverable_publish():
            raise RuntimeError('Checkout differs from GitHub main; reconcile before publishing')
        git('push', 'origin', 'HEAD:main')
    export(ROOT / 'docs')
    if not git('diff', '--', *FILES).strip():
        print('Site already current; no commit required.'); return
    git('add', '--', *FILES)
    git('commit', '--only', '-m', 'Refresh validated propane dashboard snapshot', '--', *FILES)
    git('push', 'origin', 'HEAD:main')
    print('Validated dashboard snapshot committed and pushed. Pages deployment is asynchronous.')


if __name__ == '__main__':
    try: publish()
    except Exception as error:
        print('Site publish stopped:', str(error) if isinstance(error, RuntimeError) else type(error).__name__)
        raise SystemExit(1)
