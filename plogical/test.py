import requests
import re
import sys
import warnings
from flask import Flask, request, render_template, redirect, url_for
from io_parser import FormParser
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter('ignore', InsecureRequestWarning)

app = Flask(__name__)
app.debug = True
app.config.update(
    JSON_SORT_KEYS=False,
    JSONIFY_PRETTYPRINT_REGULAR=True
)

view = 'index.html'


@app.route('/', methods=['GET'])
def explore():
    error = {
        'types': set(),
        'input': [],
    }
    http = None
    x_lsadc_cache, x_qc_cache, x_litespeed_cache, cf_cache_cache, browser_cache, cache_support, x_sucuri_cache = (
                                                                                                                 False,) * 7
    fp = FormParser(host=request.args.get('host'), ip=request.args.get('ip'),
                    port=request.args.get('port'),
                    advanced=request.args.get('advanced'))

    if not fp.host:
        return render_template(view, form=fp.__dict__())
    if fp.check_error():
        error['types'].add('input')
        error['input'] = fp.error_msgs
        return render_template(view, form=fp.__dict__(), error=error)
    form = fp.__dict__()

    finalURL = ''

    if form['url'].find('http') == -1:
        finalURL = 'https://%s' % (form['url'])
    else:
        finalURL = form['url']

    try:

        resp = requests.get('' + (finalURL, form['ip'])[form['advanced']], headers={
            'Host': form['host'],
            'User-Agent': 'wget/http3check.net',
        }, verify=False)

        http = [key + ': ' + value for key, value in resp.headers.items() if key != 'Link']
        http.insert(0, 'HTTP/1.1 {} {}'.format(resp.status_code, resp.reason))
        for key, value in resp.headers.items():
            key = key.lower()
            value = value.lower()
            if key == 'x-lsadc-cache':
                if value == 'hit':
                    x_lsadc_cache = True
                cache_support = True
            elif key == 'x-qc-cache':
                if value == 'hit':
                    x_qc_cache = True
                cache_support = True
            elif key == 'x-litespeed-cache':
                if value == 'hit':
                    x_litespeed_cache = True
                cache_support = True
            elif key == 'cf-cache-status':
                if value == 'hit':
                    cf_cache_cache = True
            elif key == 'cache-control':
                if 'no-cache' not in value and 'max-age=0' not in value:
                    browser_cache = True
            elif key == 'x-sucuri-cache':
                if value == 'hit':
                    x_sucuri_cache = True

            finalHTTP = []
            from flask import Markup

            for items in http:
                if items.lower().find('x-litespeed-cache:') > -1 or items.lower().find('x-lsadc-cache:') > -1 or items.lower().find(
                        'x-qc-cache:') > -1:
                    finalHTTP.append(Markup('<strong>%s</strong>' % (items)))
                elif items.lower().find('link:') > -1:
                    pass
                else:
                    finalHTTP.append(items)

        return render_template(view, cache_support=cache_support, x_lsadc_cache=x_lsadc_cache, x_qc_cache=x_qc_cache,
                               x_litespeed_cache=x_litespeed_cache, cf_cache_cache=cf_cache_cache,
                               x_sucuri_cache=x_sucuri_cache,
                               browser_cache=browser_cache, form=form, http=finalHTTP)
    except BaseException as msg:
        return render_template(view, form={}, error=str(msg))


@app.route('/<page>', methods=['GET'])
def home(page):
    if page == 'about' or page == 'about.html':
        return render_template(view, about=True)
        # return redirect("https://lscache.io/", code=302)
    return redirect(url_for('explore'))

if __name__ == '__main__':
    app.run(host= '0.0.0.0')