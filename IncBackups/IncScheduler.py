import argparse
import sys

sys.path.append("/usr/local/CyberCP")
from plogical.cyberpanel_python import ensure_cyberpanel_bin_python_shim, resolve_cyberpanel_python
from plogical.processUtilities import ProcessUtilities


def main():
    try:
        ensure_cyberpanel_bin_python_shim()
    except BaseException:
        pass

    parser = argparse.ArgumentParser(description="CyberPanel incremental backup cron wrapper")
    parser.add_argument("function", help="Function name to pass to plogical/IncScheduler.py")
    args = parser.parse_args()

    py = resolve_cyberpanel_python()
    command = "%s /usr/local/CyberCP/plogical/IncScheduler.py '%s'" % (py, args.function)
    ProcessUtilities.normalExecutioner(command)


if __name__ == "__main__":
    main()
