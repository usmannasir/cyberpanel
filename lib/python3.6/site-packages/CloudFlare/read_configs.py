""" reading the config file for Cloudflare API"""

import os
import re
try:
    import configparser # py3
except ImportError:
    import ConfigParser as configparser # py2

def read_configs(profile=None):
    """ reading the config file for Cloudflare API"""

    # We return all these values
    config = {'email': None, 'token': None, 'certtoken': None, 'extras': None, 'base_url': None, 'profile': None}

    # envioronment variables override config files - so setup first
    config['email'] = os.getenv('CF_API_EMAIL')
    config['token'] = os.getenv('CF_API_KEY')
    config['certtoken'] = os.getenv('CF_API_CERTKEY')
    config['extras'] = os.getenv('CF_API_EXTRAS')
    config['base_url'] = os.getenv('CF_API_URL')
    if profile is None:
        profile = 'CloudFlare'
    config['profile'] = profile

    # grab values from config files
    cp = configparser.ConfigParser()
    try:
        cp.read([
            '.cloudflare.cfg',
            os.path.expanduser('~/.cloudflare.cfg'),
            os.path.expanduser('~/.cloudflare/cloudflare.cfg')
        ])
    except Exception as e:
        raise Exception("%s: configuration file error" % (profile))

    if len(cp.sections()) > 0:
        # we have a configuration file - lets use it
        try:
            # grab the section - as we will use it for all values
            section = cp[profile]
        except Exception as e:
            # however section name is missing - this is an error
            raise Exception("%s: configuration section missing" % (profile))

        for option in ['email', 'token', 'certtoken', 'extras', 'base_url']:
            if option not in config or config[option] is None:
                try:
                    if option == 'extras':
                        config[option] = re.sub(r"\s+", ' ', section.get(option))
                    else:
                        config[option] = re.sub(r"\s+", '', section.get(option))
                    if config[option] == '':
                        config.pop(option)
                except (configparser.NoOptionError, configparser.NoSectionError):
                    pass
                except Exception as e:
                    pass
            # do we have an override for specific calls? (i.e. token.post or email.get etc)
            for method in ['get', 'patch', 'post', 'put', 'delete']:
                option_for_method = option + '.' + method
                try:
                    config[option_for_method] = re.sub(r"\s+", '', section.get(option_for_method))
                    if config[option_for_method] == '':
                        config.pop(option_for_method)
                except (configparser.NoOptionError, configparser.NoSectionError) as e:
                    pass
                except Exception as e:
                    pass

    # do any final cleanup - only needed for extras (which are multiline)
    if 'extras' in config and config['extras'] is not None:
        config['extras'] = config['extras'].strip().split(' ')

    # remove blank entries
    for x in sorted(config.keys()):
        if config[x] is None or config[x] == '':
            try:
                config.pop(x)
            except:
                pass

    return config
