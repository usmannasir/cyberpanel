#!/bin/bash

set_header() {
if [[ -f /usr/local/lsws/conf/vhosts/$1/vhost.conf ]] ; then
cat << EOF > header.txt

context /wp-content/cache/css/ {
  location                $DOC_ROOT/wp-content/cache/css/
  allowBrowse             1
  enableExpires           1
  expiresByType           text/css=A15552000
  extraHeaders            <<<END_extraHeaders
unset Cache-control
set Cache-control public, max-age=15552000
set Access-Control-Allow-Origin: *
  END_extraHeaders


  rewrite  {

  }
  addDefaultCharset       off

  phpIniOverride  {

  }
}

context /wp-content/cache/js/ {
  location                $DOC_ROOT/wp-content/cache/js/
  allowBrowse             1
  enableExpires           1
  expiresByType           application/x-javascript=A15552000, text/javascript=A15552000, application/javascript=A15552000
  extraHeaders            <<<END_extraHeaders
unset Cache-control
set Cache-control public, max-age=15552000
set Access-Control-Allow-Origin: *
  END_extraHeaders


  rewrite  {

  }
  addDefaultCharset       off

  phpIniOverride  {

  }
}

context exp:^.*(css|gif|ico|jpeg|jpg|js|png|webp|woff|woff2|fon|fot|ttf)$ {
  location                $DOC_ROOT/$0
  allowBrowse             1
  enableExpires           1
  expiresByType           text/css=A15552000, image/gif=A15552000, image/x-icon=A15552000, image/jpeg=A15552000, application/x-javascript=A15552000, text/javascript=A15552000, application/javascript=A15552000, image/png=A15552000, image/webp=A15552000, font/ttf=A15552000, font/woff=A15552000, font/woff2=A15552000, application/x-font-ttf=A15552000, application/x-font-woff=A15552000, application/font-woff=A15552000, application/font-woff2=A15552000
  extraHeaders            <<<END_extraHeaders
unset Cache-control
set Cache-control public, max-age=15552000
set Access-Control-Allow-Origin: *
  END_extraHeaders


  rewrite  {

  }
  addDefaultCharset       off

  phpIniOverride  {

  }
}
EOF

cat header.txt >> /usr/local/lsws/conf/vhosts/$1/vhost.conf
fi
}

if /usr/local/lsws/bin/lshttpd -v | grep -iF open ; then
  echo -e "\nOpenLiteSpeed detected..."
  set_header
else
  echo -e "\nLiteSpeed Enterprise detected..."
  exit
  #LiteSpeed Enterprise can read htaccess for expire header, no need to set it up.
fi

rm -f header.txt
rm -f $0
echo -e "\nexpire , cache-control and CORS header set..."
