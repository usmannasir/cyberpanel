import subprocess
import shlex
import argparse
import os



class servCTRL:
    pidfile = '/usr/local/CyberCP/WebTerminal/pid'

    def prepareArguments(self):

        parser = argparse.ArgumentParser(description='CyberPanel Policy Control Parser!')
        parser.add_argument('function', help='Specific a operation to perform!')

        return parser.parse_args()

    def start(self):

        if os.path.exists(servCTRL.pidfile):
            self.stop()

        command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/WebTerminal/CPWebSocket.py'
        subprocess.Popen(shlex.split(command))

    def stop(self):
        try:
            path = servCTRL.pidfile
            command = 'kill -9 %s' % (open(path, 'r').read())
            subprocess.Popen(shlex.split(command))
        except:
            pass


def main():

    policy = servCTRL()
    args = policy.prepareArguments()

    ## Website functions

    if args.function == "start":
        policy.start()
    elif args.function == "stop":
        policy.stop()
    elif args.function == "restart":
        policy.stop()
        policy.start()

if __name__ == "__main__":
    main()