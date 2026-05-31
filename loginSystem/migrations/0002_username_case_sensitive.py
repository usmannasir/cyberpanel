# Generated for SEC-13: case-exact usernames
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('loginSystem', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE `loginSystem_administrator` "
                "MODIFY `userName` VARCHAR(50) "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL;"
            ),
            reverse_sql=(
                "ALTER TABLE `loginSystem_administrator` "
                "MODIFY `userName` VARCHAR(50) "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL;"
            ),
        ),
    ]
