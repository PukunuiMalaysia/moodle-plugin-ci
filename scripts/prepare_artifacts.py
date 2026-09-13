#!/usr/bin/env python3
"""Verify and unpack centrally prepared runtime artifacts without credentials."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile


def checksum(path, expected):
    if not re.fullmatch('[0-9a-f]{64}', expected) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Validation artifact checksum mismatch')


def extract(archive, destination, component):
    if not re.fullmatch('[a-z]+_[a-z0-9_]+', component):
        raise ValueError('Invalid component')
    prefix = component.split('_', 1)[1]
    with zipfile.ZipFile(archive) as source:
        names = set()
        for item in source.infolist():
            path = PurePosixPath(item.filename)
            mode = item.external_attr >> 16
            if (not path.parts or path.parts[0] != prefix or len(path.parts) < 2 or path.is_absolute()
                    or any(p in {'.', '..', '.git', '.github'} for p in path.parts)
                    or '\\' in item.filename or item.filename in names
                    or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR})):
                raise ValueError('Unsafe archive member')
            names.add(item.filename)
        if prefix + '/version.php' not in names:
            raise ValueError('Plugin version.php missing from archive')
        source.extractall(destination)
    return destination / prefix


def main():
    bundle = Path('validation-artifacts')
    checksum(bundle / 'manifest.json', os.environ['BUNDLE_SHA256'])
    manifest = json.loads((bundle / 'manifest.json').read_text())
    if manifest['component'] != os.environ['COMPONENT'] or manifest['commit'] != os.environ['RELEASE_SHA']:
        raise ValueError('Artifact source identity mismatch')
    if manifest['release_sha256'] != os.environ['PACKAGE_SHA256']:
        raise ValueError('Artifact release checksum differs from requested release')
    checksum(bundle / 'release.zip', manifest['release_sha256'])
    temp = Path(os.environ['RUNNER_TEMP'])
    shutil.copyfile(bundle / 'release.zip', temp / 'release.zip')
    # Validate the upgrade target archive before Moodle or any plugin code executes.
    release = extract(bundle / 'release.zip', temp / 'release-package', manifest['component'])
    if os.environ['INSTALLATION'] == 'fresh':
        release.rename('plugin')
    elif os.environ['INSTALLATION'] == 'upgrade':
        checksum(bundle / 'baseline.zip', manifest['baseline_sha256'])
        extract(bundle / 'baseline.zip', temp / 'baseline-package', manifest['component']).rename('plugin')
    else:
        raise ValueError('Unsupported installation mode')
    for index, dep in enumerate(manifest['dependencies']):
        if dep['archive'] != f'dependency-{index}.zip':
            raise ValueError('Invalid dependency archive name')
        checksum(bundle / dep['archive'], dep['sha256'])
        if not re.fullmatch('[a-z][a-z0-9_]*/[a-z][a-z0-9_]*', dep['path']):
            raise ValueError('Invalid dependency installation path')
        unpacked = extract(bundle / dep['archive'], temp / f'dependency-{index}', dep['component'])



def register_dependencies():
    import subprocess
    manifest = json.loads(Path('validation-artifacts/manifest.json').read_text())
    for index, dep in enumerate(manifest['dependencies']):
        folder = Path(os.environ['RUNNER_TEMP']) / f'dependency-{index}' / dep['component'].split('_', 1)[1]
        # add-plugin accepts Git sources; create an offline commit of verified bytes.
        subprocess.run(['git', '-C', str(folder), 'init', '-q'], check=True)
        subprocess.run(['git', '-C', str(folder), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(folder), '-c', 'user.name=Validation',
                        '-c', 'user.email=validation@example.invalid', 'commit', '-qm', 'Verified dependency'], check=True)
        subprocess.run(['moodle-plugin-ci', 'add-plugin', '--clone', str(folder.resolve())], check=True)


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['register-dependencies']:
        register_dependencies()
    else:
        main()
