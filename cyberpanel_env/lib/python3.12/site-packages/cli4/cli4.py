#!/usr/bin/env python
"""Cloudflare API via command line"""

import sys
import re
import getopt
import json

import CloudFlare

from .dump import dump_commands, dump_commands_from_web
from . import converters
from . import examples

my_yaml = None
my_jsonlines = None

class CLI4InternalError(Exception):
    """ errors in cli4 """

def load_and_check_yaml():
    """ load_and_check_yaml() """
    # only called if user uses --yaml flag
    from . import myyaml
    global my_yaml
    try:
        my_yaml = myyaml.myyaml()
    except ImportError:
        sys.exit('cli4: install yaml support via: pip install pyyaml')

def load_and_check_jsonlines():
    """ load_and_check_yaml() """
    # only called if user uses --ndjson flag
    from . import myjsonlines
    global my_jsonlines
    try:
        my_jsonlines = myjsonlines.myjsonlines()
    except ImportError:
        sys.exit('cli4: install jsonlines support via: pip install jsonlines')

def strip_multiline(s):
    """ remove leading/trailing tabs/spaces on each line"""
    # This hack is needed in order to use yaml.safe_load() on JSON text - tabs are not allowed
    return '\n'.join([line.strip() for line in s.splitlines()])

def process_params_content_files(method, binary_file, args):
    """ process_params_content_files() """

    digits_only = re.compile('^-?[0-9]+$')
    floats_only = re.compile('^-?[0-9.]+$')

    params = None
    content = None
    files = None
    # next grab the params. These are in the form of tag=value or =value or @filename
    while len(args) > 0 and ('=' in args[0] or args[0][0] == '@'):
        arg = args.pop(0)
        if arg[0] == '@':
            # a file to be uploaded - used in workers/script etc - only via PUT or POST
            filename = arg[1:]
            if method not in ['PUT','POST']:
                sys.exit('cli4: %s - raw file upload only with PUT or POST' % (filename))
            try:
                if filename == '-':
                    if binary_file:
                        content = sys.stdin.buffer.read()
                    else:
                        content = sys.stdin.read()
                else:
                    if binary_file:
                        with open(filename, 'rb') as f:
                            content = f.read()
                    else:
                        with open(filename, 'r', encoding="utf-8") as f:
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
                # value = json.loads(value) - changed to yaml code to remove unicode string issues
                load_and_check_yaml()
                # cleanup string before parsing so that yaml.safe.load does not complain about whitespace
                # >>> found character '\t' that cannot start any token <<<
                value_string = strip_multiline(value_string)
                try:
                    value = my_yaml.safe_load(value_string)
                except my_yaml.parser.ParserError:
                    raise ValueError from None
            except ValueError:
                sys.exit('cli4: %s="%s" - can\'t parse json value' % (tag_string, value_string))
        elif value_string[0] == '@':
            # a file to be uploaded - used in dns_records/import etc - only via PUT or POST
            filename = value_string[1:]
            if method not in ['PUT', 'POST']:
                sys.exit('cli4: %s=%s - file upload only with PUT or POST' % (tag_string, filename))
            if files is None:
                files = {}
            if tag_string in files:
                sys.exit('cli4: %s=%s - duplicate name' % (tag_string, filename))
            try:
                if filename == '-':
                    files[tag_string] = sys.stdin
                else:
                    files[tag_string] = open(filename, 'rb')
            except IOError:
                sys.exit('cli4: %s=%s - file open failure' % (tag_string, filename))
            # no need for param code below
            continue
        elif (value_string[0] == '"' and value_string[-1] == '"') or (value_string[0] == '\'' and value_string[-1] == '\''):
            # remove quotes
            value = value_string[1:-1]
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

    if content and params:
        sys.exit('cli4: content and params not allowed together')

    if params and files:
        for k,v in params.items():
            files[k] = (None, v)
        params = None
        # sys.exit('cli4: params and files not allowed together')

    if method != 'GET':
        if params:
            content = params
            params = None

    return (params, content, files)

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
    uuid_value = re.compile('^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$') # 8-4-4-4-12

    m = cf
    for element in parts:
        if element[0] == ':':
            element = element[1:]
            if identifier1 is None:
                if len(element) in [32, 40, 48] and hex_only.match(element):
                    # raw identifier - lets just use it as-is
                    identifier1 = element
                elif len(element) == 36 and uuid_value.match(element):
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
                            raise CLI4InternalError("/%s/%s :NOT CODED YET" % ('/'.join(cmd), element))
                    except CLI4InternalError as e:
                        sys.stderr.write('cli4: /%s - %s\n' % (command, e))
                        raise e
                cmd.append(':' + identifier1)
            elif identifier2 is None:
                if len(element) in [32, 40, 48] and hex_only.match(element):
                    # raw identifier - lets just use it as-is
                    identifier2 = element
                elif len(element) == 36 and uuid_value.match(element):
                    # uuid identifier - lets just use it as-is
                    identifier2 = element
                elif element[0] == ':':
                    # raw string - used for workers script_names
                    identifier2 = element[1:]
                else:
                    try:
                        if (cmd[0] and cmd[0] == 'zones') and (cmd[2] and cmd[2] == 'dns_records'):
                            identifier2 = converters.convert_dns_record_to_identifier(cf, identifier1, element)
                        elif (cmd[0] and cmd[0] == 'zones') and (cmd[2] and cmd[2] == 'custom_hostnames'):
                            identifier2 = converters.convert_custom_hostnames_to_identifier(cf, identifier1, element)
                        else:
                            raise CLI4InternalError("/%s/:%s :NOT CODED YET" % ('/'.join(cmd), element))
                    except CLI4InternalError as e:
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
                elif len(element) == 36 and uuid_value.match(element):
                    # uuid identifier - lets just use it as-is
                    identifier3 = element
                elif waf_rules.match(element):
                    identifier3 = element
                elif element[0] == ':':
                    # raw string - used for workers script_names
                    identifier3 = element[1:]
                else:
                    #  /accounts/:id/storage/kv/namespaces/:id/values/:key_name - it's a strange one!
                    if len(cmd) >= 6 and cmd[0] == 'accounts' and cmd[2] == 'storage' and cmd[3] == 'kv' and cmd[4] == 'namespaces' and cmd[6] == 'values':
                        identifier3 = element
                    else:
                        sys.stderr.write('/%s/:%s :NOT CODED YET\n' % ('/'.join(cmd), element))
                        raise e
        else:
            try:
                m = getattr(m, CloudFlare.CloudFlare.sanitize_verb(element))
                cmd.append(element)
            except AttributeError as e:
                # the verb/element was not found
                sys.stderr.write('cli4: /%s - not found\n' % (command))
                raise e

    results = []
    if identifier2 is None:
        identifier2 = [None]
    for i2 in identifier2:
        try:
            if method == 'GET':
                # no content with a GET call
                r = m.get(identifier1=identifier1,
                          identifier2=i2,
                          identifier3=identifier3,
                          params=params)
            elif method == 'PATCH':
                r = m.patch(identifier1=identifier1,
                            identifier2=i2,
                            identifier3=identifier3,
                            data=content)
            elif method == 'POST':
                r = m.post(identifier1=identifier1,
                           identifier2=i2,
                           identifier3=identifier3,
                           data=content, files=files)
            elif method == 'PUT':
                r = m.put(identifier1=identifier1,
                          identifier2=i2,
                          identifier3=identifier3,
                          data=content, files=files)
            elif method == 'DELETE':
                r = m.delete(identifier1=identifier1,
                             identifier2=i2,
                             identifier3=identifier3,
                             data=content)
            else:
                pass
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            if len(e) > 0:
                # more than one error returned by the API
                for x in e:
                    sys.stderr.write('cli4: /%s - %d %s\n' % (command, int(x), str(x)))
            sys.stderr.write('cli4: /%s - %d %s\n' % (command, int(e), str(e)))
            raise e
        except CloudFlare.exceptions.CloudFlareInternalError as e:
            sys.stderr.write('cli4: InternalError: /%s - %d %s\n' % (command, int(e), str(e)))
            raise e
        except Exception as e:
            sys.stderr.write('cli4: /%s - %s - api error\n' % (command, str(e)))
            raise e

        results.append(r)
    return results

def write_results(results, output):
    """dump the results"""

    if output is None:
        return

    if len(results) == 1:
        results = results[0]

    if isinstance(results, (str, bytes, bytearray)):
        # if the results are a simple string, then it should be dumped directly
        # this is only used for /zones/:id/dns_records/export, workers, and other calls
        # or
        # output is image or audio or video or something like that so we dump directly
        pass
    else:
        # anything more complex (dict, list, etc) should be dumped as JSON/YAML
        if output == 'json':
            try:
                results = json.dumps(results,
                                     indent=4,
                                     sort_keys=True,
                                     ensure_ascii=False,
                                     encoding='utf8')
            except TypeError:
                results = json.dumps(results,
                                     indent=4,
                                     sort_keys=True,
                                     ensure_ascii=False)
        elif output == 'yaml':
            results = my_yaml.safe_dump(results)
        elif output == 'ndjson':
            # NDJSON support seems like a hack. There has to be a better way
            try:
                writer = my_jsonlines.Writer(sys.stdout)
                writer.write_all(results)
                writer.close()
            except (BrokenPipeError, IOError):
                pass
            return
        else:
            # None of the above, so pass thru results except something in byte form
            if not isinstance(results, (bytes, bytearray)):
                results = str(results)

    if results:
        try:
            if isinstance(results, (bytes, bytearray)):
                sys.stdout.buffer.write(results)
            else:
                sys.stdout.write(results)
                if not results.endswith('\n'):
                    sys.stdout.write('\n')
        except (BrokenPipeError, IOError):
            pass

def do_it(args):
    """Cloudflare API via command line"""

    verbose = False
    output = 'json'
    example = False
    raw = False
    do_dump = False
    do_openapi = None
    openapi_url = None
    binary_file = False
    profile = None
    http_headers = None
    warnings = True
    method = 'GET'

    usage = ('usage: cli4 '
             + '[-V|--version] [-h|--help] [-v|--verbose] '
             + '[-e|--examples] '
             + '[-q|--quiet] '
             + '[-j|--json] [-y|--yaml] [-n|--ndjson] [-i|--image] '
             + '[-r|--raw] '
             + '[-d|--dump] '
             + '[-A|--openapi url] '
             + '[-b|--binary] '
             + '[-p|--profile profile-name] '
             + '[-h|--header additional-header] '
             + '[-w|--warnings [True|False]] '
             + '[--get|--patch|--post|--put|--delete] '
             + '[item=value|item=@filename|@filename ...] '
             + '/command ...')

    try:
        opts, args = getopt.getopt(args,
                                   'VhveqjynirdA:bp:h:w:GPOUD',
                                   [
                                       'version', 'help', 'verbose',
                                       'examples',
                                       'quiet',
                                       'json', 'yaml', 'ndjson', 'image',
                                       'raw',
                                       'dump',
                                       'openapi=',
                                       'binary',
                                       'profile=',
                                       'header=',
                                       'warnings=',
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
        elif opt in ('-e', '--examples'):
            example = True
        elif opt in ('-j', '--json'):
            output = 'json'
        elif opt in ('-y', '--yaml'):
            load_and_check_yaml()
            output = 'yaml'
        elif opt in ('-n', '--ndjson'):
            load_and_check_jsonlines()
            output = 'ndjson'
        elif opt in ('-i', '--image'):
            output = 'image'
        elif opt in ('-r', '--raw'):
            raw = True
        elif opt in ('-p', '--profile'):
            profile = arg
        elif opt in ('-h', '--header'):
            if http_headers is None:
                http_headers = []
            http_headers.append(arg)
        elif opt in ('-w', '--warnings'):
            if arg is None or arg == '':
                warnings = None
            elif arg.lower() in ('yes', 'true', '1'):
                warnings = True
            elif arg.lower() in ('no', 'false', '0'):
                warnings = False
            else:
                sys.exit('cli4: --warnings takes boolean True/False argument')
        elif opt in ('-d', '--dump'):
            do_dump = True
        elif opt in ('-A', '--openapi'):
            do_openapi = True
            openapi_url = arg if arg != '' else None
        elif opt in ('-b', '--binary'):
            binary_file = True
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

    if example:
        try:
            examples.display()
        except ModuleNotFoundError as e:
            sys.exit(e)
        sys.exit(0)

    try:
        cf = CloudFlare.CloudFlare(debug=verbose, raw=raw, profile=profile, http_headers=http_headers, warnings=warnings)
    except Exception as e:
        sys.exit(e)

    if do_dump:
        a = dump_commands(cf)
        # success - just dump results and exit
        sys.stdout.write(a)
        sys.exit(0)

    if do_openapi:
        try:
            a = dump_commands_from_web(cf, openapi_url)
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            sys.exit('cli4: %s - Failed' % (e))
        # success - just dump results and exit
        sys.stdout.write(a)
        sys.exit(0)

    # next grab the params. These are in the form of tag=value or =value or @filename
    (params, content, files) = process_params_content_files(method, binary_file, args)

    # what's left is the command itself
    if len(args) < 1:
        sys.exit(usage)
    commands = args

    exit_with_error = False
    for command in commands:
        try:
            results = run_command(cf, method, command, params, content, files)
            write_results(results, output)
        except KeyboardInterrupt as e:
            sys.exit('cli4: %s - Interrupted\n' % (command))
        except Exception as e:
            exit_with_error = True

    if exit_with_error:
        sys.exit(1)

def cli4(args):
    """Cloudflare API via command line"""

    do_it(args)
    sys.exit(0)
