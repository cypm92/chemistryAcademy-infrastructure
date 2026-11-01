import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('promotion_branch', Path(__file__).with_name('promotion_branch.py'))


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


class BranchTests(unittest.TestCase):
    def test_proposal_starts_from_current_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, 'init', '-q')
            git(repo, 'config', 'user.name', 'Test')
            git(repo, 'config', 'user.email', 'test@example.com')
            (repo / 'image').write_text('old')
            git(repo, 'add', 'image')
            git(repo, 'commit', '-qm', 'main')
            main = git(repo, 'rev-parse', 'HEAD')
            self.assertTrue(SPEC.loader is not None)
            module = importlib.util.module_from_spec(SPEC)
            SPEC.loader.exec_module(module)
            self.assertEqual(module.validate_base(repo, main, main), main)
            with self.assertRaisesRegex(RuntimeError, 'main'):
                module.validate_base(repo, main, '0' * 40)

    def test_existing_bot_proposal_and_idempotence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, 'init', '-q')
            git(repo, 'config', 'user.name', 'Bot')
            git(repo, 'config', 'user.email', 'beciencia-promotion[bot]@users.noreply.github.com')
            path = repo / 'kubernetes/apps/production/backend.yaml'
            path.parent.mkdir(parents=True)
            path.write_text('old')
            git(repo, 'add', '.')
            git(repo, 'commit', '-qm', 'main')
            main = git(repo, 'rev-parse', 'HEAD')
            path.write_text('new')
            git(repo, 'commit', '-qam', 'Promote published main images')
            previous = git(repo, 'rev-parse', 'HEAD')
            module = importlib.util.module_from_spec(SPEC)
            SPEC.loader.exec_module(module)
            module.validate_previous(repo, main, previous)
            self.assertTrue(module.same_proposal(repo, previous, previous))
            git(repo, 'checkout', '-q', main)
            (repo / 'other').write_text('main advanced')
            git(repo, 'add', 'other')
            git(repo, 'commit', '-qm', 'advance main')
            updated_base = git(repo, 'rev-parse', 'HEAD')
            module.validate_previous(repo, updated_base, previous)
            path.write_text('newer')
            git(repo, 'commit', '-qam', 'Promote published main images')
            updated = git(repo, 'rev-parse', 'HEAD')
            self.assertEqual(git(repo, 'rev-parse', updated + '^'), updated_base)
            self.assertFalse(module.same_proposal(repo, previous, updated))
            module.validate_previous(repo, updated_base, updated)

    def test_existing_branch_foreign_author_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, 'init', '-q')
            git(repo, 'config', 'user.name', 'Human')
            git(repo, 'config', 'user.email', 'human@example.com')
            (repo / 'image').write_text('old')
            git(repo, 'add', 'image')
            git(repo, 'commit', '-qm', 'main')
            main = git(repo, 'rev-parse', 'HEAD')
            (repo / 'image').write_text('human work')
            git(repo, 'commit', '-qam', 'Promote published main images')
            previous = git(repo, 'rev-parse', 'HEAD')
            module = importlib.util.module_from_spec(SPEC)
            SPEC.loader.exec_module(module)
            with self.assertRaisesRegex(RuntimeError, 'ajeno'):
                module.validate_previous(repo, main, previous)

    def test_existing_branch_with_extra_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, 'init', '-q')
            git(repo, 'config', 'user.name', 'Bot')
            git(repo, 'config', 'user.email', 'beciencia-promotion[bot]@users.noreply.github.com')
            (repo / 'image').write_text('old')
            git(repo, 'add', 'image')
            git(repo, 'commit', '-qm', 'main')
            main = git(repo, 'rev-parse', 'HEAD')
            (repo / 'image').write_text('foreign')
            git(repo, 'commit', '-qam', 'Promote published main images')
            module = importlib.util.module_from_spec(SPEC)
            SPEC.loader.exec_module(module)
            with self.assertRaisesRegex(RuntimeError, 'ajenos'):
                module.validate_previous(repo, main, git(repo, 'rev-parse', 'HEAD'))

if __name__ == '__main__':
    unittest.main()
