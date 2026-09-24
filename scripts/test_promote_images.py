import importlib.util
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
