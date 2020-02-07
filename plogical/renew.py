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

            ## For websites

            for website in Websites.objects.all():
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

                    if int(diff.days) >= 15:
                        logging.writeToFile(
                            'SSL exists for %s and is not ready to renew, skipping..' % (website.domain), 0)
                    elif x509.get_issuer().get_components()[1][1].decode('utf-8') == 'Denial':
                        logging.writeToFile(
                            'SSL exists for %s and ready to renew..' % (website.domain), 0)
                        logging.writeToFile(
                            'Renewing SSL for %s..' % (website.domain), 0)

                        virtualHostUtilities.issueSSL(website.domain, '/home/%s/public_html' % (website.domain),
                                                      website.adminEmail)
                    elif x509.get_issuer().get_components()[1][1].decode('utf-8') != "Let's Encrypt":
                        logging.writeToFile(
                            'Custom SSL exists for %s and ready to renew..' % (website.domain), 1)
                    else:
                        logging.writeToFile(
                            'SSL exists for %s and ready to renew..' % (website.domain), 0)
                        logging.writeToFile(
                            'Renewing SSL for %s..' % (website.domain), 0)

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

                    if int(diff.days) >= 15:
                        logging.writeToFile(
                            'SSL exists for %s and is not ready to renew, skipping..' % (website.domain), 0)
                    elif x509.get_issuer().get_components()[1][1] == 'Denial':
                        logging.writeToFile(
                            'SSL exists for %s and ready to renew..' % (website.domain), 0)
                        logging.writeToFile(
                            'Renewing SSL for %s..' % (website.domain), 0)

                        virtualHostUtilities.issueSSL(website.domain, website.path,
                                                      website.master.adminEmail)
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

        except BaseException as msg:
           logging.writeToFile(str(msg) + '. Renew.SSLObtainer')


if __name__ == "__main__":
    sslOB = Renew()
    sslOB.SSLObtainer()