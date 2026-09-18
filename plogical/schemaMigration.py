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
