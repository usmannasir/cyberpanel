# -*- coding: utf-8 -*-
"""Firewall rule display order helpers (MariaDB sortOrder)."""
from __future__ import unicode_literals

from django.db import transaction
from django.db.models import Max

from firewall.models import FirewallRules


def ensure_sort_orders():
    """Backfill sortOrder for rows that still use the default 0."""
    rules = list(FirewallRules.objects.all().order_by('id'))
    needs = [r for r in rules if not r.sortOrder or r.sortOrder <= 0]
    if not needs and rules:
        # Also normalize gaps if every row already has a positive order
        return
    if not rules:
        return
    with transaction.atomic():
        for idx, rule in enumerate(rules, start=1):
            if rule.sortOrder != idx:
                rule.sortOrder = idx
                rule.save(update_fields=['sortOrder'])


def next_sort_order():
    """Return the next sortOrder value for a newly added rule."""
    ensure_sort_orders()
    current = FirewallRules.objects.aggregate(m=Max('sortOrder')).get('m') or 0
    return int(current) + 1


def ordered_queryset():
    """Rules queryset ordered for UI and apply paths."""
    ensure_sort_orders()
    return FirewallRules.objects.all().order_by('sortOrder', 'id')


def renumber_all():
    """Force contiguous sortOrder values 1..n in current order."""
    rules = list(FirewallRules.objects.all().order_by('sortOrder', 'id'))
    with transaction.atomic():
        for idx, rule in enumerate(rules, start=1):
            if rule.sortOrder != idx:
                rule.sortOrder = idx
                rule.save(update_fields=['sortOrder'])
    return [r.id for r in rules]


def apply_ordered_ids(ordered_ids):
    """
    Persist a full global order from a list of primary keys.
    Returns the new ordered id list (1..n).
    """
    if not isinstance(ordered_ids, (list, tuple)) or not ordered_ids:
        raise ValueError('ordered_ids must be a non-empty list of rule IDs')

    try:
        ordered_ids = [int(x) for x in ordered_ids]
    except (TypeError, ValueError):
        raise ValueError('ordered_ids must contain integers')

    existing = list(FirewallRules.objects.values_list('id', flat=True))
    if sorted(ordered_ids) != sorted(existing):
        raise ValueError('ordered_ids must include every firewall rule exactly once')

    with transaction.atomic():
        for idx, rule_id in enumerate(ordered_ids, start=1):
            FirewallRules.objects.filter(id=rule_id).update(sortOrder=idx)
    return ordered_ids


def apply_page_order(page_ordered_ids, page, page_size):
    """
    Replace the slice for the given page with page_ordered_ids and renumber.
    """
    if not isinstance(page_ordered_ids, (list, tuple)) or not page_ordered_ids:
        raise ValueError('page_ordered_ids must be a non-empty list')

    try:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        page_ordered_ids = [int(x) for x in page_ordered_ids]
    except (TypeError, ValueError):
        raise ValueError('Invalid page reorder payload')

    all_ids = list(ordered_queryset().values_list('id', flat=True))
    start = (page - 1) * page_size
    end = start + page_size
    current_slice = all_ids[start:end]

    if sorted(page_ordered_ids) != sorted(current_slice):
        raise ValueError('page_ordered_ids must be a permutation of the current page')

    all_ids[start:start + len(page_ordered_ids)] = page_ordered_ids
    return apply_ordered_ids(all_ids)


def move_rule(rule_id, direction):
    """
    Move a rule one step up or down in the global order.
    direction: 'up' | 'down'
    """
    direction = (direction or '').strip().lower()
    if direction not in ('up', 'down'):
        raise ValueError("direction must be 'up' or 'down'")

    try:
        rule_id = int(rule_id)
    except (TypeError, ValueError):
        raise ValueError('Invalid rule id')

    ids = list(ordered_queryset().values_list('id', flat=True))
    if rule_id not in ids:
        raise ValueError('Rule not found')

    idx = ids.index(rule_id)
    if direction == 'up':
        if idx == 0:
            return ids
        ids[idx - 1], ids[idx] = ids[idx], ids[idx - 1]
    else:
        if idx >= len(ids) - 1:
            return ids
        ids[idx + 1], ids[idx] = ids[idx], ids[idx + 1]

    return apply_ordered_ids(ids)
