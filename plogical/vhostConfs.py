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
  logFormat               "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\""
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
  logFormat               "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\""
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
    <IfModule LiteSpeed>
        CacheRoot lscache
    </IfModule>

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
    <IfModule LiteSpeed>
        CacheRoot lscache
    </IfModule>

</VirtualHost>"""

    apacheConf = """<VirtualHost *:8081>

        ServerName {virtualHostName}
        ServerAlias www.{virtualHostName}
        ServerAdmin {administratorEmail}
        SuexecUserGroup {externalApp} {externalApp}
        DocumentRoot /home/{virtualHostName}/public_html/
        <Proxy "unix:/var/run/php-fpm/{virtualHostName}.sock|fcgi://php-fpm-{externalApp}">
        ProxySet disablereuse=off
        </proxy>
        <FilesMatch \.php$>
                    SetHandler proxy:fcgi://php-fpm-{externalApp}
            </FilesMatch>
        #CustomLog /home/{virtualHostName}/logs/{virtualHostName}.access_log combined
        #AddHandler application/x-httpd-php{php} .php .php7 .phtml
        
        <Directory /home/{virtualHostName}/public_html/>
            Options Indexes FollowSymLinks
            AllowOverride all
            Require all granted
            DirectoryIndex index.html index.php
        </Directory>

</VirtualHost>
"""
    apacheConfSSL = """<VirtualHost *:8082>

         ServerName {virtualHostName}
         ServerAlias www.{virtualHostName}
         ServerAdmin {administratorEmail}
         SuexecUserGroup {externalApp} {externalApp}
         DocumentRoot /home/{virtualHostName}/public_html/
         <Proxy "unix:/var/run/php-fpm/{virtualHostName}.sock|fcgi://php-fpm-{externalApp}">
            ProxySet disablereuse=off
         </proxy>
         <FilesMatch \.php$>
            SetHandler proxy:fcgi://php-fpm-{externalApp}
         </FilesMatch>
         #CustomLog /home/{virtualHostName}/logs/{virtualHostName}.access_log combined
         #AddHandler application/x-httpd-php{php} .php .php7 .phtml

         <Directory /home/{virtualHostName}/public_html/>
            Options Indexes FollowSymLinks
            AllowOverride all
            Require all granted
            DirectoryIndex index.html index.php
         </Directory>

         SSLEngine on
         SSLVerifyClient none
         SSLCertificateFile /etc/httpd/conf.d/ssl/{virtualHostName}.fullchain.pem
         SSLCertificateKeyFile /etc/httpd/conf.d/ssl/{virtualHostName}.privkey.pem

</VirtualHost>
"""

    apacheConfChild = """<VirtualHost *:8081>

        ServerName {virtualHostName}
        ServerAlias www.{virtualHostName}
        ServerAdmin {administratorEmail}
        SuexecUserGroup {externalApp} {externalApp}
        DocumentRoot {path}
        <Proxy "unix:/var/run/php-fpm/{virtualHostName}.sock|fcgi://php-fpm-{externalApp}">
        ProxySet disablereuse=off
        </proxy>
        <FilesMatch \.php$>
                    SetHandler proxy:fcgi://php-fpm-{externalApp}
            </FilesMatch>
        #CustomLog /home/{virtualHostName}/logs/{virtualHostName}.access_log combined
        #AddHandler application/x-httpd-php{php} .php .php7 .phtml
        
        <Directory {path}>
            Options Indexes FollowSymLinks
            AllowOverride all
            Require all granted
            DirectoryIndex index.html index.php
        </Directory>

</VirtualHost>
"""
    apacheConfChildSSL = """<VirtualHost *:8082>

        ServerName {virtualHostName}
        ServerAlias www.{virtualHostName}
        ServerAdmin {administratorEmail}
        SuexecUserGroup {externalApp} {externalApp}
        DocumentRoot {path}
        <Proxy "unix:/var/run/php-fpm/{virtualHostName}.sock|fcgi://php-fpm-{externalApp}">
            ProxySet disablereuse=off
        </proxy>
        <FilesMatch \.php$>
                    SetHandler proxy:fcgi://php-fpm-{externalApp}
        </FilesMatch>
        #CustomLog /home/{virtualHostName}/logs/{virtualHostName}.access_log combined
        #AddHandler application/x-httpd-php{php} .php .php7 .phtml

        <Directory {path}>
            Options Indexes FollowSymLinks
            AllowOverride all
            Require all granted
            DirectoryIndex index.html index.php
        </Directory>
        SSLEngine on
        SSLVerifyClient none
        SSLCertificateFile /etc/httpd/conf.d/ssl/{virtualHostName}.fullchain.pem
        SSLCertificateKeyFile /etc/httpd/conf.d/ssl/{virtualHostName}.privkey.pem

</VirtualHost>
"""

    proxyApacheBackend = """extprocessor apachebackend {
  type                    proxy
  address                 http://127.0.0.1:8081
  maxConns                100
  pcKeepAliveTimeout      60
  initTimeout             60
  retryTimeout            0
  respBuffer              0
}
"""
    proxyApacheBackendSSL = """extprocessor proxyApacheBackendSSL {
type                    proxy
address                 https://127.0.0.1:8082
maxConns                100
pcKeepAliveTimeout      60
initTimeout             60
retryTimeout            0
respBuffer              0
}
"""

    OLSLBConf = """docRoot                   $VH_ROOT/public_html
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
  logFormat               "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\""
  logHeaders              5
  rollingSize             10M
  keepDays                10  compressArchive         1
}

rewrite  {
  enable                  1
  rules                   <<<END_rules
RewriteEngine On
RewriteCond %{HTTPS}  !=on
REWRITERULE ^(.*)$ HTTP://apachebackend/$1 [P,L]
REWRITERULE ^(.*)$ HTTP://proxyApacheBackendSSL/$1 [P,L]

  END_rules
}

"""

    phpFpmPool = """[{www}]
listen = /var/run/php-fpm/{Sock}.sock
listen.owner = nobody
listen.group = nobody
listen.mode = 0660
user = {externalApp}
group = {externalApp}
pm = dynamic
pm.max_children = 50
pm.start_servers = 1
pm.min_spare_servers = 1
pm.max_spare_servers = 1
"""
    phpFpmPoolReplace = """[{www}]
listen = /var/run/php-fpm/{Sock}.sock
listen.owner = nobody
listen.group = nobody
listen.mode = 0660
user = {externalApp}
group = {externalApp}
pm = dynamic
pm.max_children = {pmMaxChildren}
pm.start_servers = {pmStartServers}
pm.min_spare_servers = {pmMinSpareServers}
pm.max_spare_servers = {pmMaxSpareServers}
"""

    lswsRediConfMaster = """"vhost:{virtualHostName}" '{
   "username": "{externalApp}",
   "documentRoot": "/home/{virtualHostName}/public_html",
   "vh_root": "/home/{virtualHostName}",
   "uid": {uid},
   "gid": {gid},
   "phpVersion": {php},
   "custom_conf": {
    ServerAlias www.{virtualHostName}
    ServerAdmin {administratorEmail}
    CustomLog /home/{virtualHostName}/logs/{virtualHostName}.access_log combined
    <IfModule LiteSpeed>
        CacheRoot lscache
    </IfModule>
   }
}'"""

    lswsRediConfChild = """"vhost:{virtualHostName}" '{
    "username": "{externalApp}",
    "documentRoot": "{path}",
    "vh_root": "{path}",
    "uid": {uid},
    "gid": {gid},
    "phpVersion": {php},
    "custom_conf": {
    ServerAlias www.{virtualHostName}
    ServerAdmin {administratorEmail}
    CustomLog /home/{masterDomain}/logs/{masterDomain}.access_log combined
    <IfModule LiteSpeed>
        CacheRoot /home/{masterDomain}/lscache
    </IfModule>
    }
}'"""