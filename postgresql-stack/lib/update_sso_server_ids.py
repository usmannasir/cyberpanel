"""Merge server_group/server ids into the pgAdmin SSO secret file."""
import json
import os
import sys

SECRET_FILE = os.environ.get("PGSTACK_SSO_SECRET", "/var/lib/pgadmin/.pgstack-sso.json")


def main():
    if len(sys.argv) != 3:
        print("Usage: update_sso_server_ids.py <server_gid> <server_sid>", file=sys.stderr)
        return 2
    gid = int(sys.argv[1])
    sid = int(sys.argv[2])
    data = {}
    try:
        with open(SECRET_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        print("WARN: SSO secret file missing; run modules/55-sso.sh first.", file=sys.stderr)
    except Exception as exc:
        print("WARN: could not read SSO secret: {}".format(exc), file=sys.stderr)
    data["server_gid"] = gid
    data["server_sid"] = sid
    try:
        with open(SECRET_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except Exception as exc:
        print("ERROR: failed to write SSO secret: {}".format(exc), file=sys.stderr)
        return 1
    print("OK: SSO secret updated server_gid={} server_sid={}".format(gid, sid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
