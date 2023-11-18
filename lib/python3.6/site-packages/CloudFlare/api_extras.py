""" API extras for Cloudflare API"""

import re

from .exceptions import CloudFlareAPIError

def api_extras(self, extras=None):
    """ API extras for Cloudflare API"""

    count = 0;
    for extra in extras:
        extra = re.sub(r"^.*/client/v4/", '/', extra)
        extra = re.sub(r"^.*/v4/", '/', extra)
        extra = re.sub(r"^/", '', extra)
        if extra == '':
            continue

        # build parts of the extra command
        parts = []
        part = None
        for element in extra.split('/'):
            if element[0] == ':':
                parts.append(part)
                part = None
                continue
            if part:
                part += '/' + element
            else:
                part = element
        if part:
            parts.append(part)

        if len(parts) > 1:
            p = parts[1].split('/')
            for nn in range(0, len(p)):
                try:
                    self.add('VOID', parts[0], '/'.join(p[0:nn]))
                except CloudFlareAPIError:
                    # already exists - this is ok
                    pass

        if len(parts) > 2:
            p = parts[2].split('/')
            for nn in range(0, len(p)):
                try:
                    self.add('VOID', parts[0], parts[1], '/'.join(p[0:nn]))
                except CloudFlareAPIError:
                    # already exists - this is ok
                    pass

        while len(parts) < 3:
            parts.append(None)

        # we can only add AUTH elements presently
        try:
            self.add('AUTH', parts[0], parts[1], parts[2])
            count += 1
        except CloudFlareAPIError:
            # this is silently dropped - however, that could change
            pass

    return count
