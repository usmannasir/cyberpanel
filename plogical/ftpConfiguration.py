import os


def pure_ftpd_service_name(distro, ubuntu_distros):
    if distro in ubuntu_distros:
        return 'pure-ftpd-mysql'
    return 'pure-ftpd'


def write_chroot_everyone(config_directory):
    os.makedirs(config_directory, exist_ok=True)
    config_path = os.path.join(config_directory, 'ChrootEveryone')
    with open(config_path, 'w') as handle:
        handle.write('yes\n')
    return config_path


def ftp_user_name_prefix(panel_user_name):
    """What the panel puts before the FTP user name typed into its Create FTP Account form."""
    return panel_user_name + '_'


def stored_ftp_user_name(panel_user_name, requested_name, api):
    """The FTP user name that is stored, and signs in, for a requested one.

    The panel's own form sends no ``api`` value and reaches the creation as '0': the name goes
    behind the prefix of the panel user creating the account. The command line, and a request
    that carries another ``api`` value, name the whole account themselves.
    """
    if api == '0':
        return ftp_user_name_prefix(panel_user_name) + requested_name
    return requested_name
