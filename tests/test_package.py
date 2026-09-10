import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package',ROOT/'scripts/package.py');package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'build').mkdir(exist_ok=True)
        environment=mock.patch.dict(os.environ,{'SOURCE_DATE_EPOCH':'1789084800'});environment.start();self.addCleanup(environment.stop)

    def test_exact_local_ultra_boundary_and_external_obsidian(self):
        report=package.compatibility()
        self.assertEqual(set(report['dependencies']),{'agent-sphere','redixs','comm','obsidian','mote-vault-sync','mote-vault-syncd','init-system-helpers'})
        self.assertEqual(report['dependencies']['redixs'],'4.1.0-1')
        self.assertEqual(report['dependencies']['comm'],'1.0.0-1')
        self.assertFalse(report['external_provisioning']['obsidian']['rehost_on_motebus'])
        self.assertFalse(report['installable']);self.assertFalse(report['readiness'])

    def test_fake_aliases_manager_or_wrong_owner_cannot_enter_apps(self):
        for field,value in [('Provides','comm'),('Recommends','sphere-manager'),('Suggests','model-node'),
                            ('Depends',package.control()['Depends']+', agos'),
                            ('Depends',package.control()['Depends'].replace('comm','agos'))]:
            altered={**package.control(),field:value}
            with self.subTest(field=field,value=value),mock.patch.object(package,'control',return_value=altered):
                with self.assertRaises(ValueError):package.check_control(altered)

    def test_reproducible_declarative_target_artifact(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as temporary:
            first=package.build(Path(temporary)/'a');second=package.build(Path(temporary)/'b')
            self.assertEqual(first.read_bytes(),second.read_bytes())

    def test_modified_hooks_fake_runtime_and_configuration_are_rejected(self):
        for extra in ['DEBIAN/postinst','usr/bin/comm','etc/agent-ultra.conf']:
            with self.subTest(extra=extra),tempfile.TemporaryDirectory(dir=ROOT/'build') as temporary:
                base=Path(temporary);original=package.build(base/'clean');stage=base/'stage'
                subprocess.run(['dpkg-deb','--raw-extract',str(original),str(stage)],check=True,capture_output=True)
                file=stage/extra;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('invalid\n');file.chmod(0o755)
                bad=base/'bad.deb';subprocess.run(['dpkg-deb','--build','--root-owner-group',str(stage),str(bad)],check=True,capture_output=True)
                with self.assertRaises(ValueError):package.verify(bad)
