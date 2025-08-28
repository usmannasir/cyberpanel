""" waiting_room tests """

import os
import sys
import random

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

# test waiting_rooms

cf = None

def test_cloudflare(debug=False):
    """ test_cloudflare """
    global cf
    cf = CloudFlare.CloudFlare(debug=debug)
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

def test_waiting_room_s():
    """ test_waiting_room_s """
    s = str(cf.zones.waiting_rooms.events.details)
    assert isinstance(s, str)

def test_waiting_room():
    """ test_waiting_room """
    waiting_rooms = cf.zones.waiting_rooms(zone_id)
    assert isinstance(waiting_rooms, list)
    for waiting_room in waiting_rooms:
        assert isinstance(waiting_room, dict)

def test_waiting_room_settings():
    """ test_waiting_room_settings """
    settings = cf.zones.waiting_rooms.settings(zone_id)
    assert isinstance(settings, dict)
    assert 'search_engine_crawler_bypass' in settings

def test_waiting_room_preview():
    """ test_waiting_room_preview """
    # we expect failure
    try:
        r = cf.zones.waiting_rooms.preview(zone_id)
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert True

def test_waiting_room_events_details():
    """ test_waiting_room_events_details """
    waiting_room_id = '00000000000000000000000000000000'
    event_id = '00000000000000000000000000000000'
    # we expect failure - we are mainly testing three id style calls!
    try:
        r = cf.zones.waiting_rooms.events.details(zone_id, waiting_room_id, event_id)
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert True

def test_waiting_room_post():
    """ test_waiting_room_post """
    # we expect failure - we don't expect to create a waiting_room
    waiting_room_data = {
        'host': 'example.com',
        'path': 'waiting_room.html',
        'name': 'waiting_room_testing',
        'description': 'Waiting Room Testing',
        'suspended': True,
        'new_users_per_minute': 1e6,
        'total_active_users': 2e6
    }
    try:
        new_waitng_room = cf.zones.waiting_rooms.post(zone_id, data=waiting_room_data)
        print('new_waiting_room=', new_waiting_room, file=sys.stderr)
        assert False
    except CloudFlare.exceptions.CloudFlareAPIError as e:
        print('Error expected: %d %s' % (int(e), str(e)), file=sys.stderr)
        assert True

if __name__ == '__main__':
    test_cloudflare(debug=True)
    if len(sys.argv) > 1:
        test_find_zone(sys.argv[1])
    else:
        test_find_zone()
    test_waiting_room_s()
    test_waiting_room()
    test_waiting_room_settings()
    test_waiting_room_preview()
    test_waiting_room_events_details()
    test_waiting_room_post()
