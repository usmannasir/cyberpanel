class vhostConfs:

    olsMasterMainConf = """virtualHost {virtualHostName} {
  vhRoot                  /home/$VH_NAME
  configFile              $SERVER_ROOT/conf/vhosts/$VH_NAME/vhost.conf
  allowSymbolLink         1
  enableScript            1
  restrained              1
}
"""

    olsMasterConf = """docRoot                   $VH_ROOT/public_html
vhDomain                  $VH_NAME
vhAliases                 www.$VH_NAME
adminEmails               {adminEmails}
enableGzip                1
enableIpGeo               1

index  {
  useServer               0
  indexFiles              index.php, index.html
}

errorlog $VH_ROOT/logs/$VH_NAME.error_log {
  useServer               0
  logLevel                ERROR
  rollingSize             10M
}

accesslog $VH_ROOT/logs/$VH_NAME.access_log {
  useServer               0
  logFormat               "%v %h %l %u %t "%r" %>s %b"
  logHeaders              5
  rollingSize             10M
  keepDays                10  compressArchive         1
}

scripthandler  {
  add                     lsapi:{virtualHostUser} php
}

extprocessor {virtualHostUser} {
  type                    lsapi
  address                 UDS://tmp/lshttpd/{virtualHostUser}.sock
  maxConns                10
  env                     LSAPI_CHILDREN=10
  initTimeout             600
  retryTimeout            0
  persistConn             1
  pcKeepAliveTimeout      1
  respBuffer              0
  autoStart               1
  path                    /usr/local/lsws/lsphp{php}/bin/lsphp
  extUser                 {virtualHostUser}
  extGroup                {virtualHostUser}
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           400
  procHardLimit           500
}

phpIniOverride  {
{open_basedir}
}

rewrite  {
  enable                  1
  autoLoadHtaccess        1
}
"""

    olsChildMainConf = """virtualHost {virtualHostName} {
  vhRoot                  /home/{masterDomain}
  configFile              $SERVER_ROOT/conf/vhosts/$VH_NAME/vhost.conf
  allowSymbolLink         1
  enableScript            1
  restrained              1
}
"""

    olsChildConf =  """docRoot                   {path}
vhDomain                  $VH_NAME
vhAliases                 www.$VH_NAME
adminEmails               {adminEmails}
enableGzip                1
enableIpGeo               1

index  {
  useServer               0
  indexFiles              index.php, index.html
}

errorlog $VH_ROOT/logs/{masterDomain}.error_log {
  useServer               0
  logLevel                ERROR
  rollingSize             10M
}

accesslog $VH_ROOT/logs/{masterDomain}.access_log {
  useServer               0
  logFormat               "%v %h %l %u %t "%r" %>s %b"
  logHeaders              5
  rollingSize             10M
  keepDays                10  compressArchive         1
}

phpIniOverride  {
{open_basedir}
}
scripthandler  {
  add                     lsapi:{externalApp} php
}

extprocessor {externalApp} {
  type                    lsapi
  address                 UDS://tmp/lshttpd/{externalApp}.sock
  maxConns                10
  env                     LSAPI_CHILDREN=10
  initTimeout             60
  retryTimeout            0
  persistConn             1
  pcKeepAliveTimeout      1
  respBuffer              0
  autoStart               1
  path                    /usr/local/lsws/lsphp{php}/bin/lsphp
  extUser                 {externalAppMaster}
  extGroup                {externalAppMaster}
  memSoftLimit            2047M
  memHardLimit            2047M
  procSoftLimit           400
  procHardLimit           500
}

rewrite  {
  enable                  1
  autoLoadHtaccess        1
}
"""

    lswsMasterConf = """<VirtualHost *:80>

    ServerName {virtualHostName}
    ServerAlias www.{virtualHostName}
    ServerAdmin {administratorEmail}
    SuexecUserGroup {externalApp} {externalApp}
    DocumentRoot /home/{virtualHostName}/public_html
    CustomLog /home/{virtualHostName}/logs/{virtualHostName}.access_log combined
    AddHandler application/x-httpd-php{php} .php .php7 .phtml

</VirtualHost>
"""

    lswsChildConf = """<VirtualHost *:80>

    ServerName {virtualHostName}
    ServerAlias www.{virtualHostName}
    ServerAdmin {administratorEmail}
    SuexecUserGroup {externalApp} {externalApp}
    DocumentRoot {path}
    CustomLog /home/{masterDomain}/logs/{masterDomain}.access_log combined
    AddHandler application/x-httpd-php{php} .php .php7 .phtml

</VirtualHost>"""