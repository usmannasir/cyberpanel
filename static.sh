#!/bin/bash
python manage.py collectstatic
rm -rf /usr/local/lscp/cyberpanel/static
mv /usr/local/CyberCP/static /usr/local/lscp/cyberpanel/
service gunicorn.socket restart
