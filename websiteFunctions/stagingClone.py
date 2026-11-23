"""Copy a WordPress site into the folder of a new staging domain, and check that the copy works.

Every command runs as the website's own user through `site(command,
withErrors=True)`, which answers (1 when the command exited with status 0,
else 0; what it printed). A step the copy depends on that does not succeed
raises CloneFailed with the step and its reason. What a tool prints beside a
successful result is not a failure (see step_failure).
"""
import os
import re
import shlex

from plogical.wordpressInstallerUtilities import (
    brief_output,
    build_wordpress_config_command,
    build_wordpress_config_password_command,
    database_client_error,
    out_of_quota,
    single_line_value,
    wordpress_cli_command,
    wordpress_table_prefix_command,
)
from websiteFunctions.wordpressRestore import address_is_on

# What a WordPress version can look like ('6.8.3', '6.9-RC1', '6.9-alpha-60123-src'). WP-CLI
# downloads releases and pre-releases; a version it cannot download is replaced by
# the latest release (see StagingCopy.run).
WORDPRESS_VERSION_TEXT = re.compile(r'[0-9A-Za-z][0-9A-Za-z.-]{0,63}')


class CloneFailed(Exception):
    """A step that the copy depends on did not succeed."""


def step_failure(succeeded, output):
    """Why a step failed, or None when it succeeded.

    A step fails when its command exits with a status other than 0, or when
    a line of what it printed is an error of WP-CLI ("Error: ..."). Anything
    else printed beside a successful result is not a failure: "Warning:"
    lines of WP-CLI, PHP notices, or mysqldump's own remarks such as
    "mysqldump: Error: 'Access denied; you need (at least one of) the
    PROCESS privilege(s) ...' when trying to dump tablespaces", after which
    it goes on and writes the whole dump.
    """
    text = str(output if output is not None else '')
    if succeeded == 1 and not any(line.startswith('Error:') for line in text.splitlines()):
        return None
    if out_of_quota(text):
        return 'the disk quota of this website is used up'
    return brief_output(text) or 'the command failed'


def import_failure(succeeded, output):
    """Why a database import failed, or None when it succeeded.

    WP-CLI goes on after a statement the database refuses, ends with
    "Success" and exits with status 0: the database client's own error line
    is then the only sign that the dump was not imported as it is.
    """
    return database_client_error(output) or step_failure(succeeded, output)


class StagingCopy(object):
    def __init__(self, site, status):
        self.site = site
        self.status = status

    def step(self, command, failure, rule=step_failure):
        succeeded, output = self.site(command)
        reason = rule(succeeded, output)
        if reason is not None:
            raise CloneFailed('%s: %s' % (failure, reason))
        return output

    def value(self, php, path, failure, *arguments):
        """The one value a WP-CLI command prints (without its error output), or CloneFailed."""
        succeeded, output = self.site(wordpress_cli_command(php, path, *arguments), False)
        try:
            if step_failure(succeeded, output) is not None:
                raise ValueError(brief_output(output) or 'the command failed')
            return single_line_value(output)
        except ValueError as error:
            raise CloneFailed('%s: %s' % (failure, str(error)))

    def read_source(self, php, source):
        """What the copy takes from the site before anything is created for it.

        Its WordPress version (the copy runs the same one), its table prefix
        and the folder that holds its themes, plugins and uploads.
        """
        version = self.value(php, source, 'The WordPress version of the site could not be read',
                             'core', 'version')
        prefix = self.value(php, source, 'The table prefix of the site could not be read',
                            'config', 'get', 'table_prefix')
        # WordPress itself prints the content folder; it need not be wp-content.
        # Only the last line counts: a drop-in of the site may print before it.
        succeeded, output = self.site(wordpress_cli_command(php, source, 'theme', 'path'), False)
        lines = [line.strip() for line in str(output or '').splitlines() if line.strip()]
        themes = lines[-1].rstrip('/') if lines else ''
        if succeeded != 1 or not os.path.isabs(themes) or os.path.basename(themes) != 'themes':
            raise CloneFailed('The content folder of the site could not be found: %s' % (
                brief_output(output) or 'the command failed'))
        return {'version': version, 'prefix': prefix, 'content': os.path.dirname(themes)}

    def run(self, php, source, facts, destination, database, dump, oldAddress, domain):
        """Fill the empty folder of the staging domain with a copy of the site, then check the copy.

        database is (name, user, password, host) of the empty database made
        for the copy. dump is where the site's database is exported to on the
        way; the caller removes it. oldAddress is the site's address without
        a scheme, domain the staging domain. Returns the notes for the final
        status: what of the site the copy could not take as it is.
        """
        notes = []
        name, user, password, host = database

        def cli(*arguments):
            return wordpress_cli_command(php, destination, *arguments)

        # The copy runs the site's own WordPress version. A version WP-CLI
        # cannot download (a nightly build, a patched core) is replaced by the
        # latest release, and the final status says so. The site's own themes
        # and plugins are copied in below, so none of the default ones come
        # with the download.
        version = facts['version']
        self.status('Downloading WordPress..,20')
        try:
            if WORDPRESS_VERSION_TEXT.fullmatch(version) is None:
                raise CloneFailed('not a version number')
            self.step(cli('core', 'download', '--version=' + version, '--skip-content'),
                      'WordPress %s could not be downloaded' % version)
        except CloneFailed as error:
            # --force: a download that stopped half-way may have left files.
            self.step(cli('core', 'download', '--skip-content', '--force'), 'WordPress could not be downloaded')
            notes.append('WordPress %s of the site could not be downloaded (%s); the copy runs the latest '
                         'release' % (brief_output(version, 60), brief_output(str(error), 120)))
        # The page the domain was created with.
        self.site('rm -f -- %s' % shlex.quote(os.path.join(destination, 'index.html')))

        self.status('Creating and copying database..,40')
        self.step(build_wordpress_config_command(php, destination, name, user, password, host),
                  'wp-config.php could not be created')
        self.step(build_wordpress_config_password_command(php, destination, password),
                  'The database password could not be written to wp-config.php')
        try:
            prefix = wordpress_table_prefix_command(php, destination, facts['prefix'])
        except ValueError as error:
            raise CloneFailed('%s: %s' % (str(error).rstrip('.'), facts['prefix']))
        self.step(prefix, 'The table prefix could not be written to wp-config.php')
        # umask 077: the dump is readable by the site's user alone.
        self.step('umask 077 && ' + wordpress_cli_command(php, source, 'db', 'export', dump, '--single-transaction'),
                  'The database of the site could not be exported')
        self.step(cli('db', 'import', dump), 'The database could not be imported', import_failure)

        self.status('Copying files..,60')
        content = os.path.join(destination, 'wp-content')
        self.step('mkdir -p -- %s && cp -R -- %s %s' % (
            shlex.quote(content), shlex.quote(os.path.join(facts['content'], '.')), shlex.quote(content + '/')),
            'The themes, plugins and uploads of the site could not be copied')
        htaccess = os.path.join(source, '.htaccess')
        self.step('if [ -e %s ]; then cp -f -- %s %s; fi' % (
            shlex.quote(htaccess), shlex.quote(htaccess), shlex.quote(destination + '/')),
            'The .htaccess file of the site could not be copied')

        self.status('Replacing URLs..,75')
        for before, after in ((oldAddress, domain), ('www.' + domain, domain),
                              ('https://' + domain, 'http://' + domain)):
            self.step(cli('search-replace', before, after),
                      'The site address could not be rewritten in the database')

        # The copy has to be a WordPress that finds its tables in its own
        # database and answers under the staging domain.
        self.step(cli('core', 'is-installed'), 'The copy does not start with its database')
        address = self.value(php, destination, 'The address of the copy could not be read',
                             'option', 'get', 'siteurl')
        if not address_is_on(address, domain):
            raise CloneFailed('The copy answers under the address "%s" instead of under %s' % (
                brief_output(address, 120), domain))
        return notes
