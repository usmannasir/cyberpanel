import time

from serverStatus.serverStatusUtil import ServerStatusUtil
from plogical import CyberCPLogFileWriter as logging

from manageServices.application_backup import (
    CHOWN_CMDS,
    cleanup_managed_backup,
    create_managed_app_backup,
    merge_data_from_backup,
    restore_full_backup,
    service_is_active,
)
from manageServices.application_detection import detect_app_state, is_debian_family


def adopt_or_reconcile(status_file):
    state = detect_app_state('Redis')
    if state['installed'] and not state['markerExists']:
        ServerStatusUtil.executioner('touch /home/cyberpanel/redis', status_file)
        logging.CyberCPLogFileWriter.statusWriter(
            ServerStatusUtil.lswsInstallStatusPath,
            'Redis detected and adopted by marker reconciliation.\n'
        )
    return state


def _resolve_target_version(version):
    if version and str(version).strip() != 'latest':
        return str(version).strip()
    from manageServices.application_versions import get_latest_version
    return get_latest_version('Redis', '8', '3') or ''


def _run_redis_packages(version, status_file, allow_downgrade):
    ad = ' --allow-downgrade' if allow_downgrade else ''
    if is_debian_family():
        if version and version != 'latest':
            cmd = (
                'DEBIAN_FRONTEND=noninteractive apt-get install -y '
                '--allow-downgrades redis-server={0}'
            ).format(version)
        else:
            cmd = 'DEBIAN_FRONTEND=noninteractive apt-get install redis-server -y'
        ServerStatusUtil.executioner(cmd, status_file)
        return

    if version and version != 'latest':
        cmd = 'dnf install{0} -y redis-{1}'.format(ad, version)
        ServerStatusUtil.executioner(cmd, status_file)
    else:
        cmd = 'dnf install{0} -y redis'.format(ad)
        ServerStatusUtil.executioner(cmd, status_file)


def install(version='latest'):
    status_file = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
    adopt_or_reconcile(status_file)

    from manageServices.application_versions import version_compare

    state = detect_app_state('Redis')
    backup_dir = ''
    allow_downgrade = False
    target = _resolve_target_version(version)

    if state['installed'] and state.get('installedVersion'):
        status_file.write('Pre-version-change backup and service stop (Redis)...\n')
        status_file.flush()
        iv = state['installedVersion']
        if target and version_compare(iv, target) > 0:
            allow_downgrade = True
            status_file.write('Downgrade path enabled for Redis.\n')
            status_file.flush()
        backup_dir = create_managed_app_backup('Redis', status_file)
        ServerStatusUtil.executioner('systemctl stop redis', status_file)

    _run_redis_packages(version, status_file, allow_downgrade)
    if backup_dir:
        merge_data_from_backup('Redis', backup_dir, status_file)
        ServerStatusUtil.executioner(CHOWN_CMDS['Redis'], status_file)

    ServerStatusUtil.executioner('systemctl enable redis', status_file)
    ServerStatusUtil.executioner('systemctl start redis', status_file)
    time.sleep(2)

    if backup_dir:
        if service_is_active('Redis'):
            cleanup_managed_backup(backup_dir, status_file)
            status_file.write(
                'Redis version change completed; backup removed after success.\n'
            )
        else:
            status_file.write('Redis failed to start; restoring from backup...\n')
            restore_full_backup(backup_dir, status_file)
            ServerStatusUtil.executioner(CHOWN_CMDS['Redis'], status_file)
            ServerStatusUtil.executioner('systemctl start redis', status_file)
            time.sleep(2)
            if not service_is_active('Redis'):
                status_file.write(
                    'Recovery unclear — backup kept at {0}\n'.format(backup_dir)
                )
            else:
                status_file.write(
                    'Prior state restored from backup. Backup retained for safety.\n'
                )
        status_file.flush()

    ServerStatusUtil.executioner('touch /home/cyberpanel/redis', status_file)
    logging.CyberCPLogFileWriter.statusWriter(
        ServerStatusUtil.lswsInstallStatusPath, 'Redis installed.[200]\n', 1
    )
    return 0


def upgrade(version='latest'):
    return install(version=version)


def remove():
    status_file = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
    if is_debian_family():
        ServerStatusUtil.executioner(
            'DEBIAN_FRONTEND=noninteractive apt-get remove redis-server -y', status_file
        )
    else:
        ServerStatusUtil.executioner('yum erase redis -y', status_file)
    ServerStatusUtil.executioner('rm -f /home/cyberpanel/redis', status_file)
    logging.CyberCPLogFileWriter.statusWriter(
        ServerStatusUtil.lswsInstallStatusPath, 'Redis removed.[200]\n', 1
    )
    return 0
