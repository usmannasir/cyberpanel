import argparse
import sys
sys.path.append('/usr/local/CyberCP')
from plogical.processUtilities import ProcessUtilities

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    args = parser.parse_args()

    command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/IncScheduler.py %s' % (args.function)
    ProcessUtilities.normalExecutioner(command)


if __name__ == "__main__":
    main()