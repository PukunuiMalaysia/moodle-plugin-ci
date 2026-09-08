#!/usr/bin/env python3
"""Install only deterministic ZIP contents, retaining an explicit upgrade baseline."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import zipfile

from package_release import build


def main():
    for field in ("RELEASE_SHA", "TOOLS_SHA"):
        if not re.fullmatch(r"[0-9a-f]{40}", os.environ[field]):
            raise ValueError(f"Full SHA required: {field}")
    if not re.fullmatch(r"[0-9a-f]{64}", os.environ["PACKAGE_SHA256"]):
        raise ValueError("Expected package checksum required")
    archive = Path(os.environ["RUNNER_TEMP"]) / "release.zip"
    result = build(Path("plugin"), os.environ["RELEASE_SHA"], os.environ["COMPONENT"], archive)
    if result["sha256"] != os.environ["PACKAGE_SHA256"]:
        raise ValueError("CI ZIP differs from publisher ZIP")
    Path("plugin").rename("release-source")
    with zipfile.ZipFile(archive) as package:
        package.extractall(Path(os.environ["RUNNER_TEMP"]) / "release-package")
    unpacked = Path(os.environ["RUNNER_TEMP"]) / "release-package" / os.environ["COMPONENT"].split("_", 1)[1]
    if os.environ["INSTALLATION"] == "fresh":
        unpacked.rename("plugin")
    elif os.environ["INSTALLATION"] == "upgrade":
        sha = os.environ["UPGRADE_SHA"]
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or sha == os.environ["RELEASE_SHA"]:
            raise ValueError("Reviewed previous full commit SHA required")
        subprocess.run(["git", "clone", "--no-hardlinks", "release-source", "plugin"], check=True)
        subprocess.run(["git", "-C", "plugin", "checkout", "--detach", sha], check=True)
    else:
        raise ValueError("Unknown installation mode")


if __name__ == "__main__":
    main()
