#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys

sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    cf = CloudFlare.CloudFlare()

    print('USER:')
    # grab the user info
    try:
        user = cf.user.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/user.get %d %s - api call failed' % (e, e))
    except Exception as e:
        exit('/user.get - %s - api call failed' % (e))
    for k in sorted(user.keys()):
        if isinstance(user[k], list):
            if isinstance(user[k][0], dict):
                print('\t%-40s =' % (k))
                for l in user[k]:
                    for j in sorted(l.keys()):
                        if isinstance(l[j], list):
                            print('\t%-40s   %s = [ %s ]' % ('', j, ', '.join(l[j])))
                        else:
                            print('\t%-40s   %s = %s' % ('', j, l[j]))
            else:
                print('\t%-40s = [ %s ]' % (k, ', '.join(user[k])))
        elif isinstance(user[k], dict):
            print('\t%-40s =' % (k))
            for j in sorted(user[k].keys()):
                print('\t%-40s   %s = %s' % ('', j, user[k][j]))
        else:
            print('\t%-40s = %s' % (k, user[k]))
    print('')

    print('ORGANIZATIONS:')
    # grab the user organizations info
    try:
        organizations = cf.user.organizations.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/user.organizations.get %d %s - api call failed' % (e, e))
    if len(organizations) == 0:
        print('\tNo organization')
    for organization in organizations:
        organization_name = organization['name']
        organization_id = organization['id']
        organization_status = organization['status']
        print('\t%-40s %-10s %s' % (organization_id, organization_status, organization_name))
    print('')

    print('INVITES:')
    # grab the user invites info
    try:
        invites = cf.user.invites.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/user.invites.get %d %s - api call failed' % (e, e))
    if len(invites) == 0:
        print('\tNo user invites')
    for invite in invites:
        invited_member_id = invite['invited_member_id']
        invited_member_email = invite['invited_member_email']
        organization_id = invite['organization_id']
        organization_name = invite['organization_name']
        invited_by = invite['invited_by']
        invited_on = invite['invited_on']
        expires_on = invite['expires_on']
        status = invite['status']
        print('\t %s %s %s %s %s %s %s %s' % (
            organization_id,
            status,
            invited_member_id,
            invited_member_email,
            organization_name,
            invited_by,
            invited_on,
            expires_on
        ))
    print('')

    print('BILLING:')
    # grab the user billing profile info
    try:
        profile = cf.user.billing.profile.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/user.billing.profile.get %d %s - api call failed' % (e, e))
    profile_id = profile['id']
    profile_first = profile['first_name']
    profile_last = profile['last_name']
    profile_company = profile['company']
    if profile_company is None:
        profile_company = ''

    if profile['payment_email'] != '':
        payment_email = profile['payment_email']
        card_number = None
        card_expiry_year = None
        card_expiry_month = None
    else:
        payment_email = None
        card_number = profile['card_number']
        card_expiry_year = profile['card_expiry_year']
        card_expiry_month = profile['card_expiry_month']

    if payment_email is not None:
        print('\t %s %s %s %s PayPal: %s' % (
            profile_id,
            profile_first,
            profile_last,
            profile_company,
            payment_email
        ))
    else:
        if card_number is None:
            card_number = '---- ---- ----- ----'
        if card_expiry_year is not None and card_expiry_month is not None:
            card_expiry = card_expiry_month + '/' + card_expiry_year
        else:
            card_expiry = '--/--'
        print('\t %s %s %s %s CC: %s %s' % (
            profile_id,
            profile_first,
            profile_last,
            profile_company,
            card_number,
            card_expiry
        ))

    print('')

    print('BILLING HISTORY:')
    # grab the user billing history info
    try:
        history = cf.user.billing.history.get()
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        exit('/user.billing.history.get %d %s - api call failed' % (e, e))
    if len(history) == 0:
        print('\tNo billing history')
    for h in sorted(history, key=lambda v: v['occurred_at']):
        history_id = h['id']
        history_type = h['type']
        history_action = h['action']
        history_occurred_at = h['occurred_at']
        history_amount = h['amount']
        history_currency = h['currency']
        history_description = h['description']
        print('\t %s %s %s %s %s %s %s' % (
            history_id,
            history_type,
            history_action,
            history_occurred_at,
            history_amount,
            history_currency,
            history_description
        ))

    print('')

    exit(0)

if __name__ == '__main__':
    main()

