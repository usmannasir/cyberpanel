# Create firewall_bannedips if an older install applied firewall.0001_initial before
# the BannedIP model existed. Some upgrades then have the migration recorded but the
# table missing, causing MySQL error 1146 when banning an IP from the dashboard.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('firewall', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE TABLE IF NOT EXISTS `firewall_bannedips` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ip_address` varchar(39) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `duration` varchar(50) NOT NULL DEFAULT 'permanent',
  `banned_on` datetime(6) NOT NULL,
  `expires` bigint(20) DEFAULT NULL,
  `active` bool NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `firewall_bannedips_ip_address_uniq` (`ip_address`),
  KEY `fw_bannedip_ip_active_idx` (`ip_address`,`active`),
  KEY `fw_bannedip_active_exp_idx` (`active`,`expires`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
""",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]

