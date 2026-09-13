import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('artifacts', Path(__file__).resolve().parents[1] / 'scripts/prepare_artifacts.py')
artifacts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(artifacts)


class ArtifactTests(unittest.TestCase):
    def test_safe_archive_and_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'plugin.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('example/version.php', '<?php')
            artifacts.checksum(archive, hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertTrue((artifacts.extract(archive, root / 'out', 'block_example') / 'version.php').is_file())
            with self.assertRaises(ValueError): artifacts.checksum(archive, '0' * 64)

    def test_traversal_other_roots_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ['example/../../escape', 'other/version.php', '/example/version.php', 'example/.git/config', 'example\\bad']:
                archive = root / 'bad.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr('example/version.php', '<?php')
                    z.writestr(path, 'bad')
                with self.assertRaises(ValueError): artifacts.extract(archive, root / 'out', 'block_example')
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('example/version.php', '<?php')
                info = zipfile.ZipInfo('example/link')
                info.create_system = 3
                info.external_attr = 0o120777 << 16
                z.writestr(info, '../escape')
            with self.assertRaises(ValueError): artifacts.extract(archive, root / 'out', 'block_example')

if __name__ == '__main__': unittest.main()
