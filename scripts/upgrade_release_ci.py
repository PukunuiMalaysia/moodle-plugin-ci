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
    result = subprocess.run(["php", str(script), *args])
    if result.returncode:
        # Do not include generated test administrator credentials in a traceback.
        raise RuntimeError(f"PHP validation failed: {script}")


def cli_paths(base):
    webroot = base / "public" if (base / "public").is_dir() else base
    paths = {
        "install": base / "admin/cli/install_database.php",
        "upgrade": base / "admin/cli/upgrade.php",
        "phpunit": webroot / "admin/tool/phpunit/cli/init.php",
        "behat": webroot / "admin/tool/behat/cli/init.php",
    }
    if any(not path.is_file() for path in paths.values()):
        raise ValueError("Unsupported Moodle CLI layout")
    return webroot, paths


def main():
    component = os.environ["COMPONENT"]
    if not re.fullmatch(r"[a-z]+_[a-z0-9_]+", component):
        raise ValueError("Invalid component")
    root, paths = cli_paths(Path("moodle"))
    php(paths["install"], "--agree-license", "--adminuser=releaseadmin",
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
    php(paths["upgrade"], "--non-interactive")
    php(paths["phpunit"])
    php(paths["behat"], "--disable-composer", "--scss-deprecations")


if __name__ == "__main__":
    main()
