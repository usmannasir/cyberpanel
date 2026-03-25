#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
from typing import Union, Optional
from datetime import datetime, timedelta
import time

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from websiteFunctions.models import Websites, ChildDomains
import OpenSSL
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.processUtilities import ProcessUtilities

def _update_ssl_renewal_schedule_file():
    """Write SSL renewal schedule to world-readable file for web UI (lscpd can't read root crontab)."""
    try:
        from datetime import datetime, timedelta
        config_path = '/usr/local/CyberCP/ssl_renewal_schedule.conf'
        cron_paths = ['/var/spool/cron/root', '/var/spool/cron/crontabs/root']
        cron_content = None
        for path in cron_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    cron_content = f.read()
                break
        if not cron_content:
            return
        renew_hour, renew_minute, renew_weekday_cron = 0, 0, 4
        for line in cron_content.splitlines():
            line = line.strip()
            if 'renew.py' in line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        renew_minute = int(parts[0]) if parts[0].isdigit() else 0
                        renew_hour = int(parts[1]) if parts[1].isdigit() else 0
                        renew_weekday_cron = int(parts[4]) if parts[4].isdigit() and 0 <= int(parts[4]) <= 7 else 4
                    except (ValueError, IndexError):
                        pass
                elif len(parts) >= 2:
                    renew_minute = int(parts[0]) if parts[0].isdigit() else 0
                    renew_hour = int(parts[1]) if parts[1].isdigit() else 0
                break
        now = datetime.now()
        target_weekday = (renew_weekday_cron - 1) % 7 if renew_weekday_cron else 6
        days_until = (target_weekday - now.weekday()) % 7
        if days_until == 0 and (now.hour > renew_hour or (now.hour == renew_hour and now.minute >= renew_minute)):
            days_until = 7
        next_run = now.replace(hour=renew_hour, minute=renew_minute, second=0, microsecond=0)
        next_run += timedelta(days=days_until)
        schedule_str = next_run.strftime('%B %d, %Y %I:%M %p')
        with open(config_path, 'w') as f:
            f.write(schedule_str)
        os.chmod(config_path, 0o644)
    except Exception as e:
        logging.writeToFile(f'_update_ssl_renewal_schedule_file: {str(e)}', 1)


class Renew:
    def _check_and_renew_ssl(self, domain: str, path: str, admin_email: str, is_child: bool = False) -> None:
        """Helper method to check and renew SSL for a domain."""
        try:
            logging.writeToFile(f'Checking SSL for {domain}.', 0)
            file_path = f'/etc/letsencrypt/live/{domain}/fullchain.pem'

            if not os.path.exists(file_path):
                logging.writeToFile(f'SSL does not exist for {domain}. Obtaining now..', 0)
                virtualHostUtilities.issueSSL(domain, path, admin_email)
                return

            logging.writeToFile(f'SSL exists for {domain}. Checking if SSL will expire in 15 days..', 0)
            
            with open(file_path, 'r') as cert_file:
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_file.read())
            
            expire_data = x509.get_notAfter().decode('ascii')
            final_date = datetime.strptime(expire_data, '%Y%m%d%H%M%SZ')
            now = datetime.now()
            diff = final_date - now

            ssl_provider = x509.get_issuer().get_components()[1][1].decode('utf-8')
            logging.writeToFile(f'Provider: {ssl_provider}, Days until expiration: {diff.days}', 0)

            # Check if certificate is expired or needs renewal
            needs_renewal = diff.days < 15  # This handles both negative (expired) and soon-to-expire certs
            
            if not needs_renewal and ssl_provider != 'Denial':
                logging.writeToFile(f'SSL exists for {domain} and is not ready to renew, skipping..', 0)
                return

            # Handle expired certificates (negative days) with higher priority
            if diff.days < 0:
                logging.writeToFile(f'SSL for {domain} is EXPIRED ({abs(diff.days)} days ago). Forcing renewal..', 0)
                logging.writeToFile(f'Attempting SSL renewal for expired certificate: {domain}..', 0)
                result = virtualHostUtilities.issueSSL(domain, path, admin_email)
                if result[0] == 0:
                    logging.writeToFile(f'SSL renewal FAILED for {domain}: {result[1]}', 1)
                else:
                    logging.writeToFile(f'SSL renewal SUCCESSFUL for {domain}', 0)
            elif ssl_provider == 'Denial' or ssl_provider == "Let's Encrypt":
                logging.writeToFile(f'SSL exists for {domain} and ready to renew (expires in {diff.days} days)..', 0)
                logging.writeToFile(f'Attempting SSL renewal for {domain}..', 0)
                result = virtualHostUtilities.issueSSL(domain, path, admin_email)
                if result[0] == 0:
                    logging.writeToFile(f'SSL renewal FAILED for {domain}: {result[1]}', 1)
                else:
                    logging.writeToFile(f'SSL renewal SUCCESSFUL for {domain}', 0)
            elif ssl_provider != "Let's Encrypt":
                logging.writeToFile(f'Custom SSL exists for {domain} and ready to renew..', 1)

        except OpenSSL.crypto.Error as e:
            logging.writeToFile(f'OpenSSL error for {domain}: {str(e)}', 1)
        except Exception as e:
            logging.writeToFile(f'Error processing SSL for {domain}: {str(e)}', 1)

    def _restart_services(self) -> None:
        """Helper method to restart required services."""
        try:
            logging.writeToFile('Restarting mail services for them to see new SSL.', 0)
            
            # Update mail SSL configuration for all domains
            self._update_all_mail_ssl_configs()
            
            commands = [
                'postmap -F hash:/etc/postfix/vmail_ssl.map',
                'systemctl restart postfix',
                'doveadm reload',
                'systemctl restart lscpd'
            ]
            
            for cmd in commands:
                ProcessUtilities.normalExecutioner(cmd)
                # Add a small delay between restarts
                time.sleep(2)
                
        except Exception as e:
            logging.writeToFile(f'Error restarting services: {str(e)}', 1)

    def _update_all_mail_ssl_configs(self) -> None:
        """Update mail SSL configuration for all domains after renewal"""
        try:
            logging.writeToFile('Updating mail SSL configurations for all domains.', 0)
            
            # Update mail SSL config for all websites
            for website in Websites.objects.filter(state=1):
                virtualHostUtilities.updateMailSSLConfig(website.domain)
            
            # Update mail SSL config for all child domains
            for child in ChildDomains.objects.all():
                virtualHostUtilities.updateMailSSLConfig(child.domain)
                
        except Exception as e:
            logging.writeToFile(f'Error updating mail SSL configs: {str(e)}', 1)

    def SSLObtainer(self):
        try:
            _update_ssl_renewal_schedule_file()
            logging.writeToFile('Running SSL Renew Utility')

            # Process main domains
            for website in Websites.objects.filter(state=1):
                self._check_and_renew_ssl(
                    website.domain,
                    f'/home/{website.domain}/public_html',
                    website.adminEmail
                )

            # Process child domains
            for child in ChildDomains.objects.all():
                self._check_and_renew_ssl(
                    child.domain,
                    child.path,
                    child.master.adminEmail,
                    is_child=True
                )

            self._restart_services()

        except Exception as e:
            logging.writeToFile(f'Error in SSLObtainer: {str(e)}', 1)

    @staticmethod
    def FixMailSSL():
        try:
            for website in Websites.objects.all():
                virtualHostUtilities.setupAutoDiscover(1, '/home/cyberpanel/templogs', website.domain, website.admin)
        except Exception as e:
            logging.writeToFile(f'Error in FixMailSSL: {str(e)}', 1)

if __name__ == "__main__":
    sslOB = Renew()
    sslOB.SSLObtainer()
