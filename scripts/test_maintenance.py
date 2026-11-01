"""Offline render invariants; never contacts Kubernetes."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(path):
    return subprocess.run(['kubectl', 'kustomize', str(ROOT / path)],
                          check=True, capture_output=True, text=True, encoding='utf-8').stdout


def resources(text):
    result = {}
    for doc in re.split(r'^---\s*$', text, flags=re.M):
        kind = re.search(r'^kind: (.+)$', doc, re.M)
        metadata = re.search(r'^metadata:\n((?:[ \t].*\n)+)', doc, re.M)
        if not kind or not metadata:
            continue
        name = re.search(r'^  name: (.+)$', metadata.group(1), re.M)
        namespace = re.search(r'^  namespace: (.+)$', metadata.group(1), re.M)
        if name:
            key = (kind.group(1), namespace.group(1) if namespace else '', name.group(1))
            if key in result:
                raise AssertionError(f'duplicate resource {key}')
            result[key] = doc
    return result


class MaintenanceRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.normal = resources(render('kubernetes/apps/production'))
        cls.gate = resources(render('kubernetes/apps/maintenance-gate'))
        cls.stopped = resources(render('kubernetes/apps/maintenance-stopped'))
        cls.cluster = render('kubernetes/clusters/production')

    def test_inventory_is_identical(self):
        self.assertEqual(self.normal.keys(), self.gate.keys())
        self.assertEqual(self.normal.keys(), self.stopped.keys())

    def test_gate_all_routes_and_restart(self):
        config = ('ConfigMap', 'beciencia', 'caddy-ingress-config')
        deployment = ('Deployment', 'beciencia', 'caddy-ingress')
        for state in (self.gate, self.stopped):
            self.assertIn('respond ', state[config])
            self.assertIn(' 503', state[config])
            self.assertNotIn('reverse_proxy', state[config])
            self.assertIn('beciencia.es/caddy-config-mode: maintenance-v1', state[deployment])
        self.assertIn('reverse_proxy', self.normal[config])
        self.assertNotIn('beciencia.es/caddy-config-mode', self.normal[deployment])
        self.assertNotIn('beciencia.es/caddy-config-mode', self.cluster)
        cluster_resources = resources(self.cluster)
        self.assertIn('reverse_proxy', cluster_resources[config])
        self.assertNotIn(' 503', cluster_resources[config])

    def test_both_workloads_stopped_only_in_stopped_overlay(self):
        for name in ('backend', 'notification-worker'):
            key = ('Deployment', 'beciencia', name)
            self.assertRegex(resources(self.cluster)[key], r'(?m)^  replicas: 1$')
            for state, expected in ((self.normal, 1), (self.gate, 1), (self.stopped, 0)):
                self.assertRegex(state[key], rf'(?m)^  replicas: {expected}$')
            normal_image = re.search(r'^\s+image: (\S+)', self.normal[key], re.M)
            stopped_image = re.search(r'^\s+image: (\S+)', self.stopped[key], re.M)
            self.assertIsNotNone(normal_image)
            self.assertIsNotNone(stopped_image)
            if normal_image and stopped_image:
                self.assertEqual(normal_image.group(1), stopped_image.group(1))


if __name__ == '__main__':
    unittest.main()
