"""Versioned read-only inventory shared by the node gateway and controller."""
import json
import re

from multiServer import entitlement

PATH = '/multiserver/gateway/inventory'
CATEGORIES = ('websites', 'databases', 'mail')
ROW_LIMIT = 500
BYTE_LIMIT = 512 * 1024
_LABEL = r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?'
_DOMAIN = re.compile(_LABEL + r'(?:\.' + _LABEL + ')*')
_DATABASE = re.compile(r'[a-zA-Z0-9_][a-zA-Z0-9_$-]{0,49}')
_LOCAL_PART = re.compile(r"[A-Za-z0-9_+%-]+(?:\.[A-Za-z0-9_+%-]+)*")


def domain(value):
    return type(value) is str and len(value) <= 253 and _DOMAIN.fullmatch(value) is not None


def valid_row(category, row):
    if type(row) is not list or len(row) != 2:
        return False
    name, detail = row
    if category == 'websites':
        return domain(name) and type(detail) is int and detail in (0, 1)
    if not domain(detail) or type(name) is not str:
        return False
    if category == 'databases':
        return bool(_DATABASE.fullmatch(name))
    if category != 'mail' or len(name) > 80 or name.count('@') != 1:
        return False
    user, host = name.split('@')
    return (len(user) <= 64 and bool(_LOCAL_PART.fullmatch(user)) and domain(host)
            and host.lower() == detail.lower())


def read(admin_id, categories=CATEGORIES):
    # Each source is the full panel inventory visible to an active full administrator.
    # A linked request supplies only the mapping authenticated by the gateway.
    from multiServer.views import active_full_administrator
    if active_full_administrator(admin_id) is None:
        raise PermissionError()
    from websiteFunctions.models import Websites
    from databases.models import Databases
    from mailServer.models import EUsers
    projections = {'websites': (Websites, 'domain', 'state'),
                   'databases': (Databases, 'dbName', 'website__domain'),
                   'mail': (EUsers, 'email', 'emailOwner_id')}
    snapshot = {'version': 1}
    for category in categories:
        model, name, detail = projections[category]
        records = model.objects.order_by(name).values_list(name, detail)[:ROW_LIMIT + 1]
        rows, seen, partial = [], set(), False
        for record in records:
            row = list(record)
            if len(rows) == ROW_LIMIT or not valid_row(category, row) or row[0].lower() in seen:
                partial = True
                continue
            seen.add(row[0].lower())
            rows.append(row)
        snapshot[category] = {'rows': rows, 'partial': partial}
    return snapshot


def encode(snapshot):
    body = json.dumps(snapshot, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    if len(body) > BYTE_LIMIT:
        raise ValueError('Inventory too large.')
    return body


def _number(text):
    if text not in ('0', '1'):
        raise ValueError('Unexpected inventory number.')
    return int(text)


def decode(body):
    if type(body) is not bytes or len(body) > BYTE_LIMIT:
        raise ValueError('Invalid inventory size.')
    data = json.loads(body.decode('ascii'), object_pairs_hook=entitlement._object,
                      parse_int=_number, parse_float=_number, parse_constant=_number)
    if (type(data) is not dict or set(data) != set(CATEGORIES + ('version',)) or
            type(data['version']) is not int or data['version'] != 1):
        raise ValueError('Unknown inventory format.')
    for category in CATEGORIES:
        batch = data[category]
        if (type(batch) is not dict or set(batch) != {'rows', 'partial'} or type(batch['partial']) is not bool
                or type(batch['rows']) is not list or len(batch['rows']) > ROW_LIMIT):
            raise ValueError('Invalid inventory batch.')
        seen = set()
        for row in batch['rows']:
            if not valid_row(category, row) or row[0].lower() in seen:
                raise ValueError('Invalid inventory row.')
            seen.add(row[0].lower())
    return data
