#!/usr/bin/env python3
"""Check the exact Git index for public-source boundaries and common leak patterns."""
from pathlib import Path, PurePosixPath
import argparse
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXACT = {
    '.gitignore', '.gitattributes', 'AGENTS.md', 'README.md', 'CONTRIBUTING.md', 'LICENSE',
    '.github/workflows/validate.yml', 'scripts/check_public_repo.py', 'tests/test_workflow.py',
    'skills/photo-edit-master/SKILL.md', 'workflow/README.md', 'workflow/build_suite.py',
    'workflow/build_catalogue.py', 'workflow/verify_collection.py', 'workflow/catalogue.css',
    'workflow/selection.example.json', 'workflow/evaluation-template.json',
    'assets/readme-hero.svg',
    'docs/getting-started.md', 'docs/ecosystem.md',
    'CHANGELOG.md', 'skills/photo-style-builder/SKILL.md',
    'review/README.md', 'review/server.py', 'review/cli.py', 'review/import_legacy.py',
    'review/package.json', 'review/tests/fixture.py', 'review/tests/store.test.mjs', 'review/tests/sphere.test.mjs',
    'review/tests/compare.test.mjs', 'review/tests/sequence.test.mjs',
    'tests/test_review.py', 'tests/test_review_import.py',
}
PATTERNS = {
    'personal absolute path': re.compile(r'/(?:Users|home|Volumes)/[^/\s]+/'),
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'credential in URL': re.compile(r'https?://[^\s/@:]+:[^\s/@]+@'),
    'assigned credential': re.compile(
        r'''(?i)["']?(?:api[_-]?key|access[_-]?token|password|client[_-]?secret)["']?\s*[:=]\s*["'][A-Za-z0-9+/_.=-]{20,}["']'''),
}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def check(working_tree=False):
    errors, count, total = [], 0, 0
    entries = git('ls-files', '--stage', '-z').split(b'\0')
    if working_tree:
        names = sorted(set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0')) - {b''})
        entries = [b'100644 working-tree 0\t' + name for name in names]
    for entry in entries:
        if not entry:
            continue
        metadata, raw_path = entry.split(b'\t', 1)
        mode, oid, stage = metadata.decode().split()
        name = raw_path.decode('utf-8')
        path = PurePosixPath(name)
        count += 1
        allowed_reference = (
            path.parent in (PurePosixPath('skills/photo-edit-master/references'),
                            PurePosixPath('skills/photo-style-builder/references'))
            and path.suffix == '.md' and not path.name.startswith('.')
        )
        allowed_web = (
            path.parent in (PurePosixPath('review/web'), PurePosixPath('review/web/panels'))
            and path.suffix in {'.js', '.css', '.html', '.svg'} and not path.name.startswith('.')
        )
        if name not in EXACT and not allowed_reference and not allowed_web:
            errors.append((name, 'outside public source allowlist'))
        if mode not in {'100644', '100755'} or stage != '0':
            errors.append((name, 'symlink, nested repository, or unresolved merge entry'))
            continue
        if working_tree:
            local = ROOT / name
            if not local.exists():
                continue
            if local.is_symlink() or not local.is_file():
                errors.append((name, 'symlink or non-file'))
                continue
            size = local.stat().st_size
        else:
            size = int(git('cat-file', '-s', oid))
        total += size
        if size > 1024 * 1024:
            errors.append((name, 'larger than the 1 MiB public source limit'))
            continue
        blob = local.read_bytes() if working_tree else git('cat-file', 'blob', oid)
        try:
            text = blob.decode('utf-8')
        except UnicodeDecodeError:
            errors.append((name, 'binary file'))
            continue
        if '\x00' in text:
            errors.append((name, 'binary content'))
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                errors.append((name, label))
    if not count:
        errors.append(('(index)', 'no staged/tracked files; stage reviewed source first'))
    if errors:
        for name, reason in errors:
            # Never echo matched content, which could itself contain credentials.
            print(f'FAIL: {name}: {reason}', file=sys.stderr)
        return 1
    print(f'Public {"working tree" if working_tree else "index"} check passed: {count} text files, {total:,} bytes.')
    print('Checked source boundaries, blob sizes, and common credential/private-path patterns.')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--working-tree', action='store_true', help='Check tracked and unignored source without staging it')
    sys.exit(check(parser.parse_args().working_tree))
