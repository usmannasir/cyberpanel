#!/usr/local/CyberCP/bin/python
"""
Django management command to fix subdomain log configurations
Usage: python manage.py fix_subdomain_logs [--dry-run] [--domain <domain>]
"""

import os
import sys
import django
import re
import shutil
from datetime import datetime

# Add CyberPanel to Python path
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()

from django.core.management.base import BaseCommand, CommandError
from websiteFunctions.models import ChildDomains, Websites
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities


class Command(BaseCommand):
    help = 'Fix subdomain log configurations to use separate log files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--domain',
            type=str,
            help='Fix logs for a specific domain only',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create backup of original configurations',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_domain = options['domain']
        create_backup = options['backup']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        self.stdout.write('Starting subdomain log configuration fix...')
        
        try:
            if specific_domain:
                # Fix specific domain
                self.fix_domain_logs(specific_domain, dry_run, create_backup)
            else:
                # Fix all child domains
                child_domains = ChildDomains.objects.all()
                fixed_count = 0
                
                for child_domain in child_domains:
                    if self.fix_domain_logs(child_domain.domain, dry_run, create_backup):
                        fixed_count += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed log configurations for {fixed_count} child domains')
                )
                
        except Exception as e:
            raise CommandError(f'Failed to fix subdomain logs: {str(e)}')

    def fix_domain_logs(self, domain_name, dry_run=False, create_backup=False):
        """Fix log configuration for a specific domain"""
        try:
            # Get child domain info
            try:
                child_domain = ChildDomains.objects.get(domain=domain_name)
                master_domain = child_domain.master.domain
                domain_path = child_domain.path
            except ChildDomains.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'Domain {domain_name} is not a child domain, skipping')
                )
                return False
            
            vhost_conf_path = f"/usr/local/lsws/conf/vhosts/{domain_name}/vhost.conf"
            
            if not os.path.exists(vhost_conf_path):
                self.stdout.write(
                    self.style.WARNING(f'VHost config not found for {domain_name}: {vhost_conf_path}')
                )
                return False
            
            # Read current configuration
            with open(vhost_conf_path, 'r') as f:
                config_content = f.read()
            
            # Check if fix is needed
            if f'{master_domain}.error_log' not in config_content and f'{master_domain}.access_log' not in config_content:
                self.stdout.write(f'✓ {domain_name} already has correct log configuration')
                return True
            
            self.stdout.write(f'Fixing log configuration for {domain_name}...')
            
            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would fix log paths in {vhost_conf_path}')
                return True
            
            # Create backup if requested
            if create_backup:
                backup_path = f"{vhost_conf_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(vhost_conf_path, backup_path)
                self.stdout.write(f'  Created backup: {backup_path}')
            
            # Fix the configuration
            fixed_content = config_content
            
            # Fix error log path
            fixed_content = re.sub(
                rf'errorlog\s+\$VH_ROOT/logs/{re.escape(master_domain)}\.error_log',
                f'errorlog $VH_ROOT/logs/{domain_name}.error_log',
                fixed_content
            )
            
            # Fix access log path
            fixed_content = re.sub(
                rf'accesslog\s+\$VH_ROOT/logs/{re.escape(master_domain)}\.access_log',
                f'accesslog $VH_ROOT/logs/{domain_name}.access_log',
                fixed_content
            )
            
            # Fix CustomLog paths (for Apache configurations)
            fixed_content = re.sub(
                rf'CustomLog\s+/home/{re.escape(master_domain)}/logs/{re.escape(master_domain)}\.access_log',
                f'CustomLog /home/{domain_name}/logs/{domain_name}.access_log',
                fixed_content
            )
            
            # Write the fixed configuration
            with open(vhost_conf_path, 'w') as f:
                f.write(fixed_content)
            
            # Set proper ownership
            ProcessUtilities.executioner(f'chown lsadm:lsadm {vhost_conf_path}')
            
            # Create the log directory if it doesn't exist
            log_dir = f"/home/{master_domain}/logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                ProcessUtilities.executioner(f'chown -R {child_domain.master.externalApp}:{child_domain.master.externalApp} {log_dir}')
            
            # Create separate log files for the child domain
            error_log_path = f"{log_dir}/{domain_name}.error_log"
            access_log_path = f"{log_dir}/{domain_name}.access_log"
            
            # Create empty log files if they don't exist
            for log_path in [error_log_path, access_log_path]:
                if not os.path.exists(log_path):
                    with open(log_path, 'w') as f:
                        f.write('')
                    ProcessUtilities.executioner(f'chown {child_domain.master.externalApp}:{child_domain.master.externalApp} {log_path}')
                    ProcessUtilities.executioner(f'chmod 644 {log_path}')
            
            # Restart LiteSpeed to apply changes
            ProcessUtilities.executioner('systemctl restart lsws')
            
            self.stdout.write(f'✓ Fixed log configuration for {domain_name}')
            logging.writeToFile(f'Fixed subdomain log configuration for {domain_name}')
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to fix logs for {domain_name}: {str(e)}')
            )
            logging.writeToFile(f'Error fixing subdomain logs for {domain_name}: {str(e)}')
            return False

    def show_help_examples(self):
        """Show usage examples"""
        self.stdout.write('\nUsage examples:')
        self.stdout.write('  python manage.py fix_subdomain_logs --dry-run')
        self.stdout.write('  python manage.py fix_subdomain_logs --domain diabetes.example.com')
        self.stdout.write('  python manage.py fix_subdomain_logs --backup')
        self.stdout.write('  python manage.py fix_subdomain_logs --domain diabetes.example.com --backup --dry-run')
