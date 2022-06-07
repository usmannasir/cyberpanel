import argparse
import re

class cliParser:

    def prepareArguments(self):
        ## Website creation Arguments

        parser = argparse.ArgumentParser(description='CyberPanel Command Line Interface!')
        parser.add_argument('function', help='Specific a operation to perform!')

        parser.add_argument('--package', help='Select a package for website.')
        parser.add_argument('--owner', help='Select a website owner.')
        parser.add_argument('--masterDomain',
                            help='Master domain argument, which is required for creating child domains!')
        parser.add_argument('--childDomain',
                            help='Child domain argument, which is required for creating child domains!')
        parser.add_argument('--domainName', help='Domain name!')
        parser.add_argument('--email', help='Administrator email.')
        parser.add_argument('--php', help='PHP Selection.')
        parser.add_argument('--ssl', help='Weather to obtain SSL.')
        parser.add_argument('--dkim', help='DKIM Signing')
        parser.add_argument('--openBasedir', help='To enable or disable open_basedir protection for domain.')
        parser.add_argument('--fileName', help='Complete path to a file that needs to be restored.')
        parser.add_argument('--backupPath', help='Backup path to use when generating a backup.')

        ## Package Arguments.

        parser.add_argument('--packageName', help='Package name.')
        parser.add_argument('--diskSpace', help='Package disk space in MBs')
        parser.add_argument('--bandwidth', help='Package bandwidth in MBs.')
        parser.add_argument('--emailAccounts', help='Number of  allowed email accounts for Package.')
        parser.add_argument('--dataBases', help='Number of allowed databases for Package.')
        parser.add_argument('--ftpAccounts', help='Number of allowed ftp accounts for Package.')
        parser.add_argument('--allowedDomains', help='Number of allowed child domains for Package.')


        ## DNS Arguments

        parser.add_argument('--name', help='DNS Record Name.')
        parser.add_argument('--recordType', help='DNS Record type.')
        parser.add_argument('--value', help='DNS Record value.')
        parser.add_argument('--priority', help='Priority for DNS Record.')
        parser.add_argument('--ttl', help='TTL for DNS Record')
        parser.add_argument('--recordID', help='DNS Record ID to be deleted.')

        ## Database Arguments

        parser.add_argument('--dbName', help='Database name.')
        parser.add_argument('--dbUsername', help='Datbase username.')
        parser.add_argument('--dbPassword', help='Database password.')
        parser.add_argument('--databaseWebsite', help='Database website.')

        ## Email Arguments
        parser.add_argument('--userName', help='Email Username.')
        parser.add_argument('--password', help='Email password.')

        ### Additional Arguments for user manager

        parser.add_argument('--firstName', help='First name while creating user.')
        parser.add_argument('--lastName', help='First name while creating user.')
        parser.add_argument('--websitesLimit', help='Website limit while creating user.')
        parser.add_argument('--selectedACL', help='Select ACL while creating user.')
        parser.add_argument('--securityLevel', help='Set security level while creating user.')
        parser.add_argument('--state', help='State value used in user suspension.')


        ### WP Install

        parser.add_argument('--siteTitle', help='Site Title for application installers.')
        parser.add_argument('--path', help='Path for application installers.')

        ### Convert to LSWS Ent via cli

        parser.add_argument('--licenseKey', help='LiteSpeed Enterprise License key')


        return parser.parse_args()
