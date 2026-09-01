# Add sortOrder on legacy firewall_firewallrules (table predates Django migrations).

from django.db import migrations, connection


def add_sort_order_column(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'firewall_firewallrules'
              AND COLUMN_NAME = 'sortOrder'
            """
        )
        exists = cursor.fetchone()[0] > 0
        if not exists:
            cursor.execute(
                "ALTER TABLE `firewall_firewallrules` "
                "ADD COLUMN `sortOrder` int(11) NOT NULL DEFAULT 0"
            )
        cursor.execute(
            "UPDATE `firewall_firewallrules` SET `sortOrder` = `id` "
            "WHERE `sortOrder` IS NULL OR `sortOrder` <= 0"
        )
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'firewall_firewallrules'
              AND INDEX_NAME = 'firewall_fw_rules_sortorder_idx'
            """
        )
        idx_exists = cursor.fetchone()[0] > 0
        if not idx_exists:
            cursor.execute(
                "CREATE INDEX `firewall_fw_rules_sortorder_idx` "
                "ON `firewall_firewallrules` (`sortOrder`)"
            )


def drop_sort_order_column(apps, schema_editor):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'firewall_firewallrules'
              AND COLUMN_NAME = 'sortOrder'
            """
        )
        exists = cursor.fetchone()[0] > 0
        if exists:
            cursor.execute(
                """
                SELECT COUNT(*) FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'firewall_firewallrules'
                  AND INDEX_NAME = 'firewall_fw_rules_sortorder_idx'
                """
            )
            if cursor.fetchone()[0] > 0:
                cursor.execute(
                    "DROP INDEX `firewall_fw_rules_sortorder_idx` "
                    "ON `firewall_firewallrules`"
                )
            cursor.execute(
                "ALTER TABLE `firewall_firewallrules` DROP COLUMN `sortOrder`"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('firewall', '0002_create_bannedips_table'),
    ]

    operations = [
        migrations.RunPython(add_sort_order_column, drop_sort_order_column),
    ]
