from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.upgrade_release_ci import cli_paths, php


class ReleaseLayoutTests(unittest.TestCase):
    def test_flat_and_public_layouts(self):
        for public in (False, True):
            with self.subTest(public=public), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                webroot = base / "public" if public else base
                expected = {
                    "install": base / "admin/cli/install_database.php",
                    "upgrade": base / "admin/cli/upgrade.php",
                    "phpunit": webroot / "admin/tool/phpunit/cli/init.php",
                    "behat": webroot / "admin/tool/behat/cli/init.php",
                }
                for path in expected.values():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
                self.assertEqual(cli_paths(base), (webroot, expected))

    def test_incomplete_layout_fails_before_credentials_are_created(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                cli_paths(Path(directory))

    def test_cli_failure_does_not_echo_arguments(self):
        with patch("scripts.upgrade_release_ci.subprocess.run") as run:
            run.return_value.returncode = 1
            with self.assertRaises(RuntimeError) as caught:
                php(Path("install.php"), "--adminpass=private-value")
            self.assertNotIn("private-value", str(caught.exception))
