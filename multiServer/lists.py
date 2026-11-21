"""Read-only combined inventory in the controller's normal panel session."""
import time
from urllib.parse import urlencode

from django.db import DatabaseError
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.cache import never_cache

from multiServer import entitlement, inventory, inventory_cache, links, models, nodes, transport

TITLES = {'websites': ('Websites', 'Website', 'Status'), 'databases': ('Databases', 'Database', 'Website'),
          'mail': ('Mail', 'Mailbox', 'Domain')}
PAGE_SIZE = 25
SOURCE_PAGE_SIZE = 16


def _page(value):
    return max(1, int(value)) if value and len(value) <= 9 and all('0' <= ch <= '9' for ch in value) else 1


def _source_rows(category, admin, source):
    if source in ('', 'local'):
        try:
            local = inventory.read(admin.pk, (category,))[category]
        except PermissionError:
            raise Http404()
        except DatabaseError:
            local = None
        yield 'local', 'This server', '', local, 'Current' if local is not None else 'Unavailable'
    if source == 'local':
        return
    active = models.Node.objects.filter(status=models.ACTIVE)
    if source:
        active = active.filter(pk=source)
    inventory_cache.refresh(active, admin.userName, int(time.time()))
    for node, saved, fetched, error in inventory_cache.sources(active):
        snapshot, status = inventory_cache.contents(node, saved, fetched, error, int(time.time()))
        try:
            authority = links.link_of(node).authority
        except (links.LinkError, transport.TransportError, ValueError):
            snapshot, status, authority = None, 'Unavailable', ''
        try:
            label = links.check_label(node.label)
        except links.InvalidLabel:
            label = 'Unnamed node'
        label += ' · ' + (authority or node.pk[:8])
        yield node.pk, label, 'https://' + authority, snapshot and snapshot[category], status


def _query(query, source, page=1, servers=1):
    return '?' + urlencode({'q': query, 'source': source, 'page': page, 'servers': servers})


def _native(category, name):
    if category == 'websites':
        return reverse('siteWorkspace', args=[name])
    return reverse('listDBs' if category == 'databases' else 'listEmails')


@never_cache
def index(request, category):
    admin = nodes.administrator(request)
    if not admin or category not in TITLES:
        raise Http404()
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    from plogical.httpProc import httpProc
    title, name_heading, detail_heading = TITLES[category]
    context = {'category': category, 'inventory_title': title, 'name_heading': name_heading,
               'detail_heading': detail_heading, 'row_limit': inventory.ROW_LIMIT, 'licensed': entitlement.allowed()}
    if not context['licensed']:
        response = httpProc(request, 'multiServer/inventory.html', context).render()
        response.status_code = 403
        return response

    query = request.GET.get('q', '')[:100].strip()
    source = request.GET.get('source', '')
    if source not in ('', 'local') and not links._is_link_id(source):
        raise Http404()
    page, servers = _page(request.GET.get('page')), _page(request.GET.get('servers'))
    first, first_server = (page - 1) * PAGE_SIZE, (servers - 1) * SOURCE_PAGE_SIZE
    count, source_count = 0, 0
    partial = False
    rows, badges = [], []
    for key, label, origin, batch, status in _source_rows(category, admin, source):
        if batch and batch['partial']:
            status += ' · partial inventory'
            partial = True
        if first_server <= source_count < first_server + SOURCE_PAGE_SIZE:
            badges.append((label, status, _query(query, key)))
        source_count += 1
        for name, detail in batch['rows'] if batch else ():
            if category == 'websites':
                detail = 'Active' if detail == 1 else 'Suspended'
            if query.casefold() not in ' '.join((name, detail, label)).casefold():
                continue
            if first <= count < first + PAGE_SIZE:
                rows.append((name, detail, label, origin + _native(category, name), status))
            count += 1
    if (page > 1 and first >= count) or (servers > 1 and first_server >= source_count):
        return HttpResponseRedirect(_query(query, source))
    context.update(query=query, source=source, rows=rows, badges=badges, count=count, page=page, partial=partial,
                   all_sources=_query(query, ''), pages=max(1, (count + PAGE_SIZE - 1) // PAGE_SIZE),
                   prev=_query(query, source, page - 1, servers) if page > 1 else '',
                   next=_query(query, source, page + 1, servers) if count > first + PAGE_SIZE else '',
                   prev_sources=_query(query, source, page, servers - 1) if servers > 1 else '',
                   next_sources=_query(query, source, page, servers + 1) if source_count > first_server + SOURCE_PAGE_SIZE else '')
    return httpProc(request, 'multiServer/inventory.html', context).render()
