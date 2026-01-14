#!/usr/bin/env python3
"""
Mindset Rebranding Script

This script automates the rebranding of CyberPanel to Mindset.
It updates branding strings across the codebase while preserving functionality.

Usage:
    python scripts/rebrand.py --dry-run    # Preview changes
    python scripts/rebrand.py              # Apply changes
    python scripts/rebrand.py --revert     # Revert changes (from backup)
"""

import os
import re
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Set

# Base path
BASE_PATH = Path(__file__).parent.parent

# Branding replacements (order matters - more specific first)
REPLACEMENTS = {
    # Product names
    'CyberPanel': 'Mindset',
    'Cyber Panel': 'Mindset',
    'CyberCP': 'Mindset',
    'CYBERPANEL': 'MINDSET',
    'cyberpanel': 'mindset',
    'cybercp': 'mindset',
    'cyber-panel': 'mindset',
    'cyberPanel': 'mindset',

    # URLs and domains (be careful with these)
    'cyberpanel.net': 'mindset.sh',
    'docs.cyberpanel.net': 'docs.mindset.sh',

    # Package names
    'cyberpanel-': 'mindset-',
}

# File extensions to process
PROCESSABLE_EXTENSIONS = {
    '.py', '.html', '.htm', '.js', '.jsx', '.ts', '.tsx',
    '.css', '.scss', '.less', '.json', '.yaml', '.yml',
    '.md', '.txt', '.rst', '.sh', '.bash', '.conf',
    '.service', '.xml', '.svg', '.ini', '.cfg', '.toml',
}

# Directories to skip
SKIP_DIRECTORIES = {
    'venv', '.git', 'node_modules', '__pycache__',
    '.pytest_cache', '.mypy_cache', 'dist', 'build',
    'eggs', '*.egg-info', '.tox', '.coverage',
}

# Files to skip (exact matches or patterns)
SKIP_FILES = {
    'rebrand.py',  # Don't rebrand ourselves
    'migration_report.json',
    '.gitignore',
    'package-lock.json',
    'yarn.lock',
    'composer.lock',
}

# Specific files that need special handling
SPECIAL_FILES = {
    'version.txt': lambda content: update_version(content),
    'CyberCP/settings.py': lambda content: update_settings(content),
}


class RebrrandingStats:
    """Track rebranding statistics"""

    def __init__(self):
        self.files_processed = 0
        self.files_modified = 0
        self.total_replacements = 0
        self.errors = []
        self.changes = {}  # file -> list of changes

    def add_change(self, file_path: str, changes: List[str]):
        self.files_processed += 1
        if changes:
            self.files_modified += 1
            self.total_replacements += len(changes)
            self.changes[file_path] = changes

    def add_error(self, file_path: str, error: str):
        self.errors.append((file_path, error))

    def to_dict(self) -> dict:
        return {
            'files_processed': self.files_processed,
            'files_modified': self.files_modified,
            'total_replacements': self.total_replacements,
            'errors': self.errors,
            'changes_summary': {k: len(v) for k, v in self.changes.items()},
        }


def should_skip_path(path: Path) -> bool:
    """Check if path should be skipped"""
    path_str = str(path)

    # Check directory patterns
    for skip_dir in SKIP_DIRECTORIES:
        if skip_dir in path_str.split(os.sep):
            return True

    # Check file patterns
    if path.name in SKIP_FILES:
        return True

    return False


def should_process_file(path: Path) -> bool:
    """Check if file should be processed"""
    if not path.is_file():
        return False

    if should_skip_path(path):
        return False

    # Check extension
    if path.suffix.lower() not in PROCESSABLE_EXTENSIONS:
        return False

    return True


def update_version(content: str) -> str:
    """Update version.txt with Mindset branding"""
    lines = content.strip().split('\n')
    # First line is version number, keep it
    # Add Mindset branding
    return f"{lines[0]}\nMindset Laravel Hosting Platform"


def update_settings(content: str) -> str:
    """Update Django settings.py"""
    # Update ROOT_URLCONF
    content = content.replace("ROOT_URLCONF = 'CyberCP.urls'", "ROOT_URLCONF = 'mindset.urls'")

    # Update WSGI_APPLICATION
    content = content.replace("WSGI_APPLICATION = 'CyberCP.wsgi.application'",
                              "WSGI_APPLICATION = 'mindset.wsgi.application'")

    return content


def apply_replacements(content: str) -> Tuple[str, List[str]]:
    """Apply all replacements to content"""
    changes = []

    for old, new in REPLACEMENTS.items():
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            changes.append(f"'{old}' -> '{new}' ({count}x)")

    return content, changes


def process_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, List[str]]:
    """Process a single file for rebranding"""
    try:
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with latin-1 encoding
            content = file_path.read_text(encoding='latin-1')

        original_content = content

        # Check for special file handling
        rel_path = str(file_path.relative_to(BASE_PATH))
        if rel_path in SPECIAL_FILES:
            content = SPECIAL_FILES[rel_path](content)

        # Apply standard replacements
        content, changes = apply_replacements(content)

        # Write if changed and not dry run
        if content != original_content:
            if not dry_run:
                file_path.write_text(content, encoding='utf-8')
            return True, changes

        return False, []

    except Exception as e:
        raise Exception(f"Error processing {file_path}: {e}")


def rename_directories(base_path: Path, dry_run: bool = False) -> List[str]:
    """Rename CyberCP directory to mindset"""
    renames = []

    # Main CyberCP directory
    cybercp_dir = base_path / 'CyberCP'
    if cybercp_dir.exists():
        mindset_dir = base_path / 'mindset'
        if not dry_run:
            # Copy instead of rename to preserve during development
            if not mindset_dir.exists():
                shutil.copytree(cybercp_dir, mindset_dir)
        renames.append(f"CyberCP/ -> mindset/")

    return renames


def create_backup(base_path: Path) -> Path:
    """Create a backup before rebranding"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = base_path / f'.rebrand_backup_{timestamp}'

    # Only backup key files, not the entire directory
    key_files = [
        'CyberCP/settings.py',
        'CyberCP/urls.py',
        'CyberCP/wsgi.py',
        'version.txt',
    ]

    backup_dir.mkdir(exist_ok=True)

    for file_path in key_files:
        src = base_path / file_path
        if src.exists():
            dst = backup_dir / file_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    return backup_dir


def main():
    parser = argparse.ArgumentParser(description='Rebrand CyberPanel to Mindset')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying them')
    parser.add_argument('--revert', type=str, metavar='BACKUP_DIR',
                        help='Revert from a backup directory')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output')
    parser.add_argument('--output', '-o', type=str,
                        help='Output report to JSON file')

    args = parser.parse_args()

    print("=" * 60)
    print("  MINDSET REBRANDING TOOL")
    print("=" * 60)
    print()

    if args.revert:
        # Revert from backup
        backup_path = Path(args.revert)
        if not backup_path.exists():
            print(f"ERROR: Backup directory not found: {backup_path}")
            sys.exit(1)

        print(f"Reverting from backup: {backup_path}")
        for file_path in backup_path.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(backup_path)
                target = BASE_PATH / rel_path
                shutil.copy2(file_path, target)
                print(f"  Restored: {rel_path}")

        print("\nRevert completed!")
        sys.exit(0)

    # Normal rebranding
    stats = RebrrandingStats()

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made\n")
    else:
        # Create backup
        backup_dir = create_backup(BASE_PATH)
        print(f"Backup created: {backup_dir}\n")

    # Rename directories
    print("Directory renames:")
    dir_renames = rename_directories(BASE_PATH, args.dry_run)
    for rename in dir_renames:
        print(f"  {rename}")
    print()

    # Process files
    print("Processing files...")
    for file_path in BASE_PATH.rglob('*'):
        if not should_process_file(file_path):
            continue

        try:
            modified, changes = process_file(file_path, args.dry_run)
            stats.add_change(str(file_path.relative_to(BASE_PATH)), changes)

            if modified and args.verbose:
                print(f"  Modified: {file_path.relative_to(BASE_PATH)}")
                for change in changes:
                    print(f"    - {change}")

        except Exception as e:
            stats.add_error(str(file_path.relative_to(BASE_PATH)), str(e))
            if args.verbose:
                print(f"  ERROR: {file_path.relative_to(BASE_PATH)}: {e}")

    # Print summary
    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Files processed:    {stats.files_processed}")
    print(f"  Files modified:     {stats.files_modified}")
    print(f"  Total replacements: {stats.total_replacements}")
    print(f"  Errors:             {len(stats.errors)}")
    print()

    if stats.errors:
        print("Errors:")
        for file_path, error in stats.errors:
            print(f"  {file_path}: {error}")
        print()

    # Output report if requested
    if args.output:
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': args.dry_run,
            'stats': stats.to_dict(),
            'replacements': REPLACEMENTS,
        }
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {args.output}")

    if args.dry_run:
        print("This was a dry run. Run without --dry-run to apply changes.")
    else:
        print("Rebranding completed!")
        print(f"To revert, run: python scripts/rebrand.py --revert {backup_dir}")


if __name__ == '__main__':
    main()
