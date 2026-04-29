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

    def SSLObtainer(self):
        try:
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
