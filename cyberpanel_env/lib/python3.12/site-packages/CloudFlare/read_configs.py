""" reading the config file for Cloudflare API"""

import os
import re
try:
    # py3
    import configparser
except ImportError:
    # py2
    import ConfigParser as configparser # type: ignore

class ReadConfigError(Exception):
    """ errors for read_configs"""

def read_configs(profile=None):
    """ reading the config file for Cloudflare API"""

    # We return all these values
    config = {'email': None, 'key': None, 'token': None, 'certtoken': None, 'extras': None, 'base_url': None, 'openapi_url': None, 'profile': None}

    # envioronment variables override config files - so setup first
    config['email'] = os.getenv('CLOUDFLARE_EMAIL') if os.getenv('CLOUDFLARE_EMAIL') is not None else os.getenv('CF_API_EMAIL')
    config['key'] = os.getenv('CLOUDFLARE_API_KEY') if os.getenv('CLOUDFLARE_API_KEY') is not None else os.getenv('CF_API_KEY')
    config['token'] = os.getenv('CLOUDFLARE_API_TOKEN') if os.getenv('CLOUDFLARE_API_TOKEN') is not None else os.getenv('CF_API_TOKEN')
    config['certtoken'] = os.getenv('CLOUDFLARE_API_CERTKEY') if os.getenv('CLOUDFLARE_API_CERTKEY') is not None else os.getenv('CF_API_CERTKEY')
    config['extras'] = os.getenv('CLOUDFLARE_API_EXTRAS') if os.getenv('CLOUDFLARE_API_EXTRAS') is not None else os.getenv('CF_API_EXTRAS')
    config['base_url'] = os.getenv('CLOUDFLARE_API_URL') if os.getenv('CLOUDFLARE_API_URL') is not None else os.getenv('CF_API_URL')
    config['openapi_url'] = os.getenv('CLOUDFLARE_OPENAPI_URL') if os.getenv('CLOUDFLARE_OPENAPI_URL') is not None else os.getenv('CF_OPENAPI_URL')

    config['global_request_timeout'] = os.getenv('CLOUDFLARE_GLOBAL_REQUEST_TIMEOUT')
    config['max_request_retries'] = os.getenv('CLOUDFLARE_MAX_REQUEST_RETRIES')
    config['http_headers'] = os.getenv('CLOUDFLARE_HTTP_HEADERS')

    # grab values from config files
    cp = configparser.ConfigParser()
    try:
        cp.read([
            '.cloudflare.cfg',
            os.path.expanduser('~/.cloudflare.cfg'),
            os.path.expanduser('~/.cloudflare/cloudflare.cfg')
        ])
    except OSError:
        raise ReadConfigError("%s: configuration file error" % ('.cloudflare.cfg')) from None

    if len(cp.sections()) == 0 and profile is not None and len(profile) > 0:
        # no config file and yet a config name provided - not acceptable!
        raise ReadConfigError("%s: configuration section provided however config file missing" % (profile)) from None

    # Is it CloudFlare or Cloudflare? (A legacy issue)
    if profile is None:
        if cp.has_section('CloudFlare'):
            profile = 'CloudFlare'
        if cp.has_section('Cloudflare'):
            profile = 'Cloudflare'

    # still not found - then set to to CloudFlare for legacy reasons
    if profile is None:
        profile = "CloudFlare"

    config['profile'] = profile

    if len(profile) > 0 and len(cp.sections()) > 0:
        # we have a configuration file - lets use it

        if not cp.has_section(profile):
            raise ReadConfigError("%s: configuration section missing - configuration file only has these sections: %s" % (profile, ','.join(cp.sections()))) from None

        for option in ['email', 'key', 'token', 'certtoken', 'extras', 'base_url', 'openapi_url', 'global_request_timeout', 'max_request_retries', 'http_headers']:
            try:
                config_value = cp.get(profile, option)
                if option == 'extras':
                    # we join all values together as one space seperated strings
                    config[option] = re.sub(r"\s+", ' ', config_value)
                elif option == 'http_headers':
                    # we keep lines as is for now
                    config[option] = config_value
                else:
                    config[option] = re.sub(r"\s+", '', config_value)
                if config[option] is None or config[option] == '':
                    config.pop(option)
            except (configparser.NoOptionError, configparser.NoSectionError):
                pass

            # do we have an override for specific calls? (i.e. token.post or email.get etc)
            for method in ['get', 'patch', 'post', 'put', 'delete']:
                option_for_method = option + '.' + method
                try:
                    config_value = cp.get(profile, option_for_method)
                    config[option_for_method] = re.sub(r"\s+", '', config_value)
                    if config[option] is None or config[option] == '':
                        config.pop(option_for_method)
                except (configparser.NoOptionError, configparser.NoSectionError):
                    pass

    # do any final cleanup - only needed for extras and http_headers (which are multiline)
    if 'extras' in config and config['extras'] is not None:
        config['extras'] = config['extras'].strip().split(' ')
    if 'http_headers' in config and config['http_headers'] is not None:
        config['http_headers'] = [h for h in config['http_headers'].split('\n') if len(h) > 0]
        for h in config['http_headers']:
            try:
                t, v = h.split(':', 1)
            except ValueError:
                # clearly a bad header syntax
                raise ReadConfigError('%s: header syntax error' % (h)) from None
            if len(t.strip()) == 0:
                raise ReadConfigError('%s: header syntax error' % (h)) from None

    # remove blank entries
    for x in sorted(config.keys()):
        if config[x] is None or config[x] == '':
            try:
                config.pop(x)
            except KeyError:
                pass

    return config
