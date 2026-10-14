import re


def ensure_email_filter_tables(connection, cursor):
    """Keep email foreign keys compatible with the installed domain column."""
    cursor.execute("""SELECT CHARACTER_SET_NAME, COLLATION_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'e_domains'
        AND COLUMN_NAME = 'domain'""")
    metadata = cursor.fetchone()
    if not metadata or not all(isinstance(value, str) and
                               re.match(r'^[a-zA-Z0-9_]+$', value)
                               for value in metadata):
        raise RuntimeError('Cannot determine the e_domains.domain charset and collation')
    charset, collation = metadata
    suffix = ' ENGINE=InnoDB DEFAULT CHARSET=%s COLLATE=%s' % (charset, collation)
    definitions = (
        ('e_catchall', """`domain_id` varchar(50) NOT NULL,
            `destination` varchar(255) NOT NULL,
            `enabled` tinyint(1) NOT NULL DEFAULT 1,
            PRIMARY KEY (`domain_id`),
            CONSTRAINT `fk_catchall_domain` FOREIGN KEY (`domain_id`)
            REFERENCES `e_domains` (`domain`) ON DELETE CASCADE"""),
        ('e_plus_override', """`domain_id` varchar(50) NOT NULL,
            `enabled` tinyint(1) NOT NULL DEFAULT 1,
            PRIMARY KEY (`domain_id`),
            CONSTRAINT `fk_plus_override_domain` FOREIGN KEY (`domain_id`)
            REFERENCES `e_domains` (`domain`) ON DELETE CASCADE"""),
        ('e_pattern_forwarding', """`id` int(11) NOT NULL AUTO_INCREMENT,
            `domain_id` varchar(50) NOT NULL,
            `pattern` varchar(255) NOT NULL,
            `destination` varchar(255) NOT NULL,
            `pattern_type` varchar(20) NOT NULL DEFAULT 'wildcard',
            `priority` int(11) NOT NULL DEFAULT 100,
            `enabled` tinyint(1) NOT NULL DEFAULT 1,
            PRIMARY KEY (`id`), KEY `fk_pattern_domain` (`domain_id`),
            CONSTRAINT `fk_pattern_domain` FOREIGN KEY (`domain_id`)
            REFERENCES `e_domains` (`domain`) ON DELETE CASCADE"""),
        ('e_server_settings', """`id` int(11) NOT NULL AUTO_INCREMENT,
            `plus_addressing_enabled` tinyint(1) NOT NULL DEFAULT 0,
            `plus_addressing_delimiter` varchar(1) NOT NULL DEFAULT '+',
            PRIMARY KEY (`id`)"""),
    )
    for table, columns in definitions:
        try:
            cursor.execute('CREATE TABLE IF NOT EXISTS `%s` (%s)%s' %
                           (table, columns, suffix))
            cursor.execute('SELECT 1 FROM `%s` LIMIT 0' % table)
        except Exception as error:
            raise RuntimeError('Required email table %s could not be created: %s' %
                               (table, error)) from error
    connection.commit()


def ensure_administrator_default_site(connection, cursor):
    """Create and verify the administrator.defaultSite schema dependency."""
    cursor.execute(
        "SHOW COLUMNS FROM loginSystem_administrator LIKE 'defaultSite'"
    )
    if cursor.fetchone() is None:
        cursor.execute(
            'ALTER TABLE loginSystem_administrator '
            'ADD defaultSite integer DEFAULT 0'
        )
        connection.commit()

    cursor.execute(
        "SHOW COLUMNS FROM loginSystem_administrator LIKE 'defaultSite'"
    )
    if cursor.fetchone() is None:
        raise RuntimeError(
            'Required column loginSystem_administrator.defaultSite is missing'
        )
