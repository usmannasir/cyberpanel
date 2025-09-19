#!/usr/local/CyberCP/bin/python
"""
Django management command for SSL reconciliation
Usage: python manage.py ssl_reconcile [--all|--domain <domain>]
"""

import os
import sys
import django

# Add CyberPanel to Python path
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()

from django.core.management.base import BaseCommand, CommandError
from plogical.sslReconcile import SSLReconcile
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


class Command(BaseCommand):
    help = 'Reconcile SSL certificates and ACME challenge configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Reconcile SSL for all domains',
        )
        parser.add_argument(
            '--domain',
            type=str,
            help='Reconcile SSL for a specific domain',
        )
        parser.add_argument(
            '--fix-acme',
            action='store_true',
            help='Fix ACME challenge contexts for all domains',
        )

    def handle(self, *args, **options):
        if options['all']:
            self.stdout.write('Starting SSL reconciliation for all domains...')
            try:
                success = SSLReconcile.reconcile_all()
                if success:
                    self.stdout.write(
                        self.style.SUCCESS('SSL reconciliation completed successfully!')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR('SSL reconciliation failed. Check logs for details.')
                    )
            except Exception as e:
                raise CommandError(f'SSL reconciliation failed: {str(e)}')

        elif options['domain']:
            domain = options['domain']
            self.stdout.write(f'Starting SSL reconciliation for domain: {domain}')
            try:
                success = SSLReconcile.reconcile_domain(domain)
                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f'SSL reconciliation completed for {domain}!')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'SSL reconciliation failed for {domain}. Check logs for details.')
                    )
            except Exception as e:
                raise CommandError(f'SSL reconciliation failed for {domain}: {str(e)}')

        elif options['fix_acme']:
            self.stdout.write('Fixing ACME challenge contexts for all domains...')
            try:
                from plogical.sslUtilities import sslUtilities
                from websiteFunctions.models import Websites
                
                fixed_count = 0
                for website in Websites.objects.all():
                    if sslUtilities.fix_acme_challenge_context(website.domain):
                        fixed_count += 1
                        self.stdout.write(f'Fixed ACME context for: {website.domain}')
                
                self.stdout.write(
                    self.style.SUCCESS(f'Fixed ACME challenge contexts for {fixed_count} domains!')
                )
            except Exception as e:
                raise CommandError(f'Failed to fix ACME contexts: {str(e)}')

        else:
            self.stdout.write(
                self.style.WARNING('Please specify --all, --domain <domain>, or --fix-acme')
            )
            self.stdout.write('Usage examples:')
            self.stdout.write('  python manage.py ssl_reconcile --all')
            self.stdout.write('  python manage.py ssl_reconcile --domain example.com')
            self.stdout.write('  python manage.py ssl_reconcile --fix-acme')
