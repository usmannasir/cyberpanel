class vhostConfs:

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