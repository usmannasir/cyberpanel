# -*- coding: utf-8 -*-
# Docker Manager initial migration.
# Creates dockerManager_containers table if not exists (safe when upgrade.dockerMigrations() already ran).

from django.db import migrations


def create_table_if_not_exists(apps, schema_editor):
    """Create dockerManager_containers with full schema. Idempotent via IF NOT EXISTS."""
    if schema_editor.connection.vendor != 'mysql':
        return
    # Use raw SQL so we can do IF NOT EXISTS; matches upgrade.dockerMigrations() final schema
    sql = """
    CREATE TABLE IF NOT EXISTS dockerManager_containers (
        id int(11) NOT NULL AUTO_INCREMENT,
        name varchar(150) NOT NULL,
        cid varchar(64) NOT NULL DEFAULT '',
        admin_id int(11) NOT NULL,
        image varchar(50) NOT NULL DEFAULT 'unknown',
        tag varchar(50) NOT NULL DEFAULT 'unknown',
        memory int(11) NOT NULL DEFAULT 0,
        ports longtext NOT NULL,
        volumes longtext NOT NULL,
        env longtext NOT NULL,
        startOnReboot int(11) NOT NULL DEFAULT 0,
        network varchar(100) NOT NULL DEFAULT 'bridge',
        network_mode varchar(50) NOT NULL DEFAULT 'bridge',
        extra_options longtext NOT NULL,
        PRIMARY KEY (id),
        UNIQUE KEY name (name),
        KEY dockerManager_contai_admin_id_58fb62b7_fk_loginSyst (admin_id),
        CONSTRAINT dockerManager_contai_admin_id_58fb62b7_fk_loginSyst
            FOREIGN KEY (admin_id) REFERENCES loginSystem_administrator (id)
    )
    """
    schema_editor.execute(sql)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('loginSystem', '__first__'),
    ]

    operations = [
        migrations.RunPython(create_table_if_not_exists, noop_reverse),
    ]
