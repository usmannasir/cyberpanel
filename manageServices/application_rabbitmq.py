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
from manageServices.application_rabbitmq_repo import (
    normalize_rabbitmq_stream,
    ensure_rabbitmq_team_repos,
    ensure_erlang_meets_minimum,
)


def adopt_or_reconcile(status_file):
    state = detect_app_state('RabbitMQ')
    if state['installed'] and not state['markerExists']:
        ServerStatusUtil.executioner('touch /home/cyberpanel/rabbitmq', status_file)
        logging.CyberCPLogFileWriter.statusWriter(
            ServerStatusUtil.lswsInstallStatusPath,
            'RabbitMQ detected and adopted by marker reconciliation.\n'
        )
    return state


def _resolve_target_version(version, stream):
    if version and str(version).strip() != 'latest':
        return str(version).strip()
    from manageServices.application_versions import get_latest_version
    return get_latest_version('RabbitMQ', '8', stream) or ''


def _run_rabbitmq_packages(version, status_file, allow_downgrade):
    ad = ' --allow-downgrade' if allow_downgrade else ''
    if is_debian_family():
        if version and version != 'latest':
            cmd = (
                'DEBIAN_FRONTEND=noninteractive apt-get install -y '
                '--allow-downgrades rabbitmq-server={0}'
            ).format(version)
        else:
            cmd = 'DEBIAN_FRONTEND=noninteractive apt-get install rabbitmq-server -y'
        ServerStatusUtil.executioner(cmd, status_file)
        return

    if version and version != 'latest':
        cmd = 'dnf install{0} -y rabbitmq-server-{1}'.format(ad, version)
        ServerStatusUtil.executioner(cmd, status_file)
    else:
        cmd = 'dnf install{0} -y rabbitmq-server'.format(ad)
        ServerStatusUtil.executioner(cmd, status_file)


def install(version='latest', stream='3'):
    stream = normalize_rabbitmq_stream(stream)
    status_file = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
    adopt_or_reconcile(status_file)

    from manageServices.application_versions import version_compare

    ensure_rabbitmq_team_repos(stream, status_file=status_file)
    ensure_erlang_meets_minimum(stream, version, status_file=status_file)

    state = detect_app_state('RabbitMQ')
    backup_dir = ''
    allow_downgrade = False
    target = _resolve_target_version(version, stream)

    if state['installed'] and state.get('installedVersion'):
        status_file.write(
            'Pre-version-change backup and service stop (RabbitMQ)...\n'
        )
        status_file.flush()
        iv = state['installedVersion']
        if target and version_compare(iv, target) > 0:
            allow_downgrade = True
            status_file.write('Downgrade path enabled for RabbitMQ.\n')
            status_file.flush()
        backup_dir = create_managed_app_backup('RabbitMQ', status_file)
        ServerStatusUtil.executioner('systemctl stop rabbitmq-server', status_file)

    _run_rabbitmq_packages(version, status_file, allow_downgrade)
    if backup_dir:
        merge_data_from_backup('RabbitMQ', backup_dir, status_file)
        ServerStatusUtil.executioner(CHOWN_CMDS['RabbitMQ'], status_file)

    ServerStatusUtil.executioner('systemctl enable rabbitmq-server', status_file)
    ServerStatusUtil.executioner('systemctl start rabbitmq-server', status_file)
    time.sleep(4)

    if backup_dir:
        if service_is_active('RabbitMQ'):
            cleanup_managed_backup(backup_dir, status_file)
            status_file.write(
                'RabbitMQ version change completed; backup removed after success.\n'
            )
        else:
            status_file.write('RabbitMQ failed to start; restoring from backup...\n')
            restore_full_backup(backup_dir, status_file)
            ServerStatusUtil.executioner(CHOWN_CMDS['RabbitMQ'], status_file)
            ServerStatusUtil.executioner('systemctl start rabbitmq-server', status_file)
            time.sleep(4)
            if not service_is_active('RabbitMQ'):
                status_file.write(
                    'Recovery unclear — backup kept at {0}\n'.format(backup_dir)
                )
            else:
                status_file.write(
                    'Prior state restored from backup. Backup retained for safety.\n'
                )
        status_file.flush()

    ServerStatusUtil.executioner('touch /home/cyberpanel/rabbitmq', status_file)
    logging.CyberCPLogFileWriter.statusWriter(
        ServerStatusUtil.lswsInstallStatusPath, 'RabbitMQ installed.[200]\n', 1
    )
    return 0


def upgrade(version='latest', stream='3'):
    return install(version=version, stream=stream)


def remove():
    status_file = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
    ServerStatusUtil.executioner('systemctl stop rabbitmq-server', status_file)
    ServerStatusUtil.executioner('systemctl disable rabbitmq-server', status_file)
    if is_debian_family():
        ServerStatusUtil.executioner(
            'DEBIAN_FRONTEND=noninteractive apt-get remove rabbitmq-server -y',
            status_file,
        )
    else:
        ServerStatusUtil.executioner('yum erase rabbitmq-server -y', status_file)
    ServerStatusUtil.executioner('rm -f /home/cyberpanel/rabbitmq', status_file)
    logging.CyberCPLogFileWriter.statusWriter(
        ServerStatusUtil.lswsInstallStatusPath, 'RabbitMQ removed.[200]\n', 1
    )
    return 0
