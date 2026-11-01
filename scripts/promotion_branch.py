"""Fail-closed checks for the exclusively automated promotion branch."""
import subprocess
from pathlib import Path

MESSAGE = 'Promote published main images'
BOT = 'beciencia-promotion[bot]@users.noreply.github.com'
ALLOWED = {
    'kubernetes/apps/production/backend.yaml',
    'kubernetes/apps/production/frontend.yaml',
    'kubernetes/apps/production/notification-worker.yaml',
    'kubernetes/clusters/production/image-promotion-state.json',
}


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def validate_base(repo, expected, actual):
    if expected != actual or git(repo, 'rev-parse', 'HEAD') != expected:
        raise RuntimeError('main ha cambiado; volver a ejecutar')
    return expected


def same_proposal(repo, previous, candidate):
    if not previous:
        return False
    return (git(repo, 'rev-parse', previous + '^{tree}') == git(repo, 'rev-parse', candidate + '^{tree}')
            and git(repo, 'rev-parse', previous + '^') == git(repo, 'rev-parse', candidate + '^'))


def validate_previous(repo, main, previous):
    if not previous:
        return
    fields = git(repo, 'show', '-s', '--format=%P%n%ae%n%ce%n%s', previous).splitlines()
    if len(fields) != 4 or len(fields[0].split()) != 1 or fields[1:] != [BOT, BOT, MESSAGE]:
        raise RuntimeError('rama de promoción contiene trabajo ajeno')
    parent = fields[0]
    try:
        subprocess.check_call(['git', '-C', str(repo), 'merge-base', '--is-ancestor', parent, main], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as error:
        raise RuntimeError('base anterior de promoción no pertenece a main') from error
    paths = set(git(repo, 'diff', '--name-only', parent, previous).splitlines())
    if not paths or not paths <= ALLOWED:
        raise RuntimeError('rama de promoción contiene archivos ajenos')


if __name__ == '__main__':
    import sys
    try:
        if sys.argv[1] == 'previous':
            validate_previous(Path('.'), sys.argv[2], sys.argv[3])
        elif sys.argv[1] == 'same':
            sys.exit(0 if same_proposal(Path('.'), sys.argv[2], sys.argv[3]) else 1)
        elif sys.argv[1] == 'base':
            validate_base(Path('.'), sys.argv[2], sys.argv[3])
        else:
            raise ValueError('comando desconocido')
    except (RuntimeError, subprocess.CalledProcessError, ValueError, IndexError) as error:
        sys.exit(str(error))
