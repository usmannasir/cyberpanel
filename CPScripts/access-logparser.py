#!/usr/bin/python
# -*- coding: utf-8 -*-
# Originally based on code from: https://leancrew.com/all-this/2013/07/parsing-my-apache-logs/

import os
import re
import sys
from collections import Counter
from datetime import datetime, date, timedelta


# print('version is', sys.version)

def detectcontrolpanel():
    global controlpanel
    try:
        if os.path.isfile('/usr/local/cpanel/cpanel'):
            controlpanel = 'cpanel'
    except:
        controlpanel = 'Control Panel not found'

    try:
        if os.path.isfile('/usr/bin/cyberpanel'):
            controlpanel = 'cyberpanel'
    except:
        controlpanel = 'Control Panel not found'
    return controlpanel


def main():
    script = sys.argv[0]
    filename = sys.argv[2]
    # filenametest = "/home/example.com.access_log"

    # Define the day of interest in the Apache common log format.
    try:
        daysAgo = int(sys.argv[1])
        # daysAgo = 2
    except:
        daysAgo = 1
    theDay = date.today() - timedelta(daysAgo)
    apacheDay = theDay.strftime('[%d/%b/%Y:')

    # Regex for the Apache common log format.
    parts = [  # host %h  			:ip/hostname of the client 	172.68.142.138
        # indent %l (unused) 	:client identity via client's identd configuration 	-
        # user %u 			:HTTP authenticated user ID 	-
        # time %t 			:timestamp 	[09/Mar/2019:00:38:03 -0600]
        # request "%r" 		:request method of request, resource requested, & protocol 	"POST /wp-login.php HTTP/1.1"
        # status %>s 		:Apache status code 	404
        # size %b (careful,can be'-'):size of request in bytes, excluding headers 	3767
        # referrer "%{Referer}i"	:Referer 	"https://www.google.com/"
        # user agent "%{User-agent}i":User-Agent 	"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 SE 2.X MetaSr 1.0"
        r'(?P<host>\S+)',
        r'\S+',
        r'(?P<user>\S+)',
        r'\[(?P<time>.+)\]',
        r'"(?P<request>.*)"',
        r'(?P<status>[0-9]+)',
        r'(?P<size>\S+)',
        r'"(?P<referrer>.*)"',
        r'"(?P<agent>.*)"',
    ]
    pattern = re.compile(r'\s+'.join(parts) + r'\s*\Z')

    # Regex for a feed request.
    feed = re.compile(r'/all-this/(\d\d\d\d/\d\d/[^/]+/)?feed/(atom/)?')

    # Regexes for internal and Google search referrers.

    internal = re.compile(r'https?://(www\.)?example\.com.*')
    google = re.compile(r'https?://(www\.)?google\..*')

    # Regexes for Uptime Monitoring Robots
    uptimeroboturl = re.compile(r'https?://(www\.)?uptimerobot\..*')
    uptimerobot = re.compile(r'UptimeRobot')

    # WordPress CMS Regex
    wordpresslogin = re.compile(r'wp-login\.php.*')
    wordpressadmin = re.compile(r'wp-admin')
    wordpresscron = re.compile(r'wp-cron\.php.*')
    wordpressxmlrpc = re.compile(r'xmlrpc\.php')
    wordpressajax = re.compile(r'admin-ajax\.php')

    # Change Apache log items into Python types.

    def pythonized(d):
        # Clean up the request.

        d['request'] = d['request'].split()[1]

        # Some dashes become None.

        for k in ('user', 'referrer', 'agent'):
            if d[k] == '-':
                d[k] = None

        # The size dash becomes 0.

        if d['size'] == '-':
            d['size'] = 0
        else:
            d['size'] = int(d['size'])

        # Convert the timestamp into a datetime object. Accept the server's time zone.

        (time, zone) = d['time'].split()
        d['time'] = datetime.strptime(time, '%d/%b/%Y:%H:%M:%S')

        return d

    # Is this hit a page?

    def ispage(hit):
        # Failures and redirects.

        hit['status'] = int(hit['status'])
        if hit['status'] < 200 or hit['status'] >= 300:
            return False

        # Feed requests.

        if feed.search(hit['request']):
            return False

        # Requests that aren't GET.

        #    if (hit['request'])[0:3] != 'GET':
        #        return False

        # Images, sounds, etc.

        if hit['request'].split()[1][-1] != '/':
            return False

        # Requests that aren't Head type. AKA uptime monitoring

        if (hit['request'])[0:3] == 'HEAD':
            return False

        # Must be a page.

        return True

    # Is the referrer interesting? Internal and Google referrers are not.
    def goodref(hit):
        if hit['referrer']:
            return not (google.search(hit['referrer'])
                        or internal.search(hit['referrer']))
        else:
            return False

    # Is the user agent interesting? An uptime monitoring robot is not.
    def goodagent(hit):
        if hit['agent']:
            return not (uptimerobot.search(hit['agent'])
                        or uptimeroboturl.search(hit['agent']))
        else:
            return False

    # Is the request a Wordpress related login event?
    def wordpressbrute(hit):
        if hit['request']:
            return (wordpresslogin.search(hit['request'])
                    or wordpressadmin.search(hit['request']))
        else:
            return False

    # Initialize.

    pages = []

    # Parse all the lines associated with the day of interest.

    # Open file
    log = open(filename)
    for line in log:
        if apacheDay in line:
            m = pattern.match(line)
            hit = m.groupdict()
            if ispage(hit):
                pages.append(pythonized(hit))
        else:
            continue
    log.close()

    # Show the top five pages and the total.

    print ('Show top 10 pages %s' % theDay.strftime('%b %d, %Y'))
    pageviews = Counter(x['request'] for x in pages if goodagent(x))
    pagestop10 = pageviews.most_common(10)
    for p in pagestop10:
        print ('  %5d  %s' % p[::-1])
    print ('  %5d  total' % len(pages))

    # Show the top five referrers.

    print ('''
    Show top 10 referrers %s''' % theDay.strftime('%b %d, %Y'))
    referrers = Counter(x['referrer'] for x in pages if goodref(x))
    referrerstop10 = referrers.most_common(10)
    for r in referrerstop10:
        print ('  %5d  %s' % r[::-1])
    print ('  %5d  total' % sum(referrers.values()))

    # Show the top 10 IPs.
    print ('''
    Show Top 10 IPs %s''' % theDay.strftime('%b %d, %Y'))
    iphits = Counter(x['host'] for x in pages if goodagent(x))
    iptop10 = iphits.most_common(10)
    for p in iptop10:
        print ('  %5d  %s' % p[::-1])
    print ('  %5d  total hits' % sum(iphits.values()))

    # CMS Checks

    # Wordpress Checks
    # Wordpress Login Bruteforcing checks for wp-login.php
    print ('''
    Wordpress Bruteforce Logins for wp-login.php %s''' % theDay.strftime('%b %d, %Y'))
    wordpressloginhits = Counter(x['request'] for x in pages if wordpressbrute(x))
    # wordpresslogintop10 = wordpressloginhits.most_common(10)
    # for p in wordpresslogintop10:
    #    print '  %5d  %s' % p[::-1]
    print ('  %5d  total' % sum(wordpressloginhits.values()))


if __name__ == '__main__':
    # detectcontrolpanel()
    main()