import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("promote-images.py")
SPEC = importlib.util.spec_from_file_location("promote_images", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA = "a" * 40


class PromotionTests(unittest.TestCase):
    def test_replaces_only_target_image(self):
        original = (
            "image: ghcr.io/cypm92/beciencia-backend:sha-" + "b" * 40 + "\n"
            "image: ghcr.io/cypm92/beciencia-frontend:sha-" + "c" * 40 + "\n"
        )
        updated = MODULE.replace_image(original, "backend", SHA)
        self.assertIn("beciencia-backend:sha-" + SHA, updated)
        self.assertIn("beciencia-frontend:sha-" + "c" * 40, updated)

    def test_backend_promotion_updates_api_and_worker_manifests(self):
        old_backend, old_frontend = "b" * 40, "c" * 40
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backend = root / "backend.yaml"
            worker = root / "notification-worker.yaml"
            frontend = root / "frontend.yaml"
            state_file = root / "image-promotion-state.json"
            backend.write_text(f"image: ghcr.io/cypm92/beciencia-backend:sha-{old_backend}\n")
            worker.write_text(f"image: ghcr.io/cypm92/beciencia-backend:sha-{old_backend}\n")
            frontend.write_text(f"image: ghcr.io/cypm92/beciencia-frontend:sha-{old_frontend}\n")
            state_file.write_text(json.dumps({"backend": old_backend, "frontend": old_frontend}))
            apps = {
                "backend": {"repository": "chemistryAcademy-backend", "manifests": [backend, worker]},
                "frontend": {"repository": "chemistryAcademy-frontend", "manifests": [frontend]},
            }
            with patch.object(MODULE, "APPS", apps), patch.object(MODULE, "STATE", state_file), \
                 patch.object(MODULE, "published_main_sha", side_effect=[SHA, old_frontend]), \
                 patch.dict(MODULE.os.environ, {"GH_TOKEN": "test-token"}), \
                 patch("sys.argv", ["promote-images.py", "--apply"]):
                self.assertEqual(MODULE.main(), 0)
            self.assertIn(f"beciencia-backend:sha-{SHA}", backend.read_text())
            self.assertIn(f"beciencia-backend:sha-{SHA}", worker.read_text())
            self.assertEqual(json.loads(state_file.read_text())["backend"], SHA)

    def test_rejects_ambiguous_or_invalid_image(self):
        with self.assertRaises(ValueError):
            MODULE.replace_image("image: latest\n", "backend", SHA)
        with self.assertRaises(ValueError):
            MODULE.replace_image("image: latest\n", "backend", "main")

    def test_requires_successful_publish_job(self):
        repo = "chemistryAcademy-backend"
        responses = [
            {"commit": {"sha": SHA}},
            {"workflow_runs": [{
                "head_sha": SHA, "status": "completed", "conclusion": "success", "id": 123
            }]},
            {"jobs": [{"name": MODULE.PUBLISH_JOB, "conclusion": "failure"}]},
        ]
        with patch.object(MODULE, "github_get", side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, "no se publicó"):
                MODULE.published_main_sha(repo, "test-token")


if __name__ == "__main__":
    unittest.main()
