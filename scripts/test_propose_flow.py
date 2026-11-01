"""Hermetic end-to-end tests for propose-images.sh (unittest, Git and Bash)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash') or 'bash'
BRANCH = 'automation/promote-production-images'
PATHS = ('kubernetes/apps/production/backend.yaml',
         'kubernetes/apps/production/frontend.yaml',
         'kubernetes/apps/production/notification-worker.yaml',
         'kubernetes/clusters/production/image-promotion-state.json')


class ProposeFlow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='propose-flow-', dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / 'remote.git'
        self.repo = self.root / 'checkout'
        self.state = self.root / 'state'
        self.state.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.env = os.environ.copy()
        self.env.update(GITHUB_REPOSITORY='example/project', GH_STATE=self.state.as_posix(),
                        GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='file',
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'])
        self.git('init', '--bare', str(self.remote), cwd=self.root)
        self.git('init', '-b', 'main', str(self.repo), cwd=self.root)
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.test')
        (self.repo / 'scripts').mkdir()
        for name in ('propose-images.sh', 'promotion_branch.py'):
            shutil.copy(ROOT / 'scripts' / name, self.repo / 'scripts' / name)
        (self.repo / 'scripts/promote-images.py').write_text(
            "import os\nfrom pathlib import Path\np = Path('kubernetes/apps/production/backend.yaml')\np.write_text('image: ' + os.environ['IMAGE'] + '\\n')\n", encoding='utf-8')
        for name in PATHS:
            p = self.repo / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('image: original\n', encoding='utf-8')
        self.git('add', '.')
        self.git('commit', '-m', 'fixture main')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', 'origin', 'main')
        self.main = self.git('rev-parse', 'HEAD')
        # A shell executable works in both Git Bash on Windows and Linux.
        gh = self.bin / 'gh'
        gh.write_text('''#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >> "$GH_STATE/calls"
case "$1 $2" in
  'auth setup-git') exit 0 ;;
  'pr list') [ ! -f "$GH_STATE/fail-list" ] || exit 42; [ ! -f "$GH_STATE/prs" ] || cat "$GH_STATE/prs" ;;
  'api --paginate') [ ! -f "$GH_STATE/fail-api" ] || exit 43; [ ! -f "$GH_STATE/files" ] || cat "$GH_STATE/files" ;;
  'pr view')
    sha="$(git --git-dir="$GH_STATE/../remote.git" rev-parse refs/heads/automation/promote-production-images)"
    if [ -f "$GH_STATE/human-review" ]; then printf '%s\\tfalse\\t1\\t0\\t0\\n' "$sha"; else printf '%s\\tfalse\\t0\\t0\\t0\\n' "$sha"; fi ;;
  'pr create') printf '1\\tautomation/promote-production-images\\texample\\n' > "$GH_STATE/prs" ;;
  'pr close') : ;;
  *) echo "unexpected gh command: $*" >&2; exit 44 ;;
esac
''', encoding='utf-8', newline='\n')
        gh.chmod(0o755)

    def git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.repo, env=self.env,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=True).stdout.strip()

    def run_flow(self, image='new', ok=True):
        trace = self.state / 'git-trace'
        trace.write_text('', encoding='utf-8')
        env = dict(self.env, IMAGE=image, GIT_TRACE=str(trace))
        proc = subprocess.run([BASH, 'scripts/propose-images.sh'], cwd=self.repo,
                              env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        else:
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def refs(self):
        return self.git('--git-dir', str(self.remote), 'for-each-ref', '--format=%(refname) %(objectname)', cwd=self.root)

    def reset(self):
        self.git('reset', '--hard', self.main)

    def calls(self):
        path = self.state / 'calls'
        return path.read_text(encoding='utf-8').splitlines() if path.exists() else []

    def test_create_and_identical_rerun_preserves_branch_and_pr(self):
        self.run_flow()
        proposal = self.git('--git-dir', str(self.remote), 'rev-parse', 'refs/heads/' + BRANCH, cwd=self.root)
        self.assertEqual(self.git('rev-parse', proposal + '^'), self.main)
        self.assertEqual(self.git('show', proposal + ':' + PATHS[0]), 'image: new')
        self.assertEqual(sum(c.startswith('pr create ') for c in self.calls()), 1)
        self.reset()
        result = self.run_flow()
        self.assertIn('Propuesta idéntica', result.stdout)
        self.assertNotIn('built-in: git push ', (self.state / 'git-trace').read_text(encoding='utf-8'))
        self.assertEqual(self.git('--git-dir', str(self.remote), 'rev-parse', 'refs/heads/' + BRANCH, cwd=self.root), proposal)
        self.assertEqual(sum(c.startswith('pr create ') for c in self.calls()), 1)

    def test_changed_images_update_existing_pr(self):
        self.run_flow('one')
        before = self.refs()
        self.reset()
        self.run_flow('two')
        self.assertNotEqual(self.refs(), before)
        proposal = self.git('--git-dir', str(self.remote), 'rev-parse', 'refs/heads/' + BRANCH, cwd=self.root)
        self.assertEqual(self.git('rev-parse', proposal + '^'), self.main)
        self.assertEqual(self.git('show', proposal + ':' + PATHS[0]), 'image: two')
        self.assertEqual(sum(c.startswith('pr create ') for c in self.calls()), 1)

    def test_reviewed_proposal_is_never_overwritten_or_closed(self):
        self.run_flow('one')
        before = self.refs()
        self.reset()
        (self.state / 'human-review').touch()
        self.run_flow('two', ok=False)
        self.assertEqual(self.refs(), before)
        self.assertFalse(any(call.startswith('pr close ') for call in self.calls()))

    def test_overlapping_foreign_pr_blocks_all_branch_changes(self):
        (self.state / 'prs').write_text('9\tother-branch\tother-owner\n', encoding='utf-8')
        (self.state / 'files').write_text(PATHS[0] + '\n', encoding='utf-8')
        before = self.refs()
        result = self.run_flow(ok=False)
        self.assertIn('también modifica', result.stderr)
        self.assertEqual(self.refs(), before)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.main)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_stale_main_fails_closed(self):
        self.git('commit', '--allow-empty', '-m', 'advance main')
        self.git('push', 'origin', 'main')
        self.reset()
        before = self.refs()
        result = self.run_flow(ok=False)
        self.assertIn('main ha cambiado', result.stderr)
        self.assertEqual(self.refs(), before)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.main)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_gh_read_failures_block_changes(self):
        for failure in ('fail-list', 'fail-api'):
            with self.subTest(failure=failure):
                (self.state / 'prs').write_text('9\tother\tother-owner\n', encoding='utf-8')
                marker = self.state / failure
                marker.touch()
                before = self.refs()
                result = self.run_flow(ok=False)
                self.assertEqual(result.returncode, 42 if failure == 'fail-list' else 43)
                self.assertEqual(self.refs(), before)
                self.assertEqual(self.git('rev-parse', 'HEAD'), self.main)
                self.assertEqual(self.git('status', '--porcelain'), '')
                marker.unlink()


if __name__ == '__main__':
    unittest.main()
