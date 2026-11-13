-- Bootstrap roles for postgresql-stack (run as postgres superuser).
-- Placeholders __PG_APP_USER__ and __PG_APP_PASSWORD__ are replaced by the installer.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '__PG_APP_USER__') THEN
        CREATE ROLE __PG_APP_USER__ LOGIN PASSWORD '__PG_APP_PASSWORD__';
    ELSE
        ALTER ROLE __PG_APP_USER__ WITH PASSWORD '__PG_APP_PASSWORD__';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE postgres TO __PG_APP_USER__;
