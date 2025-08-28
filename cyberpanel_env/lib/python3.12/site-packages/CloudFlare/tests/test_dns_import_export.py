""" dns import/export test """

import os
import sys
import uuid
import time
import random
import tempfile

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test IMPORT EXPORT

cf = None

def test_cloudflare():
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare()
    assert isinstance(cf, CloudFlare.CloudFlare)

zone_name = None
zone_id = None

def test_find_zone(domain_name=None):
    """ test_find_zone """
    global zone_name, zone_id
    # grab a random zone identifier from the first 10 zones
    if domain_name:
        params = {'per_page':1, 'name':domain_name}
    else:
        params = {'per_page':10}
    try:
        zones = cf.zones.get(params=params)
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('%s: Error %d=%s' % (domain_name, int(e), str(e)), file=sys.stderr)
        assert False
    assert len(zones) > 0 and len(zones) <= 10
    n = random.randrange(len(zones))
    zone_name = zones[n]['name']
    zone_id = zones[n]['id']
    assert len(zone_id) == 32
    print('zone: %s %s' % (zone_id, zone_name), file=sys.stderr)

def test_dns_import():
    """ test_dns_import """
    # IMPORT
    # create a zero length file
    fp = tempfile.TemporaryFile(mode='w+b')
    fp.seek(0)
    while True:
        try:
            results = cf.zones.dns_records.import_.post(zone_id, files={'file':fp})
            break
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            print('cf.zones.dns_records.import: returned %d "%s"' % (int(e), str(e))) # 429 or 99998
            time.sleep(.5) # This is sadly needed as import seems to be rate limited
            fp.seek(0)
    # {"recs_added": 0, "recs_added_by_type": {}, "total_records_parsed": 0}
    assert len(results) > 0
    assert results['recs_added'] == 0
    assert len(results['recs_added_by_type']) == 0
    assert results['total_records_parsed'] == 0

def test_dns_export():
    """ test_dns_export """
    # EXPORT
    dns_records = cf.zones.dns_records.export.get(zone_id)
    assert len(dns_records) > 0
    assert isinstance(dns_records, str)
    assert 'SOA' in dns_records
    assert 'NS' in dns_records

def test_cloudflare_with_debug():
    """ test_cloudflare_with_debug """
    global cf
    cf = CloudFlare.CloudFlare(debug=True)
    assert isinstance(cf, CloudFlare.CloudFlare)

def test_dns_import_with_debug():
    """ test_dns_import_with_debug """
    # IMPORT
    # create a zero length file
    fp = tempfile.TemporaryFile(mode='w+b')
    fp.seek(0)
    while True:
        try:
            results = cf.zones.dns_records.import_.post(zone_id, files={'file':fp})
            break
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            print('cf.zones.dns_records.import: returned %d "%s"' % (int(e), str(e))) # 429 or 99998
            time.sleep(.5) # This is sadly needed as import seems to be rate limited
            fp.seek(0)
    # {"recs_added": 0, "recs_added_by_type": {}, "total_records_parsed": 0}
    assert len(results) > 0
    assert results['recs_added'] == 0
    assert len(results['recs_added_by_type']) == 0
    assert results['total_records_parsed'] == 0

def test_dns_export_with_debug():
    """ test_dns_export_with_debug """
    # EXPORT
    dns_records = cf.zones.dns_records.export.get(zone_id)
    assert len(dns_records) > 0
    assert isinstance(dns_records, str)
    assert 'SOA' in dns_records
    assert 'NS' in dns_records

if __name__ == '__main__':
    test_cloudflare()
    if len(sys.argv) > 1:
        test_find_zone(sys.argv[1])
    else:
        test_find_zone()
    test_dns_import()
    test_dns_export()
    test_cloudflare_with_debug()
    test_dns_import_with_debug()
    test_dns_export_with_debug()
