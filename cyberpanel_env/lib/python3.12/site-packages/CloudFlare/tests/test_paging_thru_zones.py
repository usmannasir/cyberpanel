""" paging thru zones tests """

import os
import sys

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test paging thru zones with raw option

cf = None

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(raw=True, debug=debug)
    assert isinstance(cf, CloudFlare.CloudFlare)

def paging_thru_zones(name=None):
    """ paging_thru_zones """
    count_received = 0
    total_count = 0 # we want to confirm this total later
    page_number = 0
    while True:
        page_number += 1
        params = {'per_page':10,'page':page_number,'name':name}
        try:
            raw_results = cf.zones.get(params=params)
        except CloudFlare.exceptions.CloudFlareAPIError:
            assert False

        assert 'result_info' in raw_results
        assert 'result' in raw_results

        results_info = raw_results['result_info']
        results = raw_results['result']

        assert 'count' in results_info
        assert 'page' in results_info
        assert 'per_page' in results_info
        assert 'total_count' in results_info
        assert 'total_pages' in results_info

        count = results_info['count']
        page = results_info['page']
        per_page = results_info['per_page']
        total_count = results_info['total_count']
        total_pages = results_info['total_pages']

        assert isinstance(count, int)
        assert isinstance(page, int)
        assert isinstance(per_page, int)
        assert isinstance(total_count, int)
        assert isinstance(total_pages, int)

        assert page_number == page

        assert len(results) == count
        assert isinstance(results, list)

        count_received += count

        domains = []
        for zone in results:
            assert 'id' in zone
            assert 'name' in zone
            zone_name = zone['name']
            domains.append(zone_name)
        print("COUNT=%d PAGE=%d PER_PAGE=%d TOTAL_COUNT=%d TOTAL_PAGES=%d -- %s" % (
            count,
            page,
            per_page,
            total_count,
            total_pages,
            ','.join(domains)
        ), file=sys.stderr)

        if count == 0 or page_number >= total_pages:
            # finished
            break

    # did we receive all the info?
    assert count_received == total_count

def test_paging_thru_zones():
    """ test_paging_thru_zones """
    paging_thru_zones(None)

def test_paging_thru_zones_match_com():
    """ test_paging_thru_zones_match_com """
    # we assume your account has one of these domains
    paging_thru_zones('ends_with:.com')

def test_paging_thru_zones_match_nothing():
    """ test_paging_thru_zones_match_nothing """
    paging_thru_zones('QWERTYUIOOP')

if __name__ == '__main__':
    test_cloudflare(debug=True)
    test_paging_thru_zones()
    test_paging_thru_zones_match_com()
    test_paging_thru_zones_match_nothing()
