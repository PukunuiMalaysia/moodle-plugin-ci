#!/usr/bin/env python3
"""Exercise a real baseline database upgrade before rebuilding test databases."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid
import zipfile


def php(script, *args):
    subprocess.run(["php", str(script), *args], check=True)


def main():
    component = os.environ["COMPONENT"]
    if not re.fullmatch(r"[a-z]+_[a-z0-9_]+", component):
        raise ValueError("Invalid component")
    root = Path("moodle/public") if Path("moodle/public").is_dir() else Path("moodle")
    php(root / "admin/cli/install_database.php", "--agree-license", "--adminuser=releaseadmin",
        f"--adminpass={uuid.uuid4().hex}Aa1!", "--adminemail=release@example.invalid",
        "--fullname=Release validation", "--shortname=release")
    # Ask Moodle itself for the component path; no type-to-directory guesswork.
    code = ('define("CLI_SCRIPT", true); require "moodle/config.php"; '
            '$parts = explode("_", getenv("COMPONENT"), 2); '
            'echo core_component::get_plugin_directory($parts[0], $parts[1]);')
    target = Path(subprocess.check_output(["php", "-r", code], text=True).strip()).resolve()
    if root.resolve() not in target.parents or not (target / "version.php").is_file():
        raise ValueError("Could not safely identify installed plugin")
    backup = Path(os.environ["RUNNER_TEMP"]) / "baseline-installed"
    target.rename(backup)
    with zipfile.ZipFile(Path(os.environ["RUNNER_TEMP"]) / "release.zip") as archive:
        archive.extractall(target.parent)
    if (backup / ".moodle-plugin-ci.yml").is_file():
        shutil.copy2(backup / ".moodle-plugin-ci.yml", target / ".moodle-plugin-ci.yml")
    php(root / "admin/cli/upgrade.php", "--non-interactive")
    php(root / "admin/tool/phpunit/cli/init.php")
    php(root / "admin/tool/behat/cli/init.php", "--disable-composer", "--scss-deprecations")


if __name__ == "__main__":
    main()
