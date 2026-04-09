# CyberMail Email Delivery — initial schema.
# Database DDL uses int(11) FK to legacy loginSystem_administrator.id (MariaDB rejects bigint FK -> int PK).

from django.db import migrations, models
import django.db.models.deletion


CREATE_CYBERMAIL_TABLES = '''
CREATE TABLE `cybermail_accounts` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `platform_account_id` int(11) DEFAULT NULL,
  `api_key` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `plan_name` varchar(100) NOT NULL,
  `plan_slug` varchar(50) NOT NULL,
  `emails_per_month` int(11) NOT NULL,
  `is_connected` tinyint(1) NOT NULL,
  `relay_enabled` tinyint(1) NOT NULL,
  `smtp_credential_id` int(11) DEFAULT NULL,
  `smtp_username` varchar(255) NOT NULL,
  `smtp_host` varchar(255) NOT NULL,
  `smtp_port` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `admin_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cybermail_accounts_admin_id_uniq` (`admin_id`),
  CONSTRAINT `cybermail_accounts_admin_id_fk` FOREIGN KEY (`admin_id`)
    REFERENCES `loginSystem_administrator` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE `cybermail_domains` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(255) NOT NULL,
  `platform_domain_id` int(11) DEFAULT NULL,
  `status` varchar(50) NOT NULL,
  `spf_verified` tinyint(1) NOT NULL,
  `dkim_verified` tinyint(1) NOT NULL,
  `dmarc_verified` tinyint(1) NOT NULL,
  `dns_configured` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `account_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `cybermail_domains_account_id_fk` (`account_id`),
  CONSTRAINT `cybermail_domains_account_id_fk` FOREIGN KEY (`account_id`)
    REFERENCES `cybermail_accounts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
'''

DROP_CYBERMAIL_TABLES = '''
DROP TABLE IF EXISTS `cybermail_domains`;
DROP TABLE IF EXISTS `cybermail_accounts`;
'''


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('loginSystem', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(CREATE_CYBERMAIL_TABLES, DROP_CYBERMAIL_TABLES),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='CyberMailAccount',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('platform_account_id', models.IntegerField(null=True)),
                        ('api_key', models.CharField(blank=True, max_length=255)),
                        ('email', models.CharField(max_length=255)),
                        ('plan_name', models.CharField(default='Free', max_length=100)),
                        ('plan_slug', models.CharField(default='free', max_length=50)),
                        ('emails_per_month', models.IntegerField(default=15000)),
                        ('is_connected', models.BooleanField(default=False)),
                        ('relay_enabled', models.BooleanField(default=False)),
                        ('smtp_credential_id', models.IntegerField(null=True)),
                        ('smtp_username', models.CharField(blank=True, max_length=255)),
                        ('smtp_host', models.CharField(default='mail.cyberpersons.com', max_length=255)),
                        ('smtp_port', models.IntegerField(default=587)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                        (
                            'admin',
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name='cybermail_account',
                                to='loginSystem.administrator',
                            ),
                        ),
                    ],
                    options={
                        'db_table': 'cybermail_accounts',
                    },
                ),
                migrations.CreateModel(
                    name='CyberMailDomain',
                    fields=[
                        ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('domain', models.CharField(max_length=255)),
                        ('platform_domain_id', models.IntegerField(null=True)),
                        ('status', models.CharField(default='pending', max_length=50)),
                        ('spf_verified', models.BooleanField(default=False)),
                        ('dkim_verified', models.BooleanField(default=False)),
                        ('dmarc_verified', models.BooleanField(default=False)),
                        ('dns_configured', models.BooleanField(default=False)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        (
                            'account',
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name='domains',
                                to='emailDelivery.cybermailaccount',
                            ),
                        ),
                    ],
                    options={
                        'db_table': 'cybermail_domains',
                    },
                ),
            ],
        ),
    ]
