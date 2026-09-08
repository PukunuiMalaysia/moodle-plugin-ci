#!/usr/bin/env python3
"""Deterministic, committed-files-only Moodle packaging. Never executes plugin PHP."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def metadata(data, component):
    text = data.decode("utf-8")
    values = {}
    patterns = {
        "component": r"['\"]([a-z]+_[a-z0-9_]+)['\"]",
        "version": r"([0-9]{10})",
        "release": r"['\"]([^'\"\r\n]+)['\"]",
        "maturity": r"(MATURITY_STABLE)",
        "requires": r"([0-9]{10})",
        "supported": r"(\[\s*[0-9]{3}\s*,\s*[0-9]{3}\s*\])",
    }
    # Comments are ignored, but expressions and duplicate assignments fail closed.
    text = re.sub(r"/\*.*?\*/|//[^\n]*|#[^\n]*", "", text, flags=re.S)
    for key, pattern in patterns.items():
        matches = re.findall(r"\$plugin->" + key + r"\s*=\s*" + pattern + r"\s*;", text)
        if len(matches) != 1 or len(re.findall(r"\$plugin->" + key + r"\s*=", text)) != 1:
            raise ValueError(f"Require one literal, valid {key} in version.php")
        values[key] = matches[0]
    if values["component"] != component:
        raise ValueError("Wrong plugin component")
    values["supported"] = json.loads(values["supported"])
    if values["supported"][0] > values["supported"][1]:
        raise ValueError("Invalid supported Moodle range")
    return values


def build(repo, sha, component, destination):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Full commit SHA required")
    if not re.fullmatch(r"[a-z]+_[a-z0-9_]+", component):
        raise ValueError("Invalid component")
    declaration = json.loads(git(repo, "show", f"{sha}:.marketplace-release.json"))
    include = declaration.get("package", {}).get("include", [])
    if not include or any(not isinstance(p, str) or p.startswith("/") or
                          ".." in PurePosixPath(p).parts or "*" in p for p in include):
        raise ValueError("Reviewed literal package allowlist required")
    entries = []
    for row in git(repo, "ls-tree", "-rz", sha).split(b"\0"):
        if not row:
            continue
        attributes, path_bytes = row.split(b"\t", 1)
        path = path_bytes.decode("utf-8")
        parts = PurePosixPath(path).parts
        if not any(path == p or (p.endswith("/") and path.startswith(p)) for p in include):
            continue
        mode, kind, oid = attributes.decode().split()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError(f"Symlinks and submodules forbidden: {path}")
        if any(p.startswith(".") or p in {"..", "AGENTS.md", "AGENTS.override.md", "node_modules", "vendor", "docs"} for p in parts):
            raise ValueError(f"Forbidden package path: {path}")
        if path.startswith("/") or "\\" in path or any(ord(c) < 32 for c in path):
            raise ValueError("Unsafe package path")
        if Path(path).suffix.lower() in {".pem", ".key", ".p12", ".zip"}:
            raise ValueError(f"Forbidden package type: {path}")
        data = git(repo, "cat-file", "blob", oid)
        if b"-----BEGIN PRIVATE KEY-----" in data or b"-----BEGIN RSA PRIVATE KEY-----" in data:
            raise ValueError("Private key detected")
        entries.append((path, data))
    files = dict(entries)
    if not {"version.php", f"lang/en/{component}.php", "LICENSE"} <= files.keys():
        raise ValueError("Package requires version.php, English strings and LICENSE")
    values = metadata(files["version.php"], component)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if Path(repo).resolve() in destination.resolve().parents:
        raise ValueError("Release ZIP must be outside the source checkout")
    prefix = component.split("_", 1)[1]
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for path, data in sorted(entries):
            entry = zipfile.ZipInfo(f"{prefix}/{path}", date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    inventory = [{"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                 for path, data in sorted(entries)]
    return {"commit": sha, "metadata": values, "declaration": declaration,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "files": inventory}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--component", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.repo, args.sha, args.component, args.output)
    args.output.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["sha256"])
