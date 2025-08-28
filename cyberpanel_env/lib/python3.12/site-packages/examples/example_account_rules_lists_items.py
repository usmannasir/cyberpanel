#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import time

# sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():

    # Code up ...
    # cli4 /accounts/::00000000000000000000000000000000/rules/lists/::00000000000000000000000000000000/items

    try:
        account_id = sys.argv[1]
        list_id = sys.argv[2]
    except IndexError:
        exit('usage: example_account_rules_lists_items.py account_id list_id')

    with CloudFlare.CloudFlare() as cf:

        #
        # Print existing list - showing GET function
        #
        print('EXISTING LIST LOOKS LIKE:')
        items = cf.accounts.rules.lists.items(account_id, list_id)
        for item in items:
            print('%s %s %s %-30s ; %s' % (item['id'], item['created_on'], item['modified_on'], item['ip'], item['comment']))
        print('')

        #
        # Add an element to list - showing POST function
        #
        new_ip_address = '4.4.4.4'
        new_ip_comment = 'all the fours!'
        new_ip_id = None

        print('ADD TO LIST:')
        new_r = cf.accounts.rules.lists.items.post(account_id, list_id, data=[{'ip':new_ip_address,'comment':new_ip_comment}])
        print('new_r = %s' % (new_r))
        print('')

        #
        # So it seems that it takes a while for the database to update; this is delay is a hack
        #
        time.sleep(1)

        #
        # Print the full list again - to show POST worked
        #
        print('NEW LIST LOOKS LIKE:')
        items = cf.accounts.rules.lists.items(account_id, list_id)
        for item in items:
            print('%s %s %s %-30s ; %s' % (item['id'], item['created_on'], item['modified_on'], item['ip'], item['comment']))
            if item['ip'] == new_ip_address:
                new_ip_id = item['id']
        print('')

        #
        # Now remove that element - to show DELETE function (note the use of new_ip_id value
        #
        print('DELETE FROM LIST:')
        if new_ip_id is None:
            exit('    --- NOTHING TO DELETE')
        del_r = cf.accounts.rules.lists.items.delete(account_id, list_id, data={'items':[{'id':new_ip_id}]})
        print('del_r = %s' % (del_r))
        print('')

        #
        # So it seems that it takes a while for the database to update; this is delay is a hack
        #
        time.sleep(1)

        #
        # Print the full list again - to show DELETE worked
        #
        print('FINAL LIST LOOKS LIKE:')
        items = cf.accounts.rules.lists.items(account_id, list_id)
        for item in items:
            print('%s %s %s %-30s ; %s' % (item['id'], item['created_on'], item['modified_on'], item['ip'], item['comment']))
        print('')

    exit(0)

if __name__ == '__main__':
    main()
