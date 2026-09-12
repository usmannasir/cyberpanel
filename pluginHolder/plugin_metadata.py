"""Read installed plugin descriptions without importing or executing plugins."""
import logging
import os
from xml.etree import ElementTree


logger = logging.getLogger(__name__)


def installed_plugin_metadata(registry='/home/cyberpanel/plugins',
                              application_root='/usr/local/CyberCP'):
    try:
        plugins = sorted(os.listdir(registry))
    except FileNotFoundError:
        unavailable = os.path.lexists(registry)
        if unavailable:
            logger.warning('The installed plugin registry cannot be resolved', exc_info=True)
        return {'plugins': [], 'pluginListUnavailable': unavailable}
    except OSError:
        logger.warning('Unable to read the installed plugin registry', exc_info=True)
        return {'plugins': [], 'pluginListUnavailable': True}

    result = []
    for plugin in plugins:
        data = {'name': plugin, 'type': '', 'desc': '', 'version': '',
                'metadata_available': False}
        try:
            metadata = ElementTree.parse(
                os.path.join(application_root, plugin, 'meta.xml'))
            fields = {}
            for key, element in (('name', 'name'), ('type', 'type'),
                                 ('desc', 'description'), ('version', 'version')):
                node = metadata.find(element)
                if node is None or (key != 'desc' and not (node.text or '').strip()):
                    raise ValueError('Required plugin metadata field is missing: ' + element)
                fields[key] = node.text or ''
            data.update(fields)
            data['metadata_available'] = True
        except (OSError, ElementTree.ParseError, ValueError, LookupError):
            logger.warning('Unable to read metadata for installed plugin %s',
                           plugin, exc_info=True)
        result.append(data)
    return {'plugins': result, 'pluginListUnavailable': False}
