""" API extras for Cloudflare API"""

import datetime

from bs4 import BeautifulSoup, Comment

API_TYPES = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE']

def do_section(section):
    """ API extras for Cloudflare API"""

    cmds = []
    # look for deprecated first in section
    deprecated = False
    deprecated_date = ''
    deprecated_already = False
    for tag2 in section.find_all('h3'):
        # <h3 class="text-warning" data-reactid="13490">Deprecation Warning</h3>
        if 'Deprecation Warning' in str(tag2):
            deprecated = True
            break
    for tag2 in section.find_all('p'):
        # <p class="deprecation-date" data-reactid="13491">End of life Date: November 2, 2020</p>
        if 'End of life Date:' in str(tag2):
            for child in tag2.children:
                deprecated_date = str(child).replace('End of life Date:','').strip()
                try:
                    # clean up date
                    d = datetime.datetime.strptime(deprecated_date, '%B %d, %Y')
                    if d <= datetime.datetime.now():
                        # already done!
                        deprecated_already = True
                    deprecated_date = d.strftime('%Y-%m-%d')
                except ValueError:
                    # Lets not worry about all the date formats that could show-up. Leave as a string
                    pass
                break
        if deprecated_date != '':
            break
    # look for all API calls in section
    for tag2 in section.find_all('pre'):
        cmd = []
        for child in tag2.children:
            if isinstance(child, Comment):
                # remove <!-- react-text ... -> parts
                continue
            cmd.append(child.strip())
        if len(cmd) == 0:
            continue
        action = cmd[0]
        if action == '' or action not in API_TYPES:
            continue
        cmd = ''.join(cmd[1:])
        if cmd[0] != '/':
            cmd = '/' + cmd
        v = {'action': action, 'cmd': cmd, 'deprecated': deprecated, 'deprecated_date': deprecated_date, 'deprecated_already': deprecated_already}
        cmds.append(v)
    return cmds

def api_decode_from_web(content):
    """ API extras for Cloudflare API"""

    soup = BeautifulSoup(content, 'html.parser')

    all_cmds = []
    for section in soup.find_all('section'):
        all_cmds += do_section(section)

    return sorted(all_cmds, key=lambda v: v['cmd'])
