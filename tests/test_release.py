"""Public packaging invariants only; the workflow also runs the derived image."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('verify_public_release',ROOT/'scripts/verify_release.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ReleaseTests(unittest.TestCase):
    def test_reviewed_manifest_and_packaging(self):
        self.assertTrue(module.verify()['verified'])

    def test_versioned_registry_and_migration_boundary(self):
        config=json.loads((ROOT/'echomuse_household_voice/config.json').read_text())
        self.assertEqual(config['image'],'ghcr.io/kidhasmoxy/echomuse-household-voice')
        self.assertNotEqual(config['slug'],'controller')
        self.assertEqual(config['environment']['DB_PATH'],'/data/echomuse.db')
        self.assertEqual(config['backup'],'cold')
        self.assertEqual(config['map'],[{'type':'ssl'}])
        self.assertTrue(config['panel_admin'])
        self.assertFalse(config['options']['external_audio_enabled'])
        self.assertEqual(config['options']['external_audio_devices'],[])
        self.assertEqual(config['schema']['external_audio_devices'][0]['key_hex'],'password')

    def test_minimal_image_overlay(self):
        docker=(ROOT/'echomuse_household_voice/Dockerfile').read_text()
        self.assertEqual(sum(line.startswith('COPY src/') for line in docker.splitlines()),4)
        self.assertNotIn('\nRUN ',docker)
        self.assertNotIn('\nCMD ',docker)
        self.assertNotIn('\nENTRYPOINT ',docker)
        self.assertIn('Copyright (c) 2026 Wil Bowes',(ROOT/'LICENSE').read_text())


if __name__=='__main__':unittest.main()
