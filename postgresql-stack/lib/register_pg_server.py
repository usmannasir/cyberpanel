"""Register the local PostgreSQL server in pgAdmin for the stack admin user.

The server password is encrypted with the pgAdmin login password (same key used
after SSO login), so saved-password connect works without prompting.

Environment variables (set by modules/45-pgadmin-server.sh):
  PGADMIN_EMAIL, PGADMIN_PASSWORD, PG_SUPERUSER, PG_SUPERUSER_PASSWORD,
  PG_HOST, PG_PORT, PG_MAINT_DB, PG_SERVER_NAME, PG_DISCOVERY_ID
"""
import os
import sys

sys.path.insert(0, "/usr/pgadmin4/web")
sys.path = [p for p in sys.path if "/usr/local/" not in p]


def _env(name, default=None):
    value = os.environ.get(name, default)
    if value is None or value == "":
        raise RuntimeError("Missing required environment variable: {}".format(name))
    return value


def main():
    email = _env("PGADMIN_EMAIL")
    pgadmin_pass = _env("PGADMIN_PASSWORD")
    pg_super_pass = _env("PG_SUPERUSER_PASSWORD")
    pg_user = os.environ.get("PG_SUPERUSER", "postgres")
    host = os.environ.get("PG_HOST", "127.0.0.1")
    port = int(os.environ.get("PG_PORT", "5432"))
    maint_db = os.environ.get("PG_MAINT_DB", "postgres")
    server_name = os.environ.get("PG_SERVER_NAME", "PostgreSQL (localhost)")
    discovery_id = os.environ.get("PG_DISCOVERY_ID", "POSTGRESQL_STACK/local")

    import config
    from pgadmin import create_app
    from pgadmin.model import Server, ServerGroup, User, db
    from pgadmin.utils.crypto import encrypt

    app = create_app(config.APP_NAME + "-cli")
    with app.app_context():
        user_row = User.query.filter_by(username=email).first()
        if user_row is None:
            print("ERROR: pgAdmin user not found: {}".format(email))
            return 1

        group = ServerGroup.query.filter_by(user_id=user_row.id).order_by("id").first()
        if group is None:
            group = ServerGroup(name="Servers", user_id=user_row.id)
            db.session.add(group)
            db.session.commit()

        server = Server.query.filter_by(
            user_id=user_row.id, discovery_id=discovery_id
        ).first()
        if server is None:
            server = Server.query.filter_by(
                user_id=user_row.id, name=server_name
            ).first()

        enc_pwd = encrypt(pg_super_pass, pgadmin_pass)
        conn_params = {"sslmode": "prefer", "connect_timeout": 10}

        if server is None:
            server = Server(
                user_id=user_row.id,
                servergroup_id=group.id,
                name=server_name,
                host=host,
                port=port,
                maintenance_db=maint_db,
                username=pg_user,
                password=enc_pwd,
                save_password=1,
                discovery_id=discovery_id,
                use_ssh_tunnel=0,
                tunnel_authentication=0,
                tunnel_prompt_password=0,
                shared=False,
                kerberos_conn=False,
                connection_params=conn_params,
                comment="Managed by postgresql-stack installer",
            )
            db.session.add(server)
            action = "registered"
        else:
            server.servergroup_id = group.id
            server.name = server_name
            server.host = host
            server.port = port
            server.maintenance_db = maint_db
            server.username = pg_user
            server.password = enc_pwd
            server.save_password = 1
            server.discovery_id = discovery_id
            server.connection_params = conn_params
            server.comment = "Managed by postgresql-stack installer"
            action = "updated"

        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            print("ERROR: failed to save server: {}".format(exc))
            return 1

        print("OK: {} server '{}' for {}".format(action, server_name, email))

        # Remove stale auto-discovered duplicates (from postgres-reg.ini on login).
        dupes = Server.query.filter(
            Server.user_id == user_row.id,
            Server.name == server_name,
            Server.discovery_id != discovery_id,
        ).all()
        for dup in dupes:
            db.session.delete(dup)
        if dupes:
            db.session.commit()
            print("OK: removed {} duplicate server row(s)".format(len(dupes)))

        print("SERVER_GID={}".format(group.id))
        print("SERVER_SID={}".format(server.id))
        return 0


if __name__ == "__main__":
    sys.exit(main())
