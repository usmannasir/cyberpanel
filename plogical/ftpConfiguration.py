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
