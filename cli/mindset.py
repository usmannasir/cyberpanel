#!/usr/bin/env python3
# Mindset CLI - Command Line Interface for Mindset Hosting Platform
# Copyright (C) 2024 Mindset Contributors
# Licensed under GPLv3

"""
Mindset CLI

A command-line interface for managing the Mindset hosting platform.

Usage:
    mindset <command> [options]

Commands:
    laravel     Laravel application management
    site        Website management
    db          Database management
    backup      Backup operations
    ai          AI services
    service     Service management
    status      System status
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_version():
    """Get Mindset version"""
    version_file = Path(__file__).parent.parent / "version.txt"
    if version_file.exists():
        try:
            data = json.loads(version_file.read_text())
            return f"{data.get('name', 'Mindset')} v{data.get('version', '1.0.0')}"
        except:
            pass
    return "Mindset v1.0.0"


class MindsetCLI:
    """Main CLI class"""

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self):
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            prog='mindset',
            description='Mindset - Laravel-Native Hosting Platform CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  mindset laravel:create example.com
  mindset laravel:deploy example.com
  mindset site:list
  mindset db:backup mydatabase
  mindset ai:analyze /path/to/logs
  mindset status

For more information, visit: https://docs.mindset.sh
            """
        )

        parser.add_argument(
            '--version', '-v',
            action='version',
            version=get_version()
        )

        parser.add_argument(
            '--json',
            action='store_true',
            help='Output in JSON format'
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Laravel commands
        self._add_laravel_commands(subparsers)

        # Site commands
        self._add_site_commands(subparsers)

        # Database commands
        self._add_db_commands(subparsers)

        # Backup commands
        self._add_backup_commands(subparsers)

        # AI commands
        self._add_ai_commands(subparsers)

        # Service commands
        self._add_service_commands(subparsers)

        # Status command
        status_parser = subparsers.add_parser('status', help='Show system status')
        status_parser.set_defaults(func=self.cmd_status)

        return parser

    def _add_laravel_commands(self, subparsers):
        """Add Laravel-related commands"""
        # laravel:create
        create = subparsers.add_parser(
            'laravel:create',
            help='Create a new Laravel application'
        )
        create.add_argument('domain', help='Domain name')
        create.add_argument('--php', default='8.3', help='PHP version (default: 8.3)')
        create.add_argument('--with-horizon', action='store_true', help='Install Laravel Horizon')
        create.add_argument('--with-octane', action='store_true', help='Install Laravel Octane')
        create.add_argument('--from-repo', help='Clone from Git repository')
        create.set_defaults(func=self.cmd_laravel_create)

        # laravel:deploy
        deploy = subparsers.add_parser(
            'laravel:deploy',
            help='Deploy a Laravel application'
        )
        deploy.add_argument('domain', help='Domain name')
        deploy.add_argument('--branch', default='main', help='Git branch (default: main)')
        deploy.add_argument('--no-migrate', action='store_true', help='Skip migrations')
        deploy.add_argument('--no-build', action='store_true', help='Skip npm build')
        deploy.set_defaults(func=self.cmd_laravel_deploy)

        # laravel:rollback
        rollback = subparsers.add_parser(
            'laravel:rollback',
            help='Rollback to previous release'
        )
        rollback.add_argument('domain', help='Domain name')
        rollback.add_argument('--releases', type=int, default=1, help='Releases to rollback')
        rollback.set_defaults(func=self.cmd_laravel_rollback)

        # laravel:artisan
        artisan = subparsers.add_parser(
            'laravel:artisan',
            help='Run artisan command'
        )
        artisan.add_argument('domain', help='Domain name')
        artisan.add_argument('artisan_command', nargs='+', help='Artisan command')
        artisan.set_defaults(func=self.cmd_laravel_artisan)

        # laravel:logs
        logs = subparsers.add_parser(
            'laravel:logs',
            help='View Laravel logs'
        )
        logs.add_argument('domain', help='Domain name')
        logs.add_argument('--lines', type=int, default=100, help='Number of lines')
        logs.add_argument('--follow', '-f', action='store_true', help='Follow log output')
        logs.set_defaults(func=self.cmd_laravel_logs)

    def _add_site_commands(self, subparsers):
        """Add site-related commands"""
        # site:list
        list_sites = subparsers.add_parser('site:list', help='List all sites')
        list_sites.set_defaults(func=self.cmd_site_list)

        # site:create
        create_site = subparsers.add_parser('site:create', help='Create a new site')
        create_site.add_argument('domain', help='Domain name')
        create_site.add_argument('--php', default='8.3', help='PHP version')
        create_site.add_argument('--ssl', action='store_true', help='Enable SSL')
        create_site.set_defaults(func=self.cmd_site_create)

        # site:delete
        delete_site = subparsers.add_parser('site:delete', help='Delete a site')
        delete_site.add_argument('domain', help='Domain name')
        delete_site.add_argument('--force', action='store_true', help='Skip confirmation')
        delete_site.set_defaults(func=self.cmd_site_delete)

    def _add_db_commands(self, subparsers):
        """Add database-related commands"""
        # db:list
        db_list = subparsers.add_parser('db:list', help='List databases')
        db_list.set_defaults(func=self.cmd_db_list)

        # db:create
        db_create = subparsers.add_parser('db:create', help='Create database')
        db_create.add_argument('name', help='Database name')
        db_create.add_argument('--user', help='Database user')
        db_create.set_defaults(func=self.cmd_db_create)

        # db:backup
        db_backup = subparsers.add_parser('db:backup', help='Backup database')
        db_backup.add_argument('name', help='Database name')
        db_backup.add_argument('--output', '-o', help='Output file')
        db_backup.set_defaults(func=self.cmd_db_backup)

    def _add_backup_commands(self, subparsers):
        """Add backup-related commands"""
        # backup:create
        backup_create = subparsers.add_parser('backup:create', help='Create backup')
        backup_create.add_argument('domain', help='Domain name')
        backup_create.add_argument('--full', action='store_true', help='Full backup')
        backup_create.set_defaults(func=self.cmd_backup_create)

        # backup:list
        backup_list = subparsers.add_parser('backup:list', help='List backups')
        backup_list.add_argument('domain', nargs='?', help='Domain name (optional)')
        backup_list.set_defaults(func=self.cmd_backup_list)

        # backup:restore
        backup_restore = subparsers.add_parser('backup:restore', help='Restore backup')
        backup_restore.add_argument('backup_id', help='Backup ID')
        backup_restore.set_defaults(func=self.cmd_backup_restore)

    def _add_ai_commands(self, subparsers):
        """Add AI-related commands"""
        # ai:analyze
        ai_analyze = subparsers.add_parser('ai:analyze', help='Analyze logs with AI')
        ai_analyze.add_argument('path', help='Path to log file or directory')
        ai_analyze.add_argument('--provider', help='AI provider (ollama, deepinfra)')
        ai_analyze.set_defaults(func=self.cmd_ai_analyze)

        # ai:explain
        ai_explain = subparsers.add_parser('ai:explain', help='Explain an error')
        ai_explain.add_argument('error', help='Error message or file')
        ai_explain.set_defaults(func=self.cmd_ai_explain)

        # ai:status
        ai_status = subparsers.add_parser('ai:status', help='AI provider status')
        ai_status.set_defaults(func=self.cmd_ai_status)

    def _add_service_commands(self, subparsers):
        """Add service-related commands"""
        # service:status
        svc_status = subparsers.add_parser('service:status', help='Service status')
        svc_status.add_argument('service', nargs='?', help='Service name')
        svc_status.set_defaults(func=self.cmd_service_status)

        # service:restart
        svc_restart = subparsers.add_parser('service:restart', help='Restart service')
        svc_restart.add_argument('service', help='Service name')
        svc_restart.set_defaults(func=self.cmd_service_restart)

    # Command implementations

    def cmd_status(self, args):
        """Show system status"""
        import subprocess

        print("=" * 60)
        print("  MINDSET SYSTEM STATUS")
        print("=" * 60)

        services = [
            ('lsws', 'OpenLiteSpeed'),
            ('mysql', 'MySQL'),
            ('redis-server', 'Redis'),
            ('mindset', 'Mindset Panel'),
            ('mindset-api', 'Mindset API'),
        ]

        print("\nServices:")
        for service, name in services:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True
            )
            status = result.stdout.strip()
            symbol = "✓" if status == "active" else "✗"
            print(f"  {symbol} {name}: {status}")

        # System resources
        print("\nResources:")
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            print(f"  CPU Usage: {cpu}%")
            print(f"  Memory: {mem.percent}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)")
            print(f"  Disk: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)")
        except ImportError:
            print("  (Install psutil for resource stats)")

        print()

    def cmd_laravel_create(self, args):
        """Create a new Laravel application"""
        print(f"Creating Laravel application: {args.domain}")
        print(f"  PHP Version: {args.php}")
        print(f"  Horizon: {'Yes' if args.with_horizon else 'No'}")
        print(f"  Octane: {'Yes' if args.with_octane else 'No'}")

        if args.from_repo:
            print(f"  Source: {args.from_repo}")

        # TODO: Implement actual creation
        print("\n[This would create the Laravel application]")

    def cmd_laravel_deploy(self, args):
        """Deploy a Laravel application"""
        print(f"Deploying: {args.domain}")
        print(f"  Branch: {args.branch}")
        print(f"  Run Migrations: {'No' if args.no_migrate else 'Yes'}")
        print(f"  NPM Build: {'No' if args.no_build else 'Yes'}")

        # TODO: Implement actual deployment
        print("\n[This would trigger a deployment]")

    def cmd_laravel_rollback(self, args):
        """Rollback to previous release"""
        print(f"Rolling back: {args.domain}")
        print(f"  Releases back: {args.releases}")

        # TODO: Implement rollback
        print("\n[This would perform a rollback]")

    def cmd_laravel_artisan(self, args):
        """Run artisan command"""
        command = ' '.join(args.artisan_command)
        print(f"Running artisan on {args.domain}: {command}")

        # TODO: Implement artisan runner
        print("\n[This would run the artisan command]")

    def cmd_laravel_logs(self, args):
        """View Laravel logs"""
        print(f"Viewing logs for: {args.domain}")
        print(f"  Lines: {args.lines}")
        print(f"  Follow: {'Yes' if args.follow else 'No'}")

        # TODO: Implement log viewer
        print("\n[This would show the logs]")

    def cmd_site_list(self, args):
        """List all sites"""
        print("Listing all sites...")
        # TODO: Implement site listing
        print("\n[This would list all sites]")

    def cmd_site_create(self, args):
        """Create a new site"""
        print(f"Creating site: {args.domain}")
        # TODO: Implement site creation
        print("\n[This would create the site]")

    def cmd_site_delete(self, args):
        """Delete a site"""
        print(f"Deleting site: {args.domain}")
        # TODO: Implement site deletion
        print("\n[This would delete the site]")

    def cmd_db_list(self, args):
        """List databases"""
        print("Listing databases...")
        # TODO: Implement database listing
        print("\n[This would list databases]")

    def cmd_db_create(self, args):
        """Create database"""
        print(f"Creating database: {args.name}")
        # TODO: Implement database creation
        print("\n[This would create the database]")

    def cmd_db_backup(self, args):
        """Backup database"""
        print(f"Backing up database: {args.name}")
        # TODO: Implement database backup
        print("\n[This would backup the database]")

    def cmd_backup_create(self, args):
        """Create backup"""
        print(f"Creating backup for: {args.domain}")
        # TODO: Implement backup creation
        print("\n[This would create a backup]")

    def cmd_backup_list(self, args):
        """List backups"""
        print("Listing backups...")
        # TODO: Implement backup listing
        print("\n[This would list backups]")

    def cmd_backup_restore(self, args):
        """Restore backup"""
        print(f"Restoring backup: {args.backup_id}")
        # TODO: Implement backup restore
        print("\n[This would restore the backup]")

    def cmd_ai_analyze(self, args):
        """Analyze logs with AI"""
        print(f"Analyzing: {args.path}")
        if args.provider:
            print(f"  Provider: {args.provider}")

        # TODO: Implement AI analysis
        print("\n[This would analyze logs with AI]")

    def cmd_ai_explain(self, args):
        """Explain an error"""
        print(f"Explaining error: {args.error[:100]}...")
        # TODO: Implement AI error explanation
        print("\n[This would explain the error with AI]")

    def cmd_ai_status(self, args):
        """AI provider status"""
        print("AI Provider Status:")
        print("  Ollama: Checking...")
        print("  DeepInfra: Checking...")
        # TODO: Implement AI status check
        print("\n[This would show AI provider status]")

    def cmd_service_status(self, args):
        """Service status"""
        if args.service:
            print(f"Status for: {args.service}")
        else:
            print("All service status:")
        # TODO: Implement service status
        print("\n[This would show service status]")

    def cmd_service_restart(self, args):
        """Restart service"""
        print(f"Restarting: {args.service}")
        # TODO: Implement service restart
        print("\n[This would restart the service]")

    def run(self, args=None):
        """Run the CLI"""
        parsed = self.parser.parse_args(args)

        if not parsed.command:
            self.parser.print_help()
            return 1

        if hasattr(parsed, 'func'):
            return parsed.func(parsed)

        return 0


def main():
    """Main entry point"""
    cli = MindsetCLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
