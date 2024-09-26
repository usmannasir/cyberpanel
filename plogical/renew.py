#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from websiteFunctions.models import Websites, ChildDomains
from os import path
from datetime import datetime
import OpenSSL
from plogical.virtualHostUtilities import virtualHostUtilities

class Renew:
    def SSLObtainer(self):
        try:
            logging.writeToFile('Running SSL Renew Utility')

            ## For Non-suspended websites only

            for website in Websites.objects.filter(state=1):
                logging.writeToFile('Checking SSL for %s.' % (website.domain), 0)
                filePath = '/etc/letsencrypt/live/%s/fullchain.pem' % (website.domain)

                if path.exists(filePath):
                    logging.writeToFile('SSL exists for %s. Checking if SSL will expire in 15 days..' % (website.domain), 0)
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                           open(filePath, 'r').read())
                    expireData = x509.get_notAfter().decode('ascii')
                    finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')
                    now = datetime.now()
                    diff = finalDate - now

                    SSLProvider = x509.get_issuer().get_components()[1][1].decode('utf-8')

                    print(f"Provider: {x509.get_issuer().get_components()[1][1].decode('utf-8')}, Days : {diff.days}")

                    if int(diff.days) >= 15 and SSLProvider!='Denial':
                        logging.writeToFile(
                            'SSL exists for %s and is not ready to renew, skipping..' % (website.domain), 0)
                        print(
                            f'SSL exists for %s and is not ready to renew, skipping..' % (website.domain))
                    elif SSLProvider == 'Denial':
                        logging.writeToFile(
                            'SSL exists for %s and ready to renew..' % (website.domain), 0)
                        logging.writeToFile(
                            'Renewing SSL for %s..' % (website.domain), 0)

                        print(
                            f'SSL exists for %s and ready to renew..' % (website.domain))

                        virtualHostUtilities.issueSSL(website.domain, '/home/%s/public_html' % (website.domain),
                                                      website.adminEmail)
                    elif SSLProvider != "Let's Encrypt":
                        logging.writeToFile(
                            'Custom SSL exists for %s and ready to renew..' % (website.domain), 1)
                        print(
                            'Custom SSL exists for %s and ready to renew..' % (website.domain))
                    else:
                        logging.writeToFile(
                            'SSL exists for %s and ready to renew..' % (website.domain), 0)
                        logging.writeToFile(
                            'Renewing SSL for %s..' % (website.domain), 0)

                        print(
                            'SSL exists for %s and ready to renew..' % (website.domain))


                        virtualHostUtilities.issueSSL(website.domain, '/home/%s/public_html' % (website.domain), website.adminEmail)
                else:
                    logging.writeToFile(
                        'SSL does not exist for %s. Obtaining now..' % (website.domain), 0)
                    virtualHostUtilities.issueSSL(website.domain, '/home/%s/public_html' % (website.domain),
                                                  website.adminEmail)

            ## For child-domains

            for website in ChildDomains.objects.all():
                logging.writeToFile('Checking SSL for %s.' % (website.domain), 0)
                filePath = '/etc/letsencrypt/live/%s/fullchain.pem' % (website.domain)

                if path.exists(filePath):
                    logging.writeToFile(
                        'SSL exists for %s. Checking if SSL will expire in 15 days..' % (website.domain), 0)
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM,
                                                           open(filePath, 'r').read())
                    expireData = x509.get_notAfter().decode('ascii')
                    finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')
                    now = datetime.now()
                    diff = finalDate - now

                    SSLProvider = x509.get_issuer().get_components()[1][1]

                    print(f"Provider: {x509.get_issuer().get_components()[1][1].decode('utf-8')}, Days : {diff.days}")

                    if int(diff.days) >= 15 and SSLProvider != 'Denial':
                        logging.writeToFile(
                            'SSL exists for %s and is not ready to renew, skipping..' % (website.domain), 0)
                    elif SSLProvider == 'Denial':
                        logging.writeToFile(
                            'SSL exists for %s and ready to renew..' % (website.domain), 0)
                        logging.writeToFile(
                            'Renewing SSL for %s..' % (website.domain), 0)

                        virtualHostUtilities.issueSSL(website.domain, website.path,
                                                      website.master.adminEmail)
                    elif SSLProvider != "Let's Encrypt":
                        logging.writeToFile(
                            'Custom SSL exists for %s and ready to renew..' % (website.domain), 1)
                    else:
                        logging.writeToFile(
                            'SSL exists for %s and ready to renew..' % (website.domain), 0)
                        logging.writeToFile(
                            'Renewing SSL for %s..' % (website.domain), 0)

                        virtualHostUtilities.issueSSL(website.domain, website.path,
                                                      website.master.adminEmail)
                else:
                    logging.writeToFile(
                        'SSL does not exist for %s. Obtaining now..' % (website.domain), 0)
                    virtualHostUtilities.issueSSL(website.domain, website.path,
                                                  website.master.adminEmail)

            self.file = logging.writeToFile('Restarting mail services for them to see new SSL.', 0)

            from plogical.processUtilities import ProcessUtilities
            command = 'postmap -F hash:/etc/postfix/vmail_ssl.map'
            ProcessUtilities.normalExecutioner(command)

            command = 'systemctl restart postfix'
            ProcessUtilities.normalExecutioner(command)

            command = 'systemctl restart dovecot'
            ProcessUtilities.normalExecutioner(command)

            command = 'systemctl restart lscpd'
            ProcessUtilities.normalExecutioner(command)

        except BaseException as msg:
           logging.writeToFile(str(msg) + '. Renew.SSLObtainer')

    @staticmethod
    def FixMailSSL():
        for website in Websites.objects.all():
            virtualHostUtilities.setupAutoDiscover(1, '/home/cyberpanel/templogs', website.domain, website.admin)


if __name__ == "__main__":
    sslOB = Renew()
    sslOB.SSLObtainer()
