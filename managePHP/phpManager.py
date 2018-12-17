from plogical.processUtilities import ProcessUtilities

class PHPManager:

    @staticmethod
    def findPHPVersions():
        if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
            return ['PHP 5.3', 'PHP 5.4', 'PHP 5.5', 'PHP 5.6', 'PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3']
        else:
            return ['PHP 7.0', 'PHP 7.1', 'PHP 7.2', 'PHP 7.3']

    @staticmethod
    def getPHPString(phpVersion):

        if phpVersion == "PHP 5.3":
            php = "53"
        elif phpVersion == "PHP 5.4":
            php = "55"
        elif phpVersion == "PHP 5.5":
            php = "55"
        elif phpVersion == "PHP 5.6":
            php = "56"
        elif phpVersion == "PHP 7.0":
            php = "70"
        elif phpVersion == "PHP 7.1":
            php = "71"
        elif phpVersion == "PHP 7.2":
            php = "72"
        elif phpVersion == "PHP 7.3":
            php = "73"

        return php