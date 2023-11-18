#!/usr/bin/env python
"""Cloudflare API via command line"""

import sys
import re
import getopt
import json
try:
    import yaml
except ImportError:
    yaml = None
try:
    import jsonlines
except ImportError:
    jsonlines = None

import CloudFlare
from . import converters

def dump_commands(cf):
    """dump a tree of all the known API commands"""
    w = cf.api_list()
    sys.stdout.write('\n'.join(w) + '\n')

def dump_commands_from_web(cf):
    """dump a tree of all the known API commands - from web"""
    w = cf.api_from_web()
    for r in w:
        if r['deprecated']:
            if r['deprecated_already']:
                sys.stdout.write('%-6s %s ; deprecated %s - expired!\n' % (r['action'], r['cmd'], r['deprecated_date']))
            else:
                sys.stdout.write('%-6s %s ; deprecated %s\n' % (r['action'], r['cmd'], r['deprecated_date']))
        else:
            sys.stdout.write('%-6s %s\n' % (r['action'], r['cmd']))

def run_command(cf, method, command, params=None, content=None, files=None):
    """run the command line"""
    # remove leading and trailing /'s
    if command[0] == '/':
        command = command[1:]
    if command[-1] == '/':
        command = command[:-1]

    # break down command into it's seperate pieces
    # these are then checked against the Cloudflare class
    # to confirm there is a method that matches
    parts = command.split('/')

    cmd = []
    identifier1 = None
    identifier2 = None
    identifier3 = None

    hex_only = re.compile('^[0-9a-fA-F]+$')
    waf_rules = re.compile('^[0-9]+[A-Z]*$')
    uuid_value = re.compile('^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')	# 8-4-4-4-12

    m = cf
    for element in parts:
        if element[0] == ':':
            element = element[1:]
            if identifier1 is None:
                if len(element) in [32, 40, 48] and hex_only.match(element):
                    # raw identifier - lets just use it as-is
                    identifier1 = element
                elif len(element) == 36  and uuid_value.match(element):
                    # uuid identifier - lets just use it as-is
                    identifier1 = element
                elif element[0] == ':':
                    # raw string - used for workers script_name - use ::script_name
                    identifier1 = element[1:]
                else:
                    try:
                        if cmd[0] == 'certificates':
                            # identifier1 = convert_certificates_to_identifier(cf, element)
                            identifier1 = converters.convert_zones_to_identifier(cf, element)
                        elif cmd[0] == 'zones':
                            identifier1 = converters.convert_zones_to_identifier(cf, element)
                        elif cmd[0] == 'accounts':
                            identifier1 = converters.convert_accounts_to_identifier(cf, element)
                        elif cmd[0] == 'organizations':
                            identifier1 = converters.convert_organizations_to_identifier(cf, element)
                        elif (cmd[0] == 'user') and (cmd[1] == 'organizations'):
                            identifier1 = converters.convert_organizations_to_identifier(cf, element)
                        elif (cmd[0] == 'user') and (cmd[1] == 'invites'):
                            identifier1 = converters.convert_invites_to_identifier(cf, element)
                        elif (cmd[0] == 'user') and (cmd[1] == 'virtual_dns'):
                            identifier1 = converters.convert_virtual_dns_to_identifier(cf, element)
                        elif (cmd[0] == 'user') and (cmd[1] == 'load_balancers') and (cmd[2] == 'pools'):
                            identifier1 = converters.convert_load_balancers_pool_to_identifier(cf, element)
                        else:
                            raise Exception("/%s/%s :NOT CODED YET" % ('/'.join(cmd), element))
                    except Exception as e:
                        sys.stderr.write('cli4: /%s - %s\n' % (command, e))
                        raise e
                cmd.append(':' + identifier1)
            elif identifier2 is None:
                if len(element) in [32, 40, 48] and hex_only.match(element):
                    # raw identifier - lets just use it as-is
                    identifier2 = element
                elif len(element) == 36  and uuid_value.match(element):
                    # uuid identifier - lets just use it as-is
                    identifier2 = element
                elif element[0] == ':':
                    # raw string - used for workers script_names
                    identifier2 = element[1:]
                else:
                    try:
                        if (cmd[0] and cmd[0] == 'zones') and (cmd[2] and cmd[2] == 'dns_records'):
                            identifier2 = converters.convert_dns_record_to_identifier(cf,
                                                                                      identifier1,
                                                                                      element)
                        elif (cmd[0] and cmd[0] == 'zones') and (cmd[2] and cmd[2] == 'custom_hostnames'):
                            identifier2 = converters.convert_custom_hostnames_to_identifier(cf,
                                                                                      identifier1,
                                                                                      element)
                        else:
                            raise Exception("/%s/%s :NOT CODED YET" % ('/'.join(cmd), element))
                    except Exception as e:
                        sys.stderr.write('cli4: /%s - %s\n' % (command, e))
                        raise e
                # identifier2 may be an array - this needs to be dealt with later
                if isinstance(identifier2, list):
                    cmd.append(':' + '[' + ','.join(identifier2) + ']')
                else:
                    cmd.append(':' + identifier2)
                    identifier2 = [identifier2]
            else:
                if len(element) in [32, 40, 48] and hex_only.match(element):
                    # raw identifier - lets just use it as-is
                    identifier3 = element
                elif len(element) == 36  and uuid_value.match(element):
                    # uuid identifier - lets just use it as-is
                    identifier3 = element
                elif waf_rules.match(element):
                    identifier3 = element
                elif element[0] == ':':
                    # raw string - used for workers script_names
                    identifier3 = element[1:]
                else:
                    if len(cmd) >= 6 and cmd[0] == 'accounts' and cmd[2] == 'storage' and cmd[3] == 'kv' and cmd[4] == 'namespaces' and cmd[6] == 'values':
                        identifier3 = element
                    else:
                        sys.stderr.write('/%s/%s :NOT CODED YET 3\n' % ('/'.join(cmd), element))
                        raise e
        else:
            try:
                # dashes (vs underscores) cause issues in Python and other languages
                if '-' in element:
                    m = getattr(m, element.replace('-','_'))
                else:
                    m = getattr(m, element)
                cmd.append(element)
            except AttributeError:
                # the verb/element was not found
                if len(cmd) == 0:
                    sys.stderr.write('cli4: /%s - not found\n' % (element))
                else:
                    sys.stderr.write('cli4: /%s/%s - not found\n' % ('/'.join(cmd), element))
                raise e

    if content and params:
        sys.stderr.write('cli4: /%s - content and params not allowed together\n' % (command))
        raise Exception
    if content:
        params = content

    results = []
    if identifier2 is None:
        identifier2 = [None]
    for i2 in identifier2:
        try:
            if method == 'GET':
                r = m.get(identifier1=identifier1,
                          identifier2=i2,
                          identifier3=identifier3,
                          params=params)
            elif method == 'PATCH':
                r = m.patch(identifier1=identifier1,
                            identifier2=i2,
                            identifier3=identifier3,
                            data=params)
            elif method == 'POST':
                r = m.post(identifier1=identifier1,
                           identifier2=i2,
                           identifier3=identifier3,
                           data=params, files=files)
            elif method == 'PUT':
                r = m.put(identifier1=identifier1,
                          identifier2=i2,
                          identifier3=identifier3,
                          data=params)
            elif method == 'DELETE':
                r = m.delete(identifier1=identifier1,
                             identifier2=i2,
                             identifier3=identifier3,
                             data=params)
            else:
                pass
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            if len(e) > 0:
                # more than one error returned by the API
                for x in e:
                    sys.stderr.write('cli4: /%s - %d %s\n' % (command, x, x))
            sys.stderr.write('cli4: /%s - %d %s\n' % (command, e, e))
            raise e
        except CloudFlare.exceptions.CloudFlareInternalError as e:
            sys.stderr.write('cli4: InternalError: /%s - %d %s\n' % (command, e, e))
            raise e
        except Exception as e:
            sys.stderr.write('cli4: /%s - %s - api error\n' % (command, e))
            raise e

        results.append(r)
    return results

def write_results(results, output):
    """dump the results"""

    if output is None:
        return

    if len(results) == 1:
        results = results[0]

    if isinstance(results, str):
        # if the results are a simple string, then it should be dumped directly
        # this is only used for /zones/:id/dns_records/export presently
        pass
    else:
        # anything more complex (dict, list, etc) should be dumped as JSON/YAML
        if output is None:
            results = None
        if output == 'json':
            try:
                results = json.dumps(results,
                                     indent=4,
                                     sort_keys=True,
                                     ensure_ascii=False,
                                     encoding='utf8')
            except TypeError as e:
                results = json.dumps(results,
                                     indent=4,
                                     sort_keys=True,
                                     ensure_ascii=False)
        if output == 'yaml':
            results = yaml.safe_dump(results)
        if output == 'ndjson':
            # NDJSON support seems like a hack. There has to be a better way
            try:
                writer = jsonlines.Writer(sys.stdout)
                writer.write_all(results)
                writer.close()
            except (BrokenPipeError, IOError):
                pass
            return

    if results:
        try:
            sys.stdout.write(results)
            if not results.endswith('\n'):
                sys.stdout.write('\n')
        except (BrokenPipeError, IOError):
            pass

def do_it(args):
    """Cloudflare API via command line"""

    verbose = False
    output = 'json'
    raw = False
    dump = False
    dump_from_web = False
    profile = None
    method = 'GET'

    usage = ('usage: cli4 '
             + '[-V|--version] [-h|--help] [-v|--verbose] [-q|--quiet] '
             + '[-j|--json] [-y|--yaml] [-n|ndjson] '
             + '[-r|--raw] '
             + '[-d|--dump] '
             + '[-a|--api] '
             + '[-p|--profile profile-name] '
             + '[--get|--patch|--post|--put|--delete] '
             + '[item=value|item=@filename|@filename ...] '
             + '/command ...')

    try:
        opts, args = getopt.getopt(args,
                                   'Vhvqjyrdap:GPOUD',
                                   [
                                       'version',
                                       'help', 'verbose', 'quiet', 'json', 'yaml', 'ndjson',
                                       'raw',
                                       'dump', 'api',
                                       'profile=',
                                       'get', 'patch', 'post', 'put', 'delete'
                                   ])
    except getopt.GetoptError:
        sys.exit(usage)
    for opt, arg in opts:
        if opt in ('-V', '--version'):
            sys.exit('Cloudflare library version: %s' % (CloudFlare.__version__))
        if opt in ('-h', '--help'):
            sys.exit(usage)
        elif opt in ('-v', '--verbose'):
            verbose = True
        elif opt in ('-q', '--quiet'):
            output = None
        elif opt in ('-j', '--json'):
            output = 'json'
        elif opt in ('-y', '--yaml'):
            if yaml is None:
                sys.exit('cli4: install yaml support')
            output = 'yaml'
        elif opt in ('-n', '--ndjson'):
            if jsonlines is None:
                sys.exit('cli4: install jsonlines support')
            output = 'ndjson'
        elif opt in ('-r', '--raw'):
            raw = True
        elif opt in ('-p', '--profile'):
            profile = arg
        elif opt in ('-d', '--dump'):
            dump = True
        elif opt in ('-a', '--api'):
            dump_from_web = True
        elif opt in ('-G', '--get'):
            method = 'GET'
        elif opt in ('-P', '--patch'):
            method = 'PATCH'
        elif opt in ('-O', '--post'):
            method = 'POST'
        elif opt in ('-U', '--put'):
            method = 'PUT'
        elif opt in ('-D', '--delete'):
            method = 'DELETE'

    if dump:
        cf = CloudFlare.CloudFlare(debug=verbose, raw=raw, profile=profile)
        dump_commands(cf)
        sys.exit(0)

    if dump_from_web:
        cf = CloudFlare.CloudFlare(debug=verbose, raw=raw, profile=profile)
        dump_commands_from_web(cf)
        sys.exit(0)

    digits_only = re.compile('^-?[0-9]+$')
    floats_only = re.compile('^-?[0-9.]+$')

    # next grab the params. These are in the form of tag=value or =value or @filename
    params = None
    content = None
    files = None
    while len(args) > 0 and ('=' in args[0] or args[0][0] == '@'):
        arg = args.pop(0)
        if arg[0] == '@':
            # a file to be uploaded - used in workers/script - only via PUT
            filename = arg[1:]
            if method not in ['PUT','POST']:
                sys.exit('cli4: %s - raw file upload only with PUT or POST' % (filename))
            try:
                if filename == '-':
                    content = sys.stdin.read()
                else:
                    with open(filename, 'r') as f:
                        content = f.read()
            except IOError:
                sys.exit('cli4: %s - file open failure' % (filename))
            continue
        tag_string, value_string = arg.split('=', 1)
        if value_string.lower() == 'true':
            value = True
        elif value_string.lower() == 'false':
            value = False
        elif value_string == '' or value_string.lower() == 'none':
            value = None
        elif value_string[0] == '=' and value_string[1:] == '':
            sys.exit('cli4: %s== - no number value passed' % (tag_string))
        elif value_string[0] == '=' and digits_only.match(value_string[1:]):
            value = int(value_string[1:])
        elif value_string[0] == '=' and floats_only.match(value_string[1:]):
            value = float(value_string[1:])
        elif value_string[0] == '=':
            sys.exit('cli4: %s== - invalid number value passed' % (tag_string))
        elif value_string[0] in '[{' and value_string[-1] in '}]':
            # a json structure - used in pagerules
            try:
                #value = json.loads(value) - changed to yaml code to remove unicode string issues
                if yaml is None:
                    sys.exit('cli4: install yaml support')
                try:
                    value = yaml.safe_load(value_string)
                except yaml.parser.ParserError as e:
                    raise ValueError
            except ValueError:
                sys.exit('cli4: %s="%s" - can\'t parse json value' % (tag_string, value_string))
        elif value_string[0] == '@':
            # a file to be uploaded - used in dns_records/import - only via POST
            filename = value_string[1:]
            if method != 'POST':
                sys.exit('cli4: %s=%s - file upload only with POST' % (tag_string, filename))
            files = {}
            try:
                if filename == '-':
                    files[tag_string] = sys.stdin
                else:
                    files[tag_string] = open(filename, 'rb')
            except IOError:
                sys.exit('cli4: %s=%s - file open failure' % (tag_string, filename))
            # no need for param code below
            continue
        else:
            value = value_string

        if tag_string == '':
            # There's no tag; it's just an unnamed list
            if params is None:
                params = value
            else:
                sys.exit('cli4: %s=%s - param error. Can\'t mix unnamed and named list' %
                         (tag_string, value_string))
        else:
            if params is None:
                params = {}
            tag = tag_string
            try:
                params[tag] = value
            except TypeError:
                sys.exit('cli4: %s=%s - param error. Can\'t mix unnamed and named list' %
                         (tag_string, value_string))

    # what's left is the command itself
    if len(args) < 1:
        sys.exit(usage)
    commands = args

    try:
        cf = CloudFlare.CloudFlare(debug=verbose, raw=raw, profile=profile)
    except Exception as e:
        sys.exit(e)

    for command in commands:
        try:
            results = run_command(cf, method, command, params, content, files)
            write_results(results, output)
        except Exception as e:
            if len(commands) > 1:
                continue

def cli4(args):
    """Cloudflare API via command line"""

    do_it(args)
    sys.exit(0)
