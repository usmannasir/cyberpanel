<?php 

global $_tipsdb;

$_tipsdb['CACertFile'] = new DAttrHelp("CA Certificate File", 'Specifies the file that contains all certificates of certification authorities (CAs) for chained certificates.  This file is simply the concatenation of PEM-encoded certificate  files, in order of preference. This can be used as an alternative or in addition to &quot;CA Certificate Path&quot;. Those certificates are used for client certificate authentication and constructing the server certificate chain, which will be sent to browsers in addition to the server certificate.', '', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT.', '');

$_tipsdb['CACertPath'] = new DAttrHelp("CA Certificate Path", 'Specifies the directory where the certificates of certification  authorities (CAs) are kept. Those certificates are used for client certificate authentication   and constructing the server certificate chain, which will be sent to browsers in addition to the server certificate.', '', 'path', '');

$_tipsdb['CGIPriority'] = new DAttrHelp("CGI优先级", '指定外部应用程序进程的优先级。数值范围从-20到20。数值越小，优先级越高。<br/><br/>CGI进程不能拥有比Web服务器更高的优先级。如果这个优先级数值被设置为低于 服务器的优先级数值，则将使用服务器优先级作为替代。', '', '整数', '');

$_tipsdb['CPUHardLimit'] = new DAttrHelp("CPU硬限制", '以秒为单位，指定CGI进程的CPU占用时间限制。 如果进程持续占用CPU时间，达到硬限制，则进程将被强制杀死。如果没有设置该限制，或者限制设为0， 操作系统的默认设置将被使用。', '', '无符号整数', '');

$_tipsdb['CPUSoftLimit'] = new DAttrHelp("CPU软限制", '以秒为单位，指定CGI进程的CPU占用时间限制。当进程达到 软限制时，将收到通知信号。如果没有设置该限制，或者限制设为0， 将使用操作系统的默认设置。', '', '无符号整数', '');

$_tipsdb['DHParam'] = new DAttrHelp("DH Parameter", 'Specifies the location of the Diffie-Hellman parameter file necessary for DH key exchange.', '', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT.', '');

$_tipsdb['GroupDBLocation'] = new DAttrHelp("Group DB Location", '指定组数据库的位置。<br/>组信息可以在用户数据库或在这个独立的组数据库中设置。 用于用户验证时，将首先检查用户数据库。 如果用户数据库同样包含组信息，组数据库将不被检查。<br/>对于类型为Password File的数据库， 组数据库地址应当是到达包含有组定义的平面文件的路径。 你可以在WebAmin控制台中点击文件名来修改这个设置。<br/>每一行组文件应当包含一个组名， 组名后面跟一个冒号，并在冒号后面使用空格来分割组中的用户名。 例如: <blockquote><code>testgroup: user1 user2 user3</code></blockquote><br/><br/>对于类型为LDAP的数据库， 组数据库地址应当是查询组信息的LDAP URL地址。 对于每一个有效的组， 基于同一URL地址和同一在&quot;Require（授权的用户/组）&quot;中指明的组名进行的LDAP查询请求，应当有且仅有一个记录返回。 &quot;$k&quot;中指定的组名称必须在URL的过滤部分指定并用组名称代替。在组中指定成员的属性名称需在&quot;组成员属性名&quot;中指定。<br/><br/> 例如: 如果objectClass posixGroup被用来存储组信息。可以使用以下的地址：<br/><blockquote><code>ldap: //localhost/ou=GroupDB,dc=example,dc=com???(&(objectClass=*)(cn=$k))</code></blockquote>', '[安全建议] 建议把组文件保存到站点目录外。 如果必须将组文件放置在站点目录内，只需要用&quot;.ht&quot;开头命名，如.htgroup，来防止文件被当做静态文件而输出。LiteSpeed网页服务器不会输出前缀是&quot;.ht&quot;的文件。', '文件3', '');

$_tipsdb['HANDLER_RESTART'] = new DAttrHelp("Hook::HANDLER_RESTART Priority", 'Sets the priority for this module callback within the HTTP Handler Restart Hook.<br/>   The HTTP Handler Restart Hook is triggered when the web server needs to discard the current response and start processing from beginning, for example, when an internal redirect has been requested.<br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['HTTP_AUTH'] = new DAttrHelp("Hook::HTTP_AUTH Priority", 'Sets the priority for this module callback within the HTTP Authentication Hook.<br/>  The HTTP Authentication Hook is triggered after resource mapping and before handler processing.  It occurs after HTTP built-in authentication, and can be used to perform additional authentication checking.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['HTTP_BEGIN'] = new DAttrHelp("Hook::HTTP_BEGIN Priority", 'Sets the priority for this module callback within the HTTP Begin Hook.<br/>   The HTTP Begin Hook is triggered when the TCP/IP connection begins an HTTP Session.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['HTTP_END'] = new DAttrHelp("Hook::HTTP_END Priority", 'Sets the priority for this module callback within the HTTP Session End Hook. <br/><br/>The HTTP Session End Hook is triggered when the HTTP connection has ended.     <br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['L4_BEGINSESSION'] = new DAttrHelp("Hook::L4_BEGINSESSION Priority", 'Sets the priority for this module callback within the L4 Begin Session Hook.<br/>  The L4 Begin Session Hook is triggered when the TCP/IP connection begins.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['L4_ENDSESSION'] = new DAttrHelp("Hook::L4_ENDSESSION Priority", 'Sets the priority for this module callback within the L4 End Session Hook.<br/>   The L4 End Session Hook is triggered when the TCP/IP connection ends.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['L4_RECVING'] = new DAttrHelp("Hook::L4_RECVING Priority", 'Sets the priority for this module callback within the L4 Receiving Hook.<br/>   The L4 Receiving Hook is triggered when the TCP/IP connection receives data.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['L4_SENDING'] = new DAttrHelp("Hook::L4_SENDING Priority", 'Sets the priority for this module callback within the L4 Sending Hook.<br/>  The L4 Sending Hook is triggered when the TCP/IP connection sends data.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['MAIN_ATEXIT'] = new DAttrHelp("Hook::MAIN_ATEXIT Priority", 'Sets the priority for this module callback within the Main At Exit Hook. <br/><br/>The Main At Exit Hook is triggered by the main (controller) process just prior to exiting. It is the last hook point to be called by the main process.   <br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['MAIN_INITED'] = new DAttrHelp("Hook::MAIN_INITED Priority", 'Sets the priority for this module callback within the Main Initialized Hook. <br/><br/>The Main Initialized Hook is triggered once upon startup, after the server configuration and  initialization is completed by the main (controller) process, and before any requests are serviced.   <br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['MAIN_POSTFORK'] = new DAttrHelp("Hook::MAIN_POSTFORK Priority", 'Sets the priority for this module callback within the Main Postfork Hook. <br/><br/>The Main Postfork Hook is triggered by the main (controller) process immediately after  a new worker process has been started (forked). This is called for each worker, and may happen during  system startup, or if a worker has been restarted.   <br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['MAIN_PREFORK'] = new DAttrHelp("Hook::MAIN_PREFORK Priority", 'Sets the priority for this module callback within the Main Prefork Hook. <br/><br/>The Main Prefork Hook is triggered by the main (controller) process immediately before  a new worker process is started (forked). This is called for each worker, and may happen during  system startup, or if a worker has been restarted.   <br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['RCVD_REQ_BODY'] = new DAttrHelp("Hook::RCVD_REQ_BODY Priority", 'Sets the priority for this module callback within the HTTP Received Request Body Hook.  <br/><br/>The HTTP Received Request Body Hook is triggered when the web server finishes receiving request body data.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['RCVD_RESP_BODY'] = new DAttrHelp("Hook::RCVD_RESP_BODY Priority", 'Sets the priority for this module callback within the HTTP Received Response Body Hook.  <br/><br/>The HTTP Received Response Body Hook is triggered when the web server backend finishes receiving the response body.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['RECV_REQ_BODY'] = new DAttrHelp("Hook::RECV_REQ_BODY Priority", 'Sets the priority for this module callback within the HTTP Receive Request Body Hook.  <br/><br/>The HTTP Receive Request Body Hook is triggered when the web server receives request body data.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['RECV_REQ_HEADER'] = new DAttrHelp("Hook::RECV_REQ_HEADER Priority", 'Sets the priority for this module callback within the HTTP Receive Request Header Hook.<br/>   The HTTP Receive Request Header Hook is triggered when the web server receives a request header.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['RECV_RESP_BODY'] = new DAttrHelp("Hook::RECV_RESP_BODY Priority", 'Sets the priority for this module callback within the HTTP Receive Response Body Hook.  <br/><br/>The HTTP Receive Response Body Hook is triggered when the web server backend receives the response body.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['RECV_RESP_HEADER'] = new DAttrHelp("Hook::RECV_RESP_HEADER Priority", 'Sets the priority for this module callback within the HTTP Receive Response Header Hook.  <br/><br/>The HTTP Receive Response Header Hook is triggered when the web server creates the response header.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['SEND_RESP_BODY'] = new DAttrHelp("Hook::SEND_RESP_BODY Priority", 'Sets the priority for this module callback within the HTTP Send Response Body Hook. <br/><br/>The HTTP Send Response Body Hook is triggered when the web server is going to send the response body.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['SEND_RESP_HEADER'] = new DAttrHelp("Hook::SEND_RESP_HEADER Priority", 'Sets the priority for this module callback within the HTTP Send Response Header Hook. <br/><br/>The HTTP Send Response Header Hook is triggered when the web server is ready to send the response header.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['SSLStrongDhKey'] = new DAttrHelp("SSL Strong DH Key", 'Specifies whether to use 2048 or 1024 bit DH keys for SSL handshakes. If set to &quot;Yes&quot;, 2048 bit DH keys will be used for 2048 bit SSL keys and certificates.  1024 bit DH keys will still be used in other situations. Default is &quot;Yes&quot;.<br/><br/>Earlier versions of Java do not support DH key size higher than 1024 bits. If Java client compatibility is required, this should be set to &quot;No&quot;.', '', 'radio', '');

$_tipsdb['URI_MAP'] = new DAttrHelp("Hook::URI_MAP Priority", 'Sets the priority for this module callback within the HTTP URI Map Hook.<br/>  The HTTP URI Map Hook is triggered when the web server maps a URI request to a context.  <br/><br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['WORKER_ATEXIT'] = new DAttrHelp("Hook::WORKER_ATEXIT Priority", 'Sets the priority for this module callback within the Worker At Exit Hook. <br/><br/>The Worker At Exit Hook is triggered by a worker process just prior to exiting. It is the last hook point to be called by a worker.   <br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['WORKER_POSTFORK'] = new DAttrHelp("Hook::WORKER_POSTFORK Priority", 'Sets the priority for this module callback within the Worker Postfork Hook. <br/><br/>The Worker Postfork Hook is triggered by a worker process after being created by the main (controller) process.  Note that a corresponding Main Postfork Hook may be called by the main process either before or after this callback.   <br/>It will only take effect if the module has a hook point here. If it is not set, the priority will be the default value defined in the module.', '', 'Integer value from -6000 to 6000. Lower value means higher priority.', '');

$_tipsdb['accessAllowed'] = new DAttrHelp("允许访问列表", '指定允许访问这个context下资源的IP地址或子网。综合 &quot;拒绝访问列表&quot;项的配置以及服务器/虚拟主机级别访问控制， 可访问性将以客户端IP所符合的最小范围来确定。', '', '逗号分隔的IP地址/子网列表。', '子网络可以写成192.168.1.0/255.255.255.0, 192.168.1 或192.168.1.*。');

$_tipsdb['accessControl'] = new DAttrHelp("登入限制", '指定哪些子网络和/或IP地址可以访问该服务器。 这是影响所有的虚拟主机的服务器级别设置。您还可以为每个虚拟主机设置登入限制。虚拟主机的设置不会覆盖服务器设置。<br/><br/>是否阻止/允许一个IP是由允许列表与阻止列表共同决定。 如果你想阻止某个特定IP或子网，请在&quot;允许列表&quot;中写入* 或 ALL，并在&quot;拒绝列表&quot;中写入需要阻止的IP或子网。 如果你想允许某个特定的IP或子网，请在&quot;拒绝列表&quot;中写入* 或 ALL，并在&quot;允许列表&quot;中写入需要允许的IP或子网。 单个IP地址是被允许访问还是禁止访问取决于该IP符合的最小限制范围。<br/><br/>信任的IP或子网络可以在&quot;允许列表&quot;列表中添加后缀“T”来指定。受信任的IP或子网不受连接数/流量限制。 只有服务器级别的登入限制才可以设置受信任的IP或子网。', '[安全建议] 用此项设置适用于所有虚拟主机的常规限制。', '', '');

$_tipsdb['accessControl_allow'] = new DAttrHelp("允许列表", '指定允许的IP地址或子网的列表。 可以使用{VAL}*或{VAL}ALL。', '[安全建议] 在服务器级别设置的受信任的IP或子网不受连接/节流限制。', '逗号分隔的IP地址或子网列表。 结尾加上“T”可以用来表示一个受信任的IP或子网，如{VAL}192.168.1.*T。', '子网: 192.168.1.0/255.255.255.0, 192.168.1.0/24, 192.168.1 或 192.168.1.*. <br/>IPv6 地址: ::1 或 [::1] <br/>IPv6 子网: 3ffe:302:11:2:20f:1fff:fe29:717c/64 或  [3ffe:302:11:2:20f:1fff:fe29:717c]/64.');

$_tipsdb['accessControl_deny'] = new DAttrHelp("拒绝列表", '指定不允许的IP地址或子网的列表。', '', '逗号分隔的IP地址或子网列表。 可以使用{VAL}*或{VAL}ALL。', '子网: 192.168.1.0/255.255.255.0, 192.168.1.0/24, 192.168.1 或 192.168.1.*. <br/>IPv6 地址: ::1 或 [::1] <br/>IPv6 子网: 3ffe:302:11:2:20f:1fff:fe29:717c/64 或  [3ffe:302:11:2:20f:1fff:fe29:717c]/64.');

$_tipsdb['accessDenied'] = new DAttrHelp("拒绝访问列表", '指定哪个IP地址或子网不被允许访问这个context下的资源。 综合&quot;允许访问列表&quot;项的配置以及服务器/虚拟主机级别访问控制， 可访问性将以客户端IP所符合的最小范围来确定。', '', '逗号分隔的IP地址/子网列表。', '子网络可以写成192.168.1.0/255.255.255.0, 192.168.1 或192.168.1.*。');

$_tipsdb['accessDenyDir'] = new DAttrHelp("拒绝访问的目录", '指定应该拒绝访问的目录。 将包含敏感数据的目录加入到这个列表，以防止向客户端意外泄露敏感文件。 在路径后加一个“*”，可包含所有子目录。 如果&quot;跟随符号链接&quot;和&quot;检查符号链接&quot;都被启用， 符号链接也将被检查是否在被拒绝访问目录中。', '[安全建议] 至关重要: 此设置只能防止服务这些目录中的静态文件。 这不能防止外部脚本如PHP、Ruby、CGI造成的泄露。', '逗号分隔的目录列表', '');

$_tipsdb['accessLog_bytesLog'] = new DAttrHelp("字节记录", '指定带宽字节日志文件的路径。设置后，将创建一份兼容cPanel面板的带宽日志。这将记录 一个请求传输的总字节数，包括请求内容和响应内容。', '[性能建议] 将日志文件放置在一个单独的磁盘上。', '文件2', '');

$_tipsdb['accessLog_compressArchive'] = new DAttrHelp("压缩存档", '指定是否压缩回滚日志以节省磁盘空间。', '日志文件是高度可压缩的，建议采取压缩以减少旧日志的磁盘占用量。', '布尔值', '');

$_tipsdb['accessLog_fileName'] = new DAttrHelp("文件名", '指定访问日志文件的文件名。', '[性能建议] 将访问日志文件放置在一个单独的磁盘上。', '文件2', '');

$_tipsdb['accessLog_keepDays'] = new DAttrHelp("保留天数", '指定访问日志文件将被保存在磁盘上多少天。 只有超出指定天数的回滚日志文件会被删除。 当前的日志文件不会被删除，无论它包含了多少天的数据。 如果你不想自动删除过时的、很旧的日志文件， 将该值设置为0。', '', '无符号整数', '');

$_tipsdb['accessLog_logFormat'] = new DAttrHelp("日志格式", ' 指定访问日志的格式。 设置之后，它将覆盖&quot;记录头部&quot; 的设定。', '', '字符串。日志格式的语法与Apache 2.0自定义 <a href="http://httpd.apache.org/docs/current/mod/mod_log_config.html#formats" target="_blank" rel="noopener noreferrer">日志格式</a>兼容。', '一般日志格式（CLF）<br/>	&quot;%h %l %u %t \&quot;%r\&quot; %>s %b&quot;<br/><br/>支持虚拟主机的一般日志格式<br/>	&quot;%v %h %l %u %t \&quot;%r\&quot; %>s %b&quot;<br/><br/>NCSA扩展/组合日志格式<br/>	&quot;%h %l %u %t \&quot;%r\&quot; %>s %b \&quot;%{Referer}i\&quot; \&quot;%{User-agent}i\&quot; <br/><br/>记录Foobar的cookie值<br/>   &quot;%{Foobar}C&quot;');

$_tipsdb['accessLog_logHeader'] = new DAttrHelp("记录头部", '指定是否记录HTTP请求头: Referer、 UserAgent和Host。', '[性能建议] 如果你不需要在访问日志中记录这些头部信息，关闭这个功能。', '复选框', '');

$_tipsdb['accessLog_pipedLogger'] = new DAttrHelp("Piped Logger", 'Specifies the external application that will receive the access log data sent by LiteSpeed through a pipe on its STDIN stream (file handle is 0).  When this field is specified, the access log will be sent only to the logger  application and not the access log file specified in previous entry.<br/><br/>The logger application must be defined in &quot;External Application&quot; section first.  Server-level access logging can only use an external logger application  defined at the server level. Virtual host-level access logging can only use a logger application defined at the virtual host level.<br/><br/>The logger process is spawned in the same way as other external  (CGI/FastCGI/LSAPI) processes. This means it will execute as the  user ID specified in the virtual host&#039;s &quot;外部应用程序设置UID模式&quot;  settings and will never run on behalf of a privileged user. <br/><br/>LiteSpeed web server performs simple load balancing among multiple logger  applications if more than one instance of a logger application is configured.  LiteSpeed server always attempts to keep the number of logger applications  as low as possible. Only when one logger application fails to process access  log entries in time will the server attempt to spawn another instance of  the logger application. <br/><br/>If a logger crashes, the web server will start another instance but the  log data in the stream buffer will be lost. It is possible to lose log  data if external loggers cannot keep up with the speed and volume of the log stream.', '', 'Select from drop down list', '');

$_tipsdb['aclogUseServer'] = new DAttrHelp("日志管理", '指定写入访问日志的地点。这里有三个选项： 1. 写入到服务器的访问日志； 2. 为虚拟主机创建一个访问日志； 3. 禁用访问日志记录。', '', '选项', '');

$_tipsdb['addDefaultCharset'] = new DAttrHelp("添加默认的字符集", '指定当内容类型是&quot;text/html&quot;或&quot;text/plain&quot;且没有参数时，是否添加字符集标记到&quot;Content-Type&quot;响应报头中。当设置为Off时，该功能禁用。当设置为On时，将添加&quot;自定义默认字符集&quot;中指定的字符集，如果没有指定，将添加默认的&quot;iso-8859-1&quot;字符集。', '', '布尔值', '');

$_tipsdb['addMIMEType'] = new DAttrHelp("MIME Type", 'Specifies additional MIME types and mappings for this 	   context. New mappings will override existing mappings under this 	   context and its children contexts.<br/>	   If you want to show PHP scripts as text files instead of being 	   executed as scripts, just override the .php mapping to MIME type 	   &quot;text/plain&quot;.', '', 'MIME-type1 extension extension ..., MIME-type2 extension ... 		Use comma to separate between MIME types, use space to 		separate multiple extensions.', 'image/jpg jpeg jpg, image/gif gif');

$_tipsdb['addonmodules'] = new DAttrHelp("Add-on Modules", 'Select the add-on modules you wish to use.   If you want to use a version not listed here, you can manually update the source code.  (The location of the source code is shown in a prompt at this step of the PHP build.)', '', 'Select from checkbox', '');

$_tipsdb['adminEmails'] = new DAttrHelp("管理员电子邮箱", '指定服务器管理员的电子邮箱地址。 如果设置了电子邮箱地址，管理员将收到重要事件的电子邮件通知（例如， LiteSpeed服务因崩溃而自动重启或者授权即将过期）。', '电子邮件提醒功能只在服务器拥有有效的邮件服务时才能正常工作，如postfix、exim或sendmail。', '逗号分隔的电子邮箱地址列表。', '');

$_tipsdb['adminUser'] = new DAttrHelp("网络管理员用户", '更改WebAdmin控制台的用户名和密码。 旧口令必须被输入以用来验证保存更新。', '', '', '');

$_tipsdb['allowBrowse'] = new DAttrHelp("Accessible", 'Specifies whether this context can be accessed. Set to No to deny access.  You can use this feature to protect the specified directory from being visited.  You may use it when you are updating contents for this context or you have special data in this directory.', '', 'Select from radio box', '');

$_tipsdb['allowSetUID'] = new DAttrHelp("Allow Set UID", 'Specifies whether the set UID bit is allowed for CGI scripts. If the  set UID bit is allowed and the set UID bit is enabled for a CGI script,  no matter which user the CGI script was started on behalf of, the user ID of the CGI process will switch to the user ID of the owner of the CGI script. <br/>The default is &quot;Off&quot;.', ' Do not allow Set UID CGI scripts whenever possible, as it is inherently a security risk.', 'Select from radio box', '');

$_tipsdb['allowSymbolLink'] = new DAttrHelp("跟随符号链接", '指定在这个虚拟主机内是否要跟随符号链接。 If Owner Match选项启用后，只有在链接和目标属主一致时才跟踪符号链接。 此设置将覆盖默认的服务器级设置。', '[性能和安全性建议] 为了更好的安全性，请禁用此功能。为了获得更好的性能，启用它。', '选项', '');

$_tipsdb['authName'] = new DAttrHelp("认证名称", '为当前context下的realm认证指定一个替代的名称。 如果没有指定，原realm名称将被使用。 认证名称将显示在浏览器登陆弹出窗口。', '', '文本', '');

$_tipsdb['autoFix503'] = new DAttrHelp("自动修复503错误", '指定是否尝试通过平滑重启LiteSpeed修复“503 服务不可用”错误。“503”错误通常是由 发生故障的外部应用程序引起的，Web服务器重新启动往往可以临时修复 错误。如果启用，当30秒内出现超过30次“503”错误时，服务器将自动 重新启动。此功能是默认启用的。', '', '布尔值', '');

$_tipsdb['autoIndex'] = new DAttrHelp("自动索引", '在目录中，当&quot;索引文件&quot;中所列的索引文件不可用时，指定运行时是否即时生成目录索引。<br/>此选项可以在虚拟主机级别和context级别中设置，并可以顺着目录树继承，直到被覆盖。 您可以自定义生成的索引页面。请访问在线百科了解如何操作。', '[安全建议] 建议关闭自动索引，从而尽可能防止泄露机密数据。', '布尔值', '');

$_tipsdb['autoIndexURI'] = new DAttrHelp("自动索引URI", '在目录中，当&quot;索引文件&quot;中所列出的索引文件（index）不可用时，指定用来生成索引页面的URI。 LiteSpeed Web服务器使用一个外部脚本来生成索引页面，从而为定制提供最大的灵活性。 默认的脚本生成一个类似于Apache的索引页面。 定制生成的索引页，请访问在线百科。 被索引的目录通过一个环境变量 &quot;LS_AI_PATH&quot;来传递给脚本。', '', 'URI', '');

$_tipsdb['autoStart'] = new DAttrHelp("Auto Start", 'Specifies whether you want the web server to start the application automatically. Only FastCGI and LSAPI applications running on the same machine can be started automatically. The IP in the &quot;Address&quot; must be a local IP. Starting through the LiteSpeed  CGI Daemon instead of a main server process will help reduce system overhead.', '', 'Select from drop down list', '');

$_tipsdb['backlog'] = new DAttrHelp("Back Log", 'Specifies the backlog of the listening socket.  Required if &quot;Auto Start&quot; is enabled.', '', '无符号整数', '');

$_tipsdb['banPeriod'] = new DAttrHelp("禁止期（秒）", '指定在&quot;宽限期（秒）&quot;之后，如果连接数仍然高于 &quot;连接软限制&quot;，来自该IP的新连接将被拒绝多长时间。如果IP 经常被屏蔽，我们建议您延长禁止期以更强硬地惩罚滥用。', '', '无符号整数', '');

$_tipsdb['blockBadReq'] = new DAttrHelp("封锁坏请求", '封锁持续发送坏HTTP请求的IP&quot;禁止期（秒）&quot;所设置的时长。默认为{VAL}Yes。 这有助于封锁反复发送垃圾请求的僵尸网络攻击。', '', '布尔值', '');

$_tipsdb['brStaticCompressLevel'] = new DAttrHelp("Compression Level (Static File)", 'Specifies the level of compression for static content. Ranges  from 1 (lowest) to 9 (highest). The default is 5.', '', 'Number between 1 and 9.', '');

$_tipsdb['certChain'] = new DAttrHelp("Chained Certificate", 'Specifies whether the certificate is a chained certificate or not. The file that stores a certificate chain must be in PEM format, and the certificates must be in the chained order, from the lowest level (the actual client or server certificate) to the highest level (root) CA.', '', 'Select from radio box', '');

$_tipsdb['certFile'] = new DAttrHelp("Certificate File", 'The filename of the SSL certificate file.', ' The certificate file should be placed in a secured directory,  which allows read-only access to the user that the server runs as.', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT.', '');

$_tipsdb['cgiContext'] = new DAttrHelp("CGI Context", 'A CGI context defines scripts in a particular directory as CGI scripts.  This directory can be inside or outside of the document root.  When a file under this directory is requested, the server will always  try to execute it as a CGI script, no matter if it&#039;s executable or not.  In this way, file content under a CGI Context is always protected and cannot  be read as static content. It is recommended that you put all your CGI  scripts in a directory and set up a CGI Context to access them.', '', '', '');

$_tipsdb['cgiResource'] = new DAttrHelp("CGI Settings", 'The following settings control CGI processes. Memory and process limits also serve as the default for  other external applications if limits have not been set explicitly for those applications.', '', '', '');

$_tipsdb['cgi_path'] = new DAttrHelp("Path", 'Specifies the location of CGI scripts.', '', 'The path can be a directory that contains a group of CGI scripts,  like $VH_ROOT/myapp/cgi-bin/.  In this case, the context &quot;URI&quot; must end with &quot;/&quot;, like /app1/cgi/.   The Path can also specify only one CGI script, like $VH_ROOT/myapp/myscript.pl.  This script should have the corresponding &quot;URI&quot; /myapp/myscript.pl.', '');

$_tipsdb['cgidSock'] = new DAttrHelp("CGI守护进程套接字", '用于与CGI守护进程沟通的唯一套接字地址。为了 最佳性能和安全性，LiteSpeed服务器使用一个独立的CGI 守护进程来产生CGI脚本的子进程。 默认套接字是“uds://$SERVER_ROOT/admin/conf/.cgid.sock”。 如果你需要放置在另一个位置，在这里指定一​​个Unix域套接字。', '', 'UDS://路径', '例如UDS://tmp/lshttpd/cgid.sock');

$_tipsdb['checkSymbolLink'] = new DAttrHelp("检查符号链接", '指定在启用了&quot;跟随符号链接&quot;时，是否检查符号链接在不在&quot;拒绝访问的目录&quot;中。 如果启用检查，将检查网址对应的真正的资源路径是否在配置的禁止访问目录中。 如果在禁止访问目录中，访问将被禁止。', '[性能和安全] 要获得最佳的安全性，启用该选项。要获得最佳性能，禁用该选项。', '布尔值', '');

$_tipsdb['chrootMode'] = new DAttrHelp("外部应用程序Chroot模式", '指定外部应用程序是如何设定根目录的。 为了保护机密系统数据不被易受攻击的外部应用脚本访问， 可以通过为外部应用程序设置替代的根路径来确保新根目录以外的数据不可访问。 这种方法被称为&quot;chroot监狱&quot;。<br/>三个选项可供选择: <ul><li>Same as Server: 外部应用程序将在与服务器相同的监狱目录下运行。</li>     <li>Virtual Host Root: 为虚拟主机设根目录设置为chroot监狱。外部应用程序脚本只能访问虚拟主机根路径下的文件。</li> 	<li>Customized Chroot Path: 自定义chroot路径 &quot;外部应用程序Chroot路径&quot;。 </li> </ul>', '如果使用得当，chroot环境将大大提高外部应用程序脚本安全性，但你必须确保外部程序脚本在chroot环境的限制下可以正常运作。', '选项', '');

$_tipsdb['chrootPath'] = new DAttrHelp("外部应用程序Chroot路径", '当&quot;外部应用程序Chroot模式&quot;被设置为Customized Chroot Path时，用来为当前虚拟主机外部应用程序脚本指定新的根目录。', '', '路径1', '');

$_tipsdb['ciphers'] = new DAttrHelp("Ciphers", 'Specifies the cipher suite to be used when negotiating the SSL handshake.  LSWS supports cipher suites implemented in SSL v3.0, TLS v1.0, TLS v1.2, and TLS v1.3.', ' We recommend leaving this field blank to use our default cipher which follows SSL cipher best practices.', 'Colon-separated string of cipher specifications.', 'ECDHE-RSA-AES128-SHA256:RC4:HIGH:!MD5:!aNULL:!EDH');

$_tipsdb['clientVerify'] = new DAttrHelp("Client Verification", ' Specifies the type of client certifcate authentication. Available types are: <ul> <li><b>None:</b> No client certificate is required.</li> <li><b>Optional:</b> Client certificate is optional.</li> <li><b>Require:</b> The client must has valid certificate.</li> <li><b>Optional_no_ca:</b> Same as optional.</li> </ul> The default is &quot;None&quot;.', '&quot;None&quot; or &quot;Require&quot; are recommended.', 'Select from drop down list', '');

$_tipsdb['compilerflags'] = new DAttrHelp("Compiler Flags", 'Add additional compiler flags, like optimized compiler options.', '', 'Supported flags are CFLAGS, CXXFLAGS, CPPFLAGS, LDFLAGS. Use a space to separate different flags. Use single quotes (not double quotes) for flag values.', 'CFLAGS=&#039;-O3 -msse2 -msse3 -msse4.1 -msse4.2 -msse4 -mavx&#039;');

$_tipsdb['compressibleTypes'] = new DAttrHelp("压缩类型", '指定允许哪些MIME类型进行压缩。', '[性能建议] 只允许特定类型进行GZIP压缩。 二进制文件如gif/png/jpeg图片文件及flash文件无法从压缩中获益。', '以逗号分隔的MIME类型列表。通配符“*”和 否定符号“！”是允许的，如text/*, !text/js。', 'If you want to compress text/* but not text/css, you can have a rule like  text/*, !text/css. &quot;!&quot; will exclude that MIME type.');

$_tipsdb['configFile'] = new DAttrHelp("配置文件", '指定虚拟主机的配置文件名称。 配置文件必须位于$SERVER_ROOT/conf/vhosts/目录下。 推荐使用$SERVER_ROOT/conf/vhosts/$VH_NAME/vhconf.conf。', '$SERVER_ROOT/conf/vhosts/$VH_NAME/vhconf.conf is recommended', '文件3', '');

$_tipsdb['configureparams'] = new DAttrHelp("Configure Parameters", 'Configure parameters for PHP build. Apache-specific parameters and &quot;--prefix&quot; value will be automatically  removed and &quot;--with-litespeed&quot; will be automatically appended when you click Next Step.  (Prefix can be set in the field above.) This way you can simply copy and paste the configure  parameters from the phpinfo() output of an existing working PHP build.', '', 'Space-delimited series of options (with or without double quotes)', '');

$_tipsdb['connTimeout'] = new DAttrHelp("连接超时时长", '指定在处理一个请求时所允许的最长连接闲置时间。 如果它在此期间一直闲置，例如没有I/O活动，连接将被关闭。', '[安全建议] 将值设置得尽可能低，在可能的拒绝服务攻击中，这可以帮助释放无效连接所占用的连接数。', '无符号整数', '');

$_tipsdb['consoleSessionTimeout'] = new DAttrHelp("会话超时时长（秒）", '自定义WebAdmin控制台会话超时时间。 如果未设置任何值，则默认值60秒生效。', '[安全建议] 在生产环境中一般设置一个不超过300秒的合适值。', '无符号整数', '');

$_tipsdb['crlFile'] = new DAttrHelp("Client Revocation File", ' Specifies the file containing PEM-encoded CA CRL files enumerating revoked  client certificates. This can be used as an alternative or in addition to  &quot;Client Revocation Path&quot;.', '', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT.', '');

$_tipsdb['crlPath'] = new DAttrHelp("Client Revocation Path", ' Specifies the directory containing PEM-encoded CA CRL files for revoked  client certificates. The files in this directory have to be PEM-encoded.  These files are accessed through hash filenames, hash-value.rN. Please refer to openSSL or Apache mod_ssl documentation regarding creating the hash filename.', '', 'path', '');

$_tipsdb['ctxType'] = new DAttrHelp("Context Type", 'The type of context created determines it&#039;s usage.<br><br><b>Static</b> context can be used to map a URI to a directory either outside document root or within it.<br> <b>Java Web App</b> context is used to automatically import a predefined Java Application in an AJPv13 compilant Java servlet engine.<br> <b>Servlet</b> context is used to import a specific servlet under a web application.<br> <b>Fast CGI</b> context is a mount point of Fast CGI application.<br> <b>LiteSpeed SAPI</b> context can be used to associate a URI with an LSAPI application.<br> <b>Proxy</b> context enables this virtual host to serve as a transparant reverse proxy server to an external web server or application server.<br> <b>CGI</b> context can be used to specify a directory only contains CGI scripts.<br> <b>Load Balancer</b> context can be used to assign a different cluster for that context.<br> <b>Redirect</b> context can set up an internal or external redirect URI.<br> <b>Rack/Rails</b> context is specifically used for Rack/Rails applications.<br> <b>Module handler</b> context is a mount point of hander type modules.<br>', '', '', '');

$_tipsdb['defaultCharsetCustomized'] = new DAttrHelp("自定义默认字符集", '指定一个字符集当&quot;添加默认的字符集&quot;是On时使用。这是可选的。默认值是iso-8859-1。当&quot;添加默认的字符集&quot;是Off时本设置将不生效。', '', '字符集的名称，例如utf-8', 'utf-8');

$_tipsdb['defaultType'] = new DAttrHelp("Default MIME Type", 'When specified, this type will be used when MIME type mapping 	   cannot be determined by the suffix of a document or if there is no suffix. 	   If not specified, the default value  	   application/octet-stream will be used.', '', 'MIME-type', '');

$_tipsdb['destinationuri'] = new DAttrHelp("目标URI", '指定重定向的目标位置。 如果被重定向的URI映射到另一个重定向URI时，将再次被重定向。', '', '这个URI可以是一个在同一个网站上以&quot;/&quot;开始的相对URI， 或者是一个指向其他网站以&quot;http(s): //&quot;开始的绝对URI。 如果&quot;URI&quot;包含正则表达式，目标地址可以匹配变量，如$1或$2。', '');

$_tipsdb['disableInitLogRotation'] = new DAttrHelp("Disable Initial Log Rotation", 'Specifies whether to enable/disable rotation of server error log file at startup. Initial log rotation is enabled by default when using value &quot;Not Set&quot;.', '', 'Select from radio box', '');

$_tipsdb['docRoot'] = new DAttrHelp("文档根", '指定此虚拟主机的文档根目录。 推荐使用$VH_ROOT/html。在context中，此目录可以用$DOC_ROOT来引用。', '', '路径3', '');

$_tipsdb['domainName'] = new DAttrHelp("Domains", 'Specifies the mapping domain names. Domain names are case  insensitive and the leading &quot;www.&quot; will be removed. The wildcard  characters &quot;*&quot; and &quot;?&quot; are allowed. &quot;?&quot; only represents one character.  &quot;*&quot; represents any numbers of characters.  Duplicated domain names are not allowed.', ' If a listener is dedicated to one virtual host,  always use * for the domain name to avoid unnecessary checking. Domain names with wildcard characters  (other than the catchall domain)  should be avoided whenever possible.', 'Comma-separated list.', 'www?.example.com<br/>&quot;*.mydomain.com&quot; will match all subdomains of mydomain.com.<br/>&quot;*&quot; by itself is the catchall domain and will match any unmatched domain names.');

$_tipsdb['dynReqPerSec'] = new DAttrHelp("Dynamic Requests/Second", 'Specifies the maximum number of requests to dynamically generated content  coming from a single IP address that can be processed in each second regardless of the number of connections established.  When this limit is reached, all future requests to dynamic content  are tar-pitted until the next second. <br/><br/>The request limit for static content is independent of this limit. This per client request limit can be set at server or virtual host level.  Virtual host-level settings override server-level settings.', ' Trusted IPs or sub-networks are not restrained by this limit.', '无符号整数', '');

$_tipsdb['enableBrCompress'] = new DAttrHelp("Enable Brotli Compression", 'Controls Brotli compression for static HTTP responses. The default value is enabled.', ' Enable it to save network bandwidth. Text-based responses such as  html, css, and javascript files benefit the most and on average can be compressed to half  of their original size.', 'Select from radio box', '');

$_tipsdb['enableCoreDump'] = new DAttrHelp("启用Core Dump", '指定当服务由root用户启动时是否启用core dump。 对大多数现代的Unix系统，会更改用户ID或组ID的进程出于安全考虑不被允许产生core文件。但是core dump文件对于排查故障非常有用。 这个选项只能在Linux Kernel 2.4或更高版本中可用。 Solaris用户应当使用coreadm命令来控制这个功能。', '[安全建议] 仅在当你在服务器日志中看到没有创建core文件时启用。当产生core文件后立即关闭。Core文件产生后请提交bug报告。', '布尔值', '');

$_tipsdb['enableDHE'] = new DAttrHelp("Enable DH Key Exchange", 'Allows use of Diffie-Hellman key exchange for further SSL encryption.', ' DH key exchange is more secure than using just an RSA key. ECDH and DH key exchange are equally secure.<br/><br/> Enabling DH key exchange will increase CPU load and is slower than ECDH key exchange and RSA. ECDH key exchange is preferred when available.', 'Select from radio box', '');

$_tipsdb['enableDynGzipCompress'] = new DAttrHelp("启用动态压缩", '控制动态HTTP回应的GZIP压缩。 &quot;启用压缩&quot;必须设置为Yes来开启动态GZIP压缩。', '[性能建议] 压缩动态回应将增加CPU和内存的使用，但可以节省网络带宽。', '布尔值', '');

$_tipsdb['enableECDHE'] = new DAttrHelp("Enable ECDH Key Exchange", 'Allows use of Elliptic Curve Diffie-Hellman key exchange for further SSL encryption.', ' ECDH key exchange is more secure than using just an RSA key. ECDH and DH key exchange are equally secure.<br/><br/> Enabling ECDH key exchange will increase CPU load and is slower than using just an RSA key.', 'Select from radio box', '');

$_tipsdb['enableExpires'] = new DAttrHelp("启用过期", '指定是否为静态文件生成Expires头。如果启用，将根据 &quot;默认过期&quot;和&quot;按类型过期&quot;生成Expires头。<br/><br/>这可以在服务器，虚拟主机和Context级别设置。低级别的设置将 覆盖高级别的设置。例如，Context级别的设置将覆盖虚拟主机级别的设置， 虚拟主机级别的设置将覆盖服务器级别的设置。', '', '布尔值', '');

$_tipsdb['enableGzipCompress'] = new DAttrHelp("启用压缩", '控制静态或动态HTTP回应的GZIP压缩。', '[性能建议] 开启该功能可以节省网络带宽。 针对基于文本的回应如html、css和javascript文件最有效果，一般可以压缩到原文件大小的一半大小。', '布尔值', '');

$_tipsdb['enableIpGeo'] = new DAttrHelp("启用IP地理定位", '指定是否启用IP地理定位查找。 可以在服务器级别，虚拟主机级别，或context级别设置。', '', '布尔值', '');

$_tipsdb['enableRewrite'] = new DAttrHelp("Enable Rewrite", 'Specifies whether to enable LiteSpeed&#039;s URL rewrite engine. This option can be customized at the virtual host or context level, and is inherited along the directory tree until it is explicitly overridden.', '', 'Select from radio box', '');

$_tipsdb['enableScript'] = new DAttrHelp("启用脚本", '指定在这个虚拟主机中是否允许运行脚本（非静态页面）。 如果禁用，CGI, FastCGI, LSAPI, Servlet引擎 和其他脚本语言都将在这个虚拟机中不被允许使用。 因此如果你希望使用一个脚本处理程序，你需要启用本项。', '', '布尔值', '');

$_tipsdb['enableSpdy'] = new DAttrHelp("Enable SPDY/HTTP2", 'HTTP/2 and SPDY are new versions of the HTTP network protocol with the goal of reducing page load times.  More information can be found at <a href=&quot;http://en.wikipedia.org/wiki/HTTP/2&quot;>http://en.wikipedia.org/wiki/HTTP/2</a>.', 'This setting can be set at the listener and virtual host levels.', 'Check the protocol(s) you wish to enable. Leaving all boxes unchecked will enable SPDY and HTTP/2 support (the default).  If you wish to disable SPDY and HTTP/2, check &quot;None&quot; only and leave all other boxes unchecked.', '');

$_tipsdb['enableStapling'] = new DAttrHelp("Enable OCSP Stapling", 'Determines whether to enable OCSP stapling, a more efficient way of verifying public key certificates.', '', 'Select from radio box', '');

$_tipsdb['enableh2c'] = new DAttrHelp("Enable HTTP/2 Over Cleartext TCP", 'Specifies whether to enable HTTP/2 over non-encrypted TCP connections. Default is disabled.', '', 'Select from radio box', '');

$_tipsdb['env'] = new DAttrHelp("Environment", 'Specifies extra environment variables for the external application.', '', 'Key=value. Multiple variables can be separated by &quot;ENTER&quot;', '');

$_tipsdb['errCode'] = new DAttrHelp("错误代码", '指定错误页面的HTTP状态码。 只有特定的HTTP状态码才可以自定义错误页面。', '', '选项', '');

$_tipsdb['errPage'] = new DAttrHelp("Customized Error Pages", 'Whenever the server has a problem processing a request,  the server will return an error code and an html page as an error message  to the web client. Error codes are defined in the HTTP protocol (see RFC 2616).  LiteSpeed web server has a built-in default error page for each error code, but  a customized page can be configured for each error code as well.   These error pages can be even further customized to be unique for each virtual host.', '', '', '');

$_tipsdb['errURL'] = new DAttrHelp("URL", '指定自定义错误页的URL。 当返回相应HTTP状态时服务器会将请求转发到该URL。 如果此URL指向一个不存在的地址，自带的错误页面将被使用。 该URL可以是一个静态文件，动态生成的页面，或者其他网站的页面 （网址开头为&quot;http(s): //&quot;）。 当转发到在其他网站上的页面时，客户端会收到一个重定向状态码 来替代原本的状态码。', '', 'URL', '');

$_tipsdb['eventDispatcher'] = new DAttrHelp("I/O事件调度", '指定要使用的I/O事件调度器。不同操作系统支持不同类型的事件调度器:  <ul>   <li>Linux 内核 2.4.x 支持:      <ul><li>poll</li></ul>   </li>   <li>Linux 内核 2.6.x 支持:      <ul><li>poll</li><li>epoll</li></ul>   </li>   <li>FreeBSD 支持:      <ul><li>poll</li><li>kqueue</li></ul>   </li>   <li>Solaris 支持:      <ul><li>poll</li><li>devpoll</li></ul>   </li>   <li>Mac OS X 10.3 及以上支持:      <ul><li>poll</li><li>kqueue</li></ul>   </li> </ul>   poll被所有的平台支持，并且是默认的选择。   对于高流量的网站，可以使用其他事件调度器来提高可扩展性。', '', '选项', '');

$_tipsdb['expWSAddress'] = new DAttrHelp("Address", 'HTTP or HTTPS address used by the external web server.', ' If you proxy to another web server running on the same machine,   set the IP address to localhost or 127.0.0.1,  so the external application is inaccessible from other machines.', 'IPv4 or IPV6 address(:port). Add &quot;https://&quot; in front if the external web server uses https. Port is optional if the external web server uses the standard ports 80 or 443.', '192.168.0.10 <br/>127.0.0.1:5434<br/>https://10.0.8.9<br/>https://127.0.0.1:5438');

$_tipsdb['expiresByType'] = new DAttrHelp("按类型过期", '为各个MIME类型分别指定Expires头设置。', '', '逗号分隔的“MIME-类型=A|M秒数”的列表。 文件将在基准时间（A|M）加指定秒数的时间后失效。<br/><br/>“A”代表基准时间为客户端的访问时间，“M”代表文件的最后修改时间。 MIME-类型可使用通配符“*”，如image/*。', '');

$_tipsdb['expiresDefault'] = new DAttrHelp("默认过期", '指定生成Expires头的默认设置。该设置在&quot;启用过期&quot; 设为“启用”时有效。它可以被&quot;按类型过期&quot;覆盖。 除非必要，否则不要在服务器或虚拟主机级别设置该默认值。 因为它会为所有网页生成Expires头。大多数时候，应该是 为不常变动的某些目录在Context级别设置。如果没有默认设置，&quot;按类型过期&quot;中未指定的类型不会生成Expires头。', '', 'A|M秒数<br/>文件将在基准时间（A|M）加指定秒数的时间后失效。 “A”代表基准时间为客户端的访问时间，“M”代表文件的最后修改时间。', '');

$_tipsdb['expuri'] = new DAttrHelp("URI", 'Specifies the URI for this context.', '', 'The URI can be a plain URI (starting with &quot;/&quot;) or  a Perl compatible regular expression URI (starting with &quot;exp:&quot;). If a plain URI ends  with a &quot;/&quot;, then this context will include all sub-URIs under this URI. If the context maps to a directory on the file system, a trailing &quot;/&quot; must be added.', '');

$_tipsdb['extAppAddress'] = new DAttrHelp("Address", 'A unique socket address used by the external application.  IPv4/IPv6 sockets and Unix Domain Sockets (UDS) are supported.  IPv4/IPv6 sockets can be used for communication over the network.   UDS can only be used when the external application resides on the same machine as the server.', ' If the external application runs on the same machine,  UDS is preferred. If you have to use an IPv4|IPV6 socket,  set the IP address to localhost or 127.0.0.1,  so the external application is inaccessible from other machines. <br/> Unix Domain Sockets generally provide higher performance than IPv4 sockets.', 'IPv4 or IPV6 address:port or UDS://path', '127.0.0.1:5434<br/>UDS://tmp/lshttpd/php.sock.');

$_tipsdb['extAppName'] = new DAttrHelp("Name", 'A unique name for this external application.  You will refer to it by this name when you use it in other parts of the configuration.', '', '', '');

$_tipsdb['extAppPath'] = new DAttrHelp("Command", 'Specifies the full command line including parameters to execute the external application. Required value if  &quot;Auto Start&quot; is enabled. A parameter should be quoted with a double or single quote if the parameter contains space or tab characters.', '', 'Full path to the executable with optional parameters.', '');

$_tipsdb['extAppPriority'] = new DAttrHelp("Priority", 'Specifies priority of the external application process. Value ranges from -20 to 20. A lower number means a higher priority.  An external application process cannot have a higher priority than the web server. If this priority is set to a lower number than the server&#039;s, the server&#039;s priority will be used for this value.', '', 'int', '');

$_tipsdb['extAppType'] = new DAttrHelp("Type", 'Specifies the type of external application. Application types  are differentiated by the service they provide or the protocol they  use to communicate with the server. Choose from <ul> <li>FastCGI: a FastCGI application with a Responder role.</li> <li>FastCGI Authorizer: a FastCGI application with an Authorizer role</li> <li>Servlet Engine: a servlet engine with an AJPv13 connector, such as Tomcat.</li> <li>Web Server: a web server or application server that supports HTTP protocol.</li> <li>LiteSpeed SAPI App: an application that communicates with the web server using LSAPI protocol.</li> <li>Load Balancer: a virtual application that can balance load among worker applications.</li> <li>Piped Logger: an application that can process access log entries received on its STDIN stream.</li> </ul>', 'Most applications will use either LSAPI or FastCGI protocol.  LSAPI supports PHP, Ruby, and Python. Perl can be used with FastCGI.  (PHP, Ruby, and Python can also be set up to run using FastCGI, but  they run faster using LSAPI.) Java uses servlet engines.', 'Select from drop down list', '');

$_tipsdb['extAuthorizer'] = new DAttrHelp("Authorizer", 'Specifies an external application that can be used to generate authorized/unauthorized decisions. Currently, only the FastCGI Authorizer is available. For more details about the FastCGI Authorizer role,  please visit <a href="http://www.fastcgi.com" target="_blank" rel="noopener noreferrer">http://www.fastcgi.com</a>.', '', 'Select from drop down list', '');

$_tipsdb['extGroup'] = new DAttrHelp("suEXEC Group", 'Specifies group name that the external application will run as.', '', 'Valid group name.', '');

$_tipsdb['extMaxIdleTime'] = new DAttrHelp("Max Idle Time", 'Specifies the maximum idle time before an external application is stopped by the server. When set to &quot;-1&quot;, the external application will not be stopped by the server. The default value is &quot;-1&quot;. This feature allows resources used by idle applications to be freed. It is especially useful in the mass hosting environment when you need to define many applications running in &quot;setuid&quot; mode for the sake of maximum security.', ' This feature is especially useful in the mass hosting environment.  In order to prevent files owned by one virtual host from being accessed by the  external application scripts of another virtual host, mass hosting often requires  many different applications running at the same time in SetUID mode. Set this Max  Idle Time low to prevent these external applications from idling unnecessarily.', 'Select from radio box', '');

$_tipsdb['extUmask'] = new DAttrHelp("umask", 'Sets default umask for this external application&#039;s processes.   See  man 2 umask  for details. The default value taken from the server-level   &quot;umask&quot; setting.', '', 'value valid range [000]-[777].', '');

$_tipsdb['extUser'] = new DAttrHelp("suEXEC User", 'Specifies username that the external application will run as. If not set, the external application will run as the user of the web server.', '', 'Valid username.', '');

$_tipsdb['extWorkers'] = new DAttrHelp("Workers", 'List of worker groups previously defined in the external load balancer.', '', 'A comma-separated list in the form ExternalAppType::ExternalAppName', 'fcgi::localPHP, proxy::backend1');

$_tipsdb['externalredirect'] = new DAttrHelp("外部重定向", '指定重定向是否为外部重定向。 对于外部重定向，可以指定&quot;状态码&quot;以及 &quot;目标URI&quot;可以以&quot;/&quot;或&quot;http(s): //&quot;开头。 对于内部重定向，&quot;目标URI&quot;必须以&quot;/&quot;开头。', '', '', '');

$_tipsdb['extraHeaders'] = new DAttrHelp("Extra Headers", 'Specifies extra response headers to be added. Multiple headers can be added, one header per line. Put &quot;NONE&quot; to disable headers inherited from parent content.', '', '&quot;[HeaderName]: [HeaderValue]&quot; in each line.', 'Cache-control: no-cache, no-store <br/>My-header: Custom header value');

$_tipsdb['extrapathenv'] = new DAttrHelp("Extra PATH Environment Variables", 'Additional PATH values that will be appended to the current PATH environment variables for build scripts.', '', 'path values separated by &quot;:&quot;', '');

$_tipsdb['fcgiContext'] = new DAttrHelp("FastCGI Context", 'FastCGI applications cannot be used directly. A FastCGI application must be either configured as  a script handler or mapped to a URL through FastCGI context. A FastCGI context will  associate a URI with a FastCGI application.', '', '', '');

$_tipsdb['fcgiapp'] = new DAttrHelp("FastCGI App", 'Specifies the name of the FastCGI application.  This application must be defined in the &quot;External Application&quot; section at the server or virtual host level.', '', 'Select from drop down list', '');

$_tipsdb['fileETag'] = new DAttrHelp("文件ETag", '指定是否使用一个文件的索引节点、最后修改时间和大小属性 生成静态文件的ETag HTTP响应头。 所有这三个属性是默认启用的。 如果您打算使用镜像服务器服务相同的文件，您应该不勾选索引节点。 否则，为同一个文件生成的ETag在不同的服务器上是不同的。', '', '复选框', '');

$_tipsdb['fileUpload'] = new DAttrHelp("File Upload", 'Provides additional security functionality when uploading files by using a Request Body  Parser to parse files to a server local directory where they can be easily scanned for malicious  intent by third party modules. Request Body Parser is used when &quot;Pass Upload Data by File Path&quot; is  enabled or a module calls LSIAPI’s set_parse_req_body in the LSI_HKPT_HTTP_BEGIN level.  API examples provided in source package.', '', '', '');

$_tipsdb['followSymbolLink'] = new DAttrHelp("跟随符号链接", '指定服务静态文件时跟踪符号链接的服务器级别默认设置。<br/><br/>选项有Yes、If Owner Match和No。<br/><br/>Yes设置服务器始终跟踪符号链接。 If Owner Match设置服务器只有在链接和目标属主一致时才跟踪符号链接。 No表示服务器永远不会跟踪符号链接。 该设置可以在虚拟主机配置中覆盖，但不能通过.htaccess文件覆盖。', '[性能和安全建议] 要获得最佳安全性，选择{VAL}No或If Owner Match。 要获得最佳性能，选择{VAL}Yes。', '选项', '');

$_tipsdb['forceGID'] = new DAttrHelp("强制GID", '指定一组ID，以用于所有在suEXEC模式下启动的外部应用程序。 当设置为非零值时，所有suEXEC的外部应用程序（CGI、FastCGI、 LSAPI）都将使用该组ID。这可以用来防止外部应用程序访问其他用 户拥有的文件。<br/><br/>例如，在共享主机环境，LiteSpeed以“www-data”用户、“www-data”组 身份运行。每个文件根目录是由用户帐户所有，属组为“www-data”，权限 为0750。如果强制GID被设置为“nogroup”（或“www-data”之外的任何一 个组），所有suEXEC外部应用程序都将以特定用户身份运行，但属组为 “nogroup”。这些外部应用程序的进程依然能够访问属于相应用户的文件（ 因为他们的用户ID），但没有组权限访问其他人的文件。另一方面，服务器 仍然可以服务在任何用户文件根目录下的文件（因为它的组ID）。', '[安全建议] 设置足够高的值以排除所有系统用户所在的组。', '无符号整数', '');

$_tipsdb['forceStrictOwnership'] = new DAttrHelp("强制严格属主检查", '指定是否执行严格的文件所有权检查。 如果启用，Web服务器将检查正在服务的文件的所有者与虚拟主机的所有者是否相同。 如果不同，将返回403拒绝访问错误。 该功能默认是关闭的。', '[安全建议] 对于共享主机，启用此检查以得到更好的安全性。', '布尔值', '');

$_tipsdb['forceType'] = new DAttrHelp("Force MIME Type", 'When specified, all files under this context will be served as 	   static files with the MIME type specified regardless of file suffix.  	   When set to NONE, inherited force type setting will be 	   disabled.', '', 'MIME type or NONE.', '');

$_tipsdb['generalContext'] = new DAttrHelp("Static Context", 'Context settings are used to specify special settings for files in a  certain location. These settings can be used to bring in files outside of  the document root (like Apache&#039;s Alias or AliasMatch directives),  to protect a particular directory using authorization realms, or to  block or restrict access to a particular directory within the document root.', '', '', '');

$_tipsdb['geoipDBCache'] = new DAttrHelp("数据库缓存类型", ' 指定应该使用什么样的缓存模式。缓存模式包括:  标准缓存、内存缓存、检查缓存和索引缓存。内存缓存是推荐的模式，也是默认模式。', '', '选项', '');

$_tipsdb['geoipDBFile'] = new DAttrHelp("数据库文件路径", ' 指定MaxMind GeoIP数据库路径。', '', '文件路径', '');

$_tipsdb['geolocationDB'] = new DAttrHelp("IP地理定位数据库", '多个MaxMind地理定位数据库可以在这里指定。MaxMind有以下数据库类型: 国家，地区，城市，组织，ISP和NETSPEED。如果混合配置“国家”，“地区”，和“城市”类型数据库，则最后一项将会生效。', '', '', '');

$_tipsdb['gracePeriod'] = new DAttrHelp("宽限期（秒）", '指定来自一个IP的连接数超过&quot;连接软限制&quot;之后， 多长时间之内可以继续接受新连接。在此期间，如果总连接数仍然 低于&quot;连接硬限制&quot;，将继续接受新连接。之后，如果连接数 仍然高于&quot;连接软限制&quot;，相应的IP将被封锁&quot;禁止期（秒）&quot;里设置的时长。', '[性能与安全建议] 设置为足够大的数量，以便下载完整网页， 但也要足够低以防范蓄意攻击。', '无符号整数', '');

$_tipsdb['gracefulRestartTimeout'] = new DAttrHelp("平滑重启超时时长", '平滑重启时，即使新的服务器实例已经启动，旧的实例仍将继续 处理现有的请求。此项超时设置定义了旧实例等待多长时间后中止。 默认值是300秒。 -1表示永远等待。 0表示不等待，立即中止。', '', '整数', '');

$_tipsdb['groupDBCacheTimeout'] = new DAttrHelp("Group DB Cache Timeout (secs)", '指定多长时间后台组数据库将检查一次变更。 查看更多详细信息查看&quot;用户数据库缓存超时&quot;。', '', '无符号整数', '');

$_tipsdb['groupDBMaxCacheSize'] = new DAttrHelp("组数据库最大缓存大小", '指定组数据库的最大缓存大小。', '[性能建议] 由于更大的缓存会消耗更多的内存， 更高的值可能会也可能不会提供更好的性能。 请根据你的用户数据库大小和网站使用情况来设置合适的大小。', '无符号整数', '');

$_tipsdb['gzipAutoUpdateStatic'] = new DAttrHelp("自动更新静态文件", '指定是否由LiteSpeed自动创建/更新可压缩静态文件的GZIP压缩版本。 如果设置为Yes，当请求文件MIME属于&quot;压缩类型&quot;时， LiteSpeed会根据压缩的文件时间戳来创建/更新文件的压缩版本。 压缩的文档会创建在&quot;静态GZIP缓存目录&quot;目录下。 文件名称根据原文件的MD5散列创建。', '', '布尔值', '');

$_tipsdb['gzipCacheDir'] = new DAttrHelp("静态GZIP缓存目录", '指定目录路径来存储静态内容的压缩文件。默认是&quot;交换目录&quot;。', '', '目录路径', '');

$_tipsdb['gzipCompressLevel'] = new DAttrHelp("压缩级别（动态内容）", '指定压动态态内容的级别。 范围从1 (最低)到9 (最高)。默认值是2。', '[性能建议] 更高的压缩级别将消耗更多的内存和CPU资源。 如果您的机器有额外的资源您可以设置更高的级别。 级别9与级别6没有太大的区别，但是级别9会占用多得多的CPU资源。', '1到9之间的数。', '');

$_tipsdb['gzipMaxFileSize'] = new DAttrHelp("静态文件最大尺寸", '指定LiteSpeed可以自动创建压缩文件的静态文件最大尺寸。', '[性能建议] 不建议使用LiteSpeed创建/更新较大文件的压缩文件。 压缩操作会占用整个服务器进程并且在压缩结束前新请求都无法被处理。', '不小于1K的字节数。', '');

$_tipsdb['gzipMinFileSize'] = new DAttrHelp("静态文件最小尺寸", '指定LiteSpeed创建相应压缩文件的静态文件最小尺寸。', '因为流量节省可以忽略不计，所以压缩非常小的文件是没有必要的。', '不小于200的字节数。', '');

$_tipsdb['gzipStaticCompressLevel'] = new DAttrHelp("压缩级别（静态内容）", '指定压缩静态内容的级别。 范围从1 (最低)到9 (最高)。默认值是6。', '', '1到9之间的数。', '');

$_tipsdb['hardLimit'] = new DAttrHelp("连接硬限制", '指定来自单个IP的并发连接的硬限制。 此限制是永远执行的，客户端将永远无法超过这个限制。 HTTP/1.0客户端通常会尝试建立尽可能多的连接，因为它们需要同时下载嵌入的内容。此限制应设置得足够高，以使HTTP/1.0客户端仍然可以访问相应的网站。 使用&quot;连接软限制&quot;设置期望的连接限制。<br/><br/>建议根据你的网页内容和流量负载，限制在20与50之间。', '[安全] 一个较低的数字将使得服务器可以服务更多独立的客户。<br/>[安全] 受信任的IP或子网不受影响。<br/>[性能] 使用大量并发客户端进行基准测试时，设置一个较高的值。', '无符号整数', '');

$_tipsdb['httpdWorkers'] = new DAttrHelp("Number of Workers", 'Specifies the number of httpd workers.', ' Set an appropriate number to suit your needs. Adding more workers may not necessarily mean better performance.', 'Integer value between 1 and 16.', '');

$_tipsdb['inBandwidth'] = new DAttrHelp("入口带宽", '指定对单个IP地址允许的最大传入吞吐量（无论与该IP之间建立了多少个连接）。 为提高效率，真正的带宽可能最终会略高于设定值。 带宽是按1KB单位分配。设定值为0可禁用限制。 每个客户端的带宽限制（字节/秒）可以在服务器或虚拟主机级别设置。 虚拟主机级别的设置将覆盖服务器级别的设置。', '[安全] 受信任的IP或子网不受影响。', '无符号整数', '');

$_tipsdb['inMemBufSize'] = new DAttrHelp("最大的读写缓冲区大小", '指定用于存储请求内容和相应的动态响应的最大缓冲区大小。达到此限制时， 服务器将在&quot;交换目录&quot;中创建临时交换文件。', '[性能] 设置足够大的缓冲区，以容纳所有并发 请求/响应，避免内存和磁盘数据交换。如果交换目录（默认为/tmp/lshttpd/swap/）存在频繁的读写活动，说明缓冲区太小，LiteSpeed正在使用交换文件。', '无符号整数', '');

$_tipsdb['indexFiles'] = new DAttrHelp("索引文件", '指定URL映射到目录时顺序查找的索引文件名称。 您可以在服务器、虚拟主机和Context级别对其进行自定义。', '[性能建议] 只设置你需要的索引文件。', '逗号分隔的索引文件名列表。', '');

$_tipsdb['indexUseServer'] = new DAttrHelp("使用服务器索引文件", '指定是否使用服务器的索引文件。 如果设置为Yes，那么只有服务器的设置将被使用。 如果设置为No，那么服务器的设置将不会被使用。 如果设置为Addition，那么附加的索引文件可以被添加到此虚拟主机服务器的索引文件列表中。 如果想要禁用此虚拟主机的索引文件，您可以将该值设置为No，并将索引文件栏留空。', '', '选项', '');

$_tipsdb['initTimeout'] = new DAttrHelp("Initial Request Timeout (secs)", 'Specifies the maximum time in seconds the server will wait for the external  application to respond to the first request over a new established connection.  If the server does not receive any data from the external application within this timeout limit, it will mark this connection as bad. This helps to identify communication problems with external applications as quickly as possible. If some requests take longer to  process, increase this limit to avoid 503 error messages.', '', '无符号整数', '');

$_tipsdb['installpathprefix'] = new DAttrHelp("Installation Path Prefix", 'Sets the value for the &quot;--prefix&quot; configure option. The default installation location is under LiteSpeed Web Server&#039;s install directory.', 'LiteSpeed Web Server can use multiple PHP versions at the same time. If you are installing multiple versions, you should give them different prefixes.', 'path', '/usr/local/lsws/lsphp5');

$_tipsdb['instances'] = new DAttrHelp("Instances", 'Specifies the maximum instances of the external application the server will create. It is required if &quot;Auto Start&quot; is enabled. Most FastCGI/LSAPI applications can only process one request per process instance and for those types of applications, instances should be set to match the value of &quot;Max Connections&quot;. Some FastCGI/LSAPI applications can  spawn multiple child processes to handle multiple requests concurrently.  For these types of applications, instances should be set to &quot;1&quot; and   environment variables used to control how many child processes the application can spawn.', '', '无符号整数', '');

$_tipsdb['internalmodule'] = new DAttrHelp("Is Internal", 'Specify whether the module is an internal module, which is staticaly linked, instead of being an external .so library.', '', 'Select from radio box', '');

$_tipsdb['ip2locDBCache'] = new DAttrHelp("DB Cache Type", 'The caching method used. The default value is Memory.', '', 'Select from drop down list', '');

$_tipsdb['ip2locDBFile'] = new DAttrHelp("IP2Location DB File Path", 'The location of a valid database file.', '', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT.', '');

$_tipsdb['javaServletEngine'] = new DAttrHelp("Servlet Engine", 'Specifies the name of the servlet engine that serves this web application. Servlet engines must be defined in the &quot;External Application&quot; section at the server or virtual host level.', '', 'Select from drop down list', '');

$_tipsdb['javaWebAppContext'] = new DAttrHelp("Java Web App Context", 'Many people running Java applications use the servlet engine to serve static  content as well. But no servlet engine is nearly as efficient as LiteSpeed Web Server  for these processes. In order to improve the overall performance,  LiteSpeed Web Server can be configured as a gateway server, which serves static content  and forwards dynamic Java page requests to the servlet engine. <br/><br/>LiteSpeed Web Server requires certain contexts to be defined in order to run a  Java application. A Java Web App Context automatically creates all required  contexts based on the Java web application&#039;s configuration file (WEB-INF/web.xml). <br/><br/>There are a few points you need to keep in mind when setting up a Java Web App Context:<br/><ul> <li>A Servlet Engine external application must be set up in &quot;External Application&quot;  before Java Web App Context can be set up.</li>  <li>A &quot;Script Handler&quot; for .jsp files should be defined as well.</li> <li>If the web application is packed into a .war file, the .war file must be expanded.  The server cannot access compressed archive files.</li> <li>For the same resources, the same URL should be used no matter whether it is accessed  through LiteSpeed Web Server or through the servlet engine&#039;s built-in HTTP server.<br/>For example,    Tomcat 4.1 is installed under /opt/tomcat. Files for the &quot;examples&quot; web application are    located at /opt/tomcat/webapps/examples/. Through Tomcat&#039;s built-in HTTP server,    the &quot;examples&quot; web application is thus accessed with a URI like &quot;/examples/***&quot;.    The corresponding Java Web App Context should thus be configured:    &quot;URI&quot; = /examples/, &quot;Location&quot; = /opt/tomcat/webapps/examples/.</li>   </ul>', '', '', '');

$_tipsdb['javaWebApp_location'] = new DAttrHelp("Location", 'Specifies the directory that contains the files for this web application.  This is the directory containing &quot;WEB-INF/web.xml&quot;.', '', 'path', '');

$_tipsdb['keepAliveTimeout'] = new DAttrHelp("持续连接超时时长", '指定持续连接请求的最长闲置时间。 如果在这段时间内没有接收到新的请求，该连接将被关闭。', '[安全和性能建议] 我们建议您将值设置得刚好足够处理单个页面 视图的所有请求。没有必要延长持续连接时间。较小的值可以减少闲置 连接，提高能力，以服务更多的用户，并防范拒绝服务攻击。2-5秒 对大多数应用是合理范围。Litespeed在非持续连接环境是非常高效的。', '无符号整数', '');

$_tipsdb['keyFile'] = new DAttrHelp("Private Key File", 'The filename of the SSL private key file. The key file should not be encrypted.', ' The private key file should be placed in a secured directory that  allows read-only access to the user the server runs as.', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT.', '');

$_tipsdb['lbContext'] = new DAttrHelp("Load Balancer Context", 'Like other external applications, load balancer worker applications  cannot be used directly. They must be mapped to a URL through a context.  A Load Balancer Context will associate a URI to be load balanced by the load balancer workers.', '', '', '');

$_tipsdb['lbapp'] = new DAttrHelp("Load Balancer", 'Specifies the name of the load balancer to be associated to this context. This load balancer is a virtual application, and must be defined in the &quot;External Application&quot; section at the server or virtual host level.', '', 'Select from drop down list', '');

$_tipsdb['listenerBinding'] = new DAttrHelp("Binding", 'Specifies which lshttpd child process the listener is assigned to.  Different child processes can be used to handle requests to different listeners by manually associating a listener with a process. By default, a listener is assigned to all child processes.', '', 'Select from checkbox', '');

$_tipsdb['listenerIP'] = new DAttrHelp("IP Address", 'Specifies the IP of this listener. All available IP addresses are listed.  IPv6 addresses are enclosed in &quot;[ ]&quot;. To listen on all IPv4 IP addresses, select  ANY. To listen on all IPv4 and IPv6 IP addresses, select [ANY]. In order to serve both IPv4 and IPv6 clients, an IPv4-mapped IPv6 address should be used instead of a plain IPv4 address. An IPv4-mapped IPv6 address is written as [::FFFF:x.x.x.x].', ' If your machine has multiple IPs on different sub-networks,  you can select a specific IP to only allow traffic from the corresponding sub-network.', 'Select from drop down list', '');

$_tipsdb['listenerModules'] = new DAttrHelp("Listener Modules", 'Listener module configuration data is, by default inherited from the Server module configuration.   The Listener Modules are limited to the TCP/IP Layer 4 hooks.', '', '', '');

$_tipsdb['listenerName'] = new DAttrHelp("Listener Name", 'A unique name for this listener.', '', '', '');

$_tipsdb['listenerPort'] = new DAttrHelp("Port", 'Specifies the TCP port of the listener. Only the super user (&quot;root&quot;) can use ports   lower than 1024. Port 80 is the default HTTP port. Port 443  is the default HTTPS port.', '', '无符号整数', '');

$_tipsdb['listenerSecure'] = new DAttrHelp("Secure", 'Specifies whether this is a secure (SSL) listener.  For secure listeners, additional SSL settings need to be set properly.', '', 'Select from radio box', '');

$_tipsdb['lmap'] = new DAttrHelp("Virtual Hosts Mappings", 'Shows currently established mappings to virtual hosts from a particular listener.  The virtual host name appears in brackets and is followed by the matching domain name(s) for this listener.', 'If a virtual host has not been loaded successfully (fatal errors in the  virtual host configuration), the mapping to that virtual host will not be displayed.', '', '');

$_tipsdb['lname'] = new DAttrHelp("Name - Listener", 'The unique name that identifies this listener. This is the  &quot;Listener Name&quot; you specified when setting up the listener.', '', '', '');

$_tipsdb['location'] = new DAttrHelp("Location", 'Specifies the corresponding location of this context in the file system.', '', 'It can be an absolute path or path relative to $SERVER_ROOT, $VH_ROOT, or $DOC_ROOT.  $DOC_ROOT is the default relative path, and can be omitted.<br/><br/>If the &quot;URI&quot; is a regular expression, then the matched sub-string  can be used to form the &quot;Root&quot; string. The matched sub-string can be  referenced with the values &quot;$1&quot; - &quot;$9&quot;. &quot;$0&quot; and &quot;&&quot; can be used to reference the  whole matched string. Additionally, a query string can be set by  appending a &quot;?&quot; followed by the query string. Be careful. &quot;&&quot; should be escaped as &quot;\&&quot; in the query string.', 'A plain URI like /examples/ with &quot;Location&quot;  set to /home/john/web_examples will map the request &quot;/examples/foo/bar.html&quot;  to file &quot;/home/john/web_examples/foo/bar.html&quot;. <br/>To simulate Apache&#039;s mod_userdir,  set URI to exp: ^/~([A-Za-z0-9]+)(.*),  set &quot;Location&quot; to /home/$1/public_html$2. With these settings, a request of URI /~john/foo/bar.html will  map to file /home/john/public_html/foo/bar.html.');

$_tipsdb['logUseServer'] = new DAttrHelp("使用服务器日志", '指定是否将虚拟主机的日志信息放置到服务器日志文件中，而不是创建独自的日志文件。', '', '布尔值', '');

$_tipsdb['log_debugLevel'] = new DAttrHelp("调试级别", '指定调试日志级别。 要使用此功能，&quot;日志级别&quot;必须设置为DEBUG。 在“调试级别”设置为NONE时，即使&quot;日志级别&quot; 设置为DEBUG，调试日志也是被禁用的。 在正在运行的服务器上，&quot;Toggle Debug Logging&quot;可以被用于 控制调试级别而无需重启。', '[性能建议] 重要！如果你不需要详细的调试日志记录， 应始终将其设置为NONE。启用调试日志记录将严重降低服务性能 ，且可能在很短时间耗尽磁盘空间。 调试日志记录包括每个请求和响应的详细信息。<br/><br/>我们推荐将日志级别设置为DEBUG，调试级别设置为NONE。 这些设置意味着你的磁盘不会被调试日志塞满， 但是你可以使用&quot;Toggle Debug Logging&quot; 控制调试输出。这个动作可以实时启用或关闭调试记录， 对于调试繁忙的生产服务器非常有用。', '选项', '');

$_tipsdb['log_enableStderrLog'] = new DAttrHelp("启用标准错误日志（stderr）", '指定在接受到服务器启动的进程输出的标准错误时，是否写入到日志。 如果启用，标准错误信息将记录到服务器日志所在目录内的固定名为“stderr.log”的文件。如果禁用，所有的标准错误输出都将被丢弃。', '如果您需要调试配置的外部应用程序，如PHP、Ruby、Java、Python、Perl，请开启该功能。', '布尔值', '');

$_tipsdb['log_fileName'] = new DAttrHelp("文件名", '指定日志文件的路径。', '[性能建议] 将日志文件放置在一个单独的磁盘上。', '文件2', '');

$_tipsdb['log_logLevel'] = new DAttrHelp("日志级别", '指定日志文件中记录的日志级别。 可用级别（由高到低）为: ERROR、 WARNING、NOTICE、INFO和DEBUG。 只有级别与当前设置相同或更高的消息将被记录（级别越低记录越详细）。', '[性能建议] 使用DEBUG日志级别对 性能没有任何影响，除非&quot;调试级别&quot;没有被设置为NONE.。我们推荐将日志级别设置为DEBUG，将 调试级别值设置为NONE。这样设置意味着你的磁盘不会被调试日志塞满，但是你可以使用&quot;Toggle Debug Logging&quot; 控制调试输出。这个操作可以实时启用或关闭调试记录， 对于调试繁忙的生产服务器非常有用。', '选项', '');

$_tipsdb['log_rollingSize'] = new DAttrHelp("回滚大小", '指定何时日志文件需要回滚，也称为日志循环。 当文件大小超过回滚限制后，在使用的日志文件将在同一目录中被重命名 为log_name.mm_dd_yyyy(.sequence)，一个新的日志文件将被创建。 回滚的日志文件的实际大小有时会比限制值稍微大一些。 将值设置为0将禁用日志循环。', '请用“K”，“M”，“G”代表千字节，兆字节和千兆字节。', '无符号整数', '');

$_tipsdb['lsapiContext'] = new DAttrHelp("LiteSpeed SAPI Context", 'External applications cannot be used directly. They must be either configured as  a script handler or mapped to a URL through a context. An LiteSpeed SAPI Context will  associate a URI with an LSAPI (LiteSpeed Server Application Programming Interface) application. Currently PHP, Ruby and Python have LSAPI modules. LSAPI, as it is developed specifically for LiteSpeed web server, is the most efficient way to communicate with LiteSpeed web server.', '', '', '');

$_tipsdb['lsapiapp'] = new DAttrHelp("LiteSpeed SAPI App", 'Specifies the name of the LiteSpeed SAPI application to be connected to this context. This application must be defined in the &quot;External Application&quot; section at the server or virtual host level.', '', 'Select from drop down list', '');

$_tipsdb['lstatus'] = new DAttrHelp("Status - Listener", 'The current status of this listener. The status is either Running or Error.', 'If the listener is in the Error state, you can view the server log to find out why.', '', '');

$_tipsdb['mappedListeners'] = new DAttrHelp("Mapped Listeners", 'Specifies the names of all listeners that this template maps to. A listener-to-virtual host mapping for this template&#039;s member virtual hosts will be added to the listeners specified in this field.  This mapping will map listeners to virtual hosts based on the domain names  and aliases set in the member virtual hosts&#039; individual configurations.', '', 'comma-separated list', '');

$_tipsdb['maxCGIInstances'] = new DAttrHelp("最大CGI实例数量", '指定服务器可以启动的CGI进程最大并发数量。 对于每个对CGI脚本的请求，服务器需要启动一个独立的CGI进程。 在Unix系统中，并发进程的数量是有限的。过多的并发进程会降 低整个系统的性能，也是一种进行拒绝服务攻击的方法。 LiteSpeed服务器将对CGI脚本的请求放入管道队列，限制并发 CGI进程数量，以确保最优性能和可靠性。 硬限制为2000。', '[安全和性能建议] 更高的数量并不一定转化为更快的性能。 在大多数情况下，更低的数量提供更好的性能和安全性。更高的数量 只在CGI处理过程中读写延迟过高时有帮助。', '无符号整数', '');

$_tipsdb['maxCachedFileSize'] = new DAttrHelp("最大小文件缓存", '指定预分配内存缓冲区中缓存的静态文件最大尺寸。静态文件 可以用四种不同的方式服务：内存缓存、内存映射缓存、直接读写和 sendfile()。 尺寸小于&quot;最大小文件缓存&quot;的文件将使用内存缓存服务。尺寸大于该限制、但小于 &quot;最大MMAP文件大小&quot;的文件，将使用内存映射缓存服务。 尺寸大于&quot;最大MMAP文件大小&quot;的文件将通过直接读写或sendfile() 服务。使用内存缓存服务小于4K的文件是最佳做法。', '', '无符号整数', '');

$_tipsdb['maxConnections'] = new DAttrHelp("Max Connections", 'Specifies the maximum number of concurrent connections that the server can accept.  This includes both plain TCP connections and SSL connections. Once the maximum concurrent connections limit is reached,  the server will close Keep-Alive connections when they complete active requests.', 'When the server is started by &quot;root&quot; user, the server will try to adjust the per-process file descriptor limits automatically, however, if this fails, you may need to increase this limit manually.', '无符号整数', '');

$_tipsdb['maxConns'] = new DAttrHelp("Max Connections", 'Specifies the maximum number of concurrent connections that can be established  between the server and an external application. This setting controls how  many requests can be processed concurrently by an external application,   however, the real limit also depends on the external application itself.  Setting this value higher will not help if the external application is not fast enough or cannot scale to a large number of concurrent requests.', ' Setting a high value does not directly translate to higher performance.  Setting the limit to a value that will not overload the external  application will provide the best performance/throughput.', '无符号整数', '');

$_tipsdb['maxDynRespHeaderSize'] = new DAttrHelp("动态回应报头最大大小", '指定动态回应的最大报头大小。硬限制为8KB。', '[可靠性和性能建议] 设置一个合理的低值以帮助识别外部应用程序产生的 坏的动态回应。', '无符号整数', '');

$_tipsdb['maxDynRespSize'] = new DAttrHelp("动态回应主内容最大大小", '指定动态回应的最大主内容尺寸。硬限制是2047MB。', '[可靠性和性能建议] 设置一个合理的低值以帮助识别坏的响应。恶意脚本经常包含 无限循环而导致大尺寸回应。', '无符号整数', '');

$_tipsdb['maxKeepAliveReq'] = new DAttrHelp("最大持续连接请求数", '指定通过持续连接（持久）会话处理的请求的最大数量。一旦达 到此限制，连接将被关闭。您也可以为每个虚拟主机单独设置限制。', '[性能建议] 设置为合理的较高的值。值为“1”或“0”时将禁用持续连接。', '无符号整数', '');

$_tipsdb['maxMMapFileSize'] = new DAttrHelp("最大MMAP文件大小", '指定使用内存映射（MMAP）的最大静态文件大小。 静态文件可以用四种不同的方式服务：内存缓存、内存映射缓存、直接读写和 sendfile()。 尺寸小于&quot;最大小文件缓存&quot;的文件将使用内存缓存服务。尺寸大于该限制、但小于 &quot;最大MMAP文件大小&quot;的文件，将使用内存映射缓存服务。 尺寸大于&quot;最大MMAP文件大小&quot;的文件将通过直接读写或sendfile() 服务。 由于服务器有一个32位的地址空间（2GB），不建议使用内存映射非常大的文件。', '', '无符号整数', '');

$_tipsdb['maxReqBodySize'] = new DAttrHelp("最大请求主内容大小", '指定HTTP请求主内容最大尺寸。对于32位操作系统， 硬限制为2GB。对于64位操作系统，几乎是无限的。', '[安全建议] 为了防止拒绝服务攻击，尽量将限制值设定到实际需求的大小。 交换空间的剩余空间必须比这个限制值大。', '无符号整数', '');

$_tipsdb['maxReqHeaderSize'] = new DAttrHelp("最大请求头大小", '指定请求URL中包含的HTTP请求头最大值。 硬限制为16380字节。', '[安全和性能建议] 设置合理的低值来减少内存的使用并帮助识别虚假请求和拒绝服务攻击。<br/>对于大多数网站来说4000-8000已经足够大。', '无符号整数', '');

$_tipsdb['maxReqURLLen'] = new DAttrHelp("最大请求URL长度", '指定请求URL的最大大小。URL是一个纯文本的地址，包含查询字符串来请求服务器上的资源。 8192字节是硬限制。', '[安全和性能建议] 将其设置合理的低值来以减少内存使用 并帮助识别虚假请求和拒绝服务攻击。<br/>对大多数网站2000-3000已经足够大，除非使用HTTP GET而不是POST来提交大型的查询字符串。', '无符号整数', '');

$_tipsdb['maxSSLConnections'] = new DAttrHelp("最大SSL连接数", '指定服务器接受的并发SSL连接的最大数量。 由于总的并发SSL和非SSL连接不能超过&quot;Max Connections&quot;规定的限额， 允许的并发SSL连接的实际数量必须低于此限制。', '', '无符号整数', '');

$_tipsdb['memHardLimit'] = new DAttrHelp("内存硬限制", '与&quot;内存软限制&quot;非常相同，但是在一个用户进程中，软限制 可以被放宽到硬限制的数值。硬限制可以在服务器级别或独立的外部应用程序级别设 置。如果未在独立的外部应用程序级别设定限制，将使用服务器级别的限制。<br/><br/>如果在两个级别都没有设置该限制，或者限制值设为0，将使用操 作系统的默认设置。', '', '无符号整数', '[注意] 不要过度调整这个限制。如果您的应用程序需要更多的内存， 这可能会导致503错误。');

$_tipsdb['memSoftLimit'] = new DAttrHelp("内存软限制", '以字节为单位指定服务器启动的外部应用进程或程序的内存占用限制。<br/><br/>此限制的目的主要是为了防范软件缺陷或蓄意攻击造成的过度内存使用， 而不是限制正常使用。确保留有足够的内存，否则您的应用程序可能故障并 返回503错误。限制可以在服务器级别或独立的外部应用程序级别设置。如 果未在独立的外部应用程序级别设定限制，将使用服务器级别的限制。<br/><br/>如果在两个级别都没有设置该限制，或者限制值设为0，将使用操 作系统的默认设置。', '[注意] 不要过度调整这个限制。如果您的应用程序需要更多的内存， 这可能会导致503错误。', '无符号整数', '');

$_tipsdb['memberVHRoot'] = new DAttrHelp("Member Virtual Host Root", 'Specifies the root directory of this virtual host. If left blank, the default virtual host root for this template will be used.<br/><br/>Note: This is <b>NOT</b> the document root. It is recommended to place  all files related to the virtual host (like virtual host configuration,  log files, html files, CGI scripts, etc.) under this directory.   Virtual host root can be referred to as $VH_ROOT.', '', 'path', '');

$_tipsdb['mime'] = new DAttrHelp("MIME设置", '为此服务器指定包含MIME设置的文件。 在chroot模式中提供了绝对路径时，该文件路径总是相对于真正的根。 点击文件名可查看/编辑详细的MIME项。', 'Click the filename to edit the MIME settings.', '文件2', '');

$_tipsdb['mimesuffix'] = new DAttrHelp("后缀", '你可以列出相同MIME类型的多个后缀，用逗号分隔。', '', '', '');

$_tipsdb['mimetype'] = new DAttrHelp("MIME类型", '一个MIME类型由一个类型和子类型组成，格式为“类型/子类型”。', '', '', '');

$_tipsdb['minGID'] = new DAttrHelp("最小的GID", '指定外部应用程序的最小组ID。 如果组ID比这里指定的值更小，其外部脚本的执行将被拒绝。 如果的LiteSpeed Web服务器是由“Root”用户启动，它可以在“suEXEC” 模式运行外部应用程序，类似Apache（可以切换到与Web服务器不同的用户/组ID）。', '[安全] 设置足够高的值以排除所有系统用户所属的组。', '无符号整数', '');

$_tipsdb['minUID'] = new DAttrHelp("最小的UID", '指定外部应用程序的最小用户ID。 如果用户ID比这里指定的值更低。其外部脚本的执行将被拒绝。 如果的LiteSpeed Web服务器由“Root”用户启动，它可以在“suEXEC” 模式运行外部应用程序，类似Apache（可以切换到与Web服务器不同的用户/组ID）。', '[安全] 设置足够高的值以排除所有系统/特权用户。', '无符号整数', '');

$_tipsdb['modParams'] = new DAttrHelp("Module Parameters", 'Set module parameters. The module parameters are defined by the module developer.<br/><br/>Set the value in the Server configuration to globally assign the default value.  The user can override this setting at the Listener, Virtual Host or Context levels. If the &#039;Not Set&#039; radio button is selected, it will be inherited from the upper level.', '', 'Specified by the module interface.', '');

$_tipsdb['moduleContext'] = new DAttrHelp("Module Handler Context", 'A module handler context will associate a URI with a registered module.  Modules need to be registered at Server Module Configuration tab.', '', '', '');

$_tipsdb['moduleEnabled'] = new DAttrHelp("Enable Hooks", 'Enables or disables the module hooks globally. <br/>If the &#039;Not Set&#039; radio button is selected and the module contains hook functions, the default is enabled.  The user can override this global setting at each level.', '', 'Select from radio box', '');

$_tipsdb['moduleEnabled_lst'] = new DAttrHelp("Enable Hooks", 'Enables or disables the module hooks at the Listener level. Only if the module has TCP/IP level hooks  (L4_BEGSESSION, L4_ENDSESSION, L4_RECVING, L4_SENDING), this setting will take effect.<br/><br/>If the &#039;Not Set&#039; radio button is selected, the default will be inherited from the Server configuration. The user only needs to set it here to  override the default settings.', '', 'Select from radio box', '');

$_tipsdb['moduleEnabled_vh'] = new DAttrHelp("Enable Hooks", 'Enables or disables the module hooks at the Virtual Host or Context level. Only if the module has HTTP level hooks,  this setting will take effect.<br/><br/>If the &#039;Not Set&#039; radio button is selected, the Virtual Host level default settings will be inherited from the Server configuration. Context level settings will be   inherited from the Virtual Host level. The user only needs to set it here to override the default settings.', '', 'Select from radio box', '');

$_tipsdb['moduleNameSel'] = new DAttrHelp("Module", 'Name of the module. The module must be registered under the Server Module Configuration tab.   Once it is registered, the module name will be available in the drop down box for the Listener and Virtual Host configurations.', '', 'Select from drop down list', '');

$_tipsdb['modulename'] = new DAttrHelp("Module", 'Name of the module. The module name will be the same as the module filename.  The module file must be located under $SERVER_ROOT/modules/modulename.so in order to be loaded by the server application. The server will load the registered modules at start up. This requires that the server is restarted after new modules are registered.', '', 'the library name of .so.', '');

$_tipsdb['note'] = new DAttrHelp("Notes", 'Add notes for yourself.', '', '', '');

$_tipsdb['ocspCACerts'] = new DAttrHelp("OCSP CA Certificates", 'Specifies the location of the file where OCSP certificate authority (CA)  certificates are stored. These certificates are used to check responses  from the OCSP responder (and make sure those responses are not spoofed or  otherwise compromised). This file should contain the whole certificate chain.  If this file does not contain the root certificate, LSWS should be able to find  the root certificate in your system directory without you adding it to the file,  but, if this validation fails, you should try adding your root certificate to this file. <br/><br/>This setting is optional. If this setting is not set, the server will automatically check &quot;CA Certificate File&quot;.', '', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT.', '');

$_tipsdb['ocspRespMaxAge'] = new DAttrHelp("OCSP Response Max Age (secs)", 'This option sets the maximum allowable age for an OCSP response. If an OCSP response is older than this maximum age, the server will contact the OCSP responder for a new response. The default value is 86400. Maximum age can be turned off by setting this value to -1.', '', 'Integer of seconds', '');

$_tipsdb['ocspResponder'] = new DAttrHelp("OCSP Responder", 'Specifies the URL of the OCSP responder to be used.  If not set, the server will attempt to contact the OCSP responder  detailed in the certificate authority&#039;s issuer certificate.  Some issuer certificates may not have an OCSP responder URL specified.', '', 'URL starting with http://', 'http://rapidssl-ocsp.geotrust.com ');

$_tipsdb['outBandwidth'] = new DAttrHelp("出口带宽", '指定对单个IP地址允许的最大传出吞吐量（无论与该IP之间建立了多少个连接）。 为提高效率，真正的带宽可能最终会略高于设定值。 带宽按4KB为单位分配。设定值为0可禁用限制。 每个客户端的带宽限制（字节/秒）可以在服务器或虚拟主机级别设置。 虚拟主机级别的设置将覆盖服务器级别的设置。', '[性能建议] 按8KB单位设置带宽可获得更好的性能。<br/>[安全建议] 受信任的IP或子网不受影响。', '无符号整数', '');

$_tipsdb['pcKeepAliveTimeout'] = new DAttrHelp("Keep Alive Timeout (secs)", 'Specifies the maximum time to keep an idle persistent connection open. When set to &quot;-1&quot;, the connection will never timeout. When set to greater than or equal to 0, the connection will be closed after this time in seconds has passed.', '', 'int', '');

$_tipsdb['perClientConnLimit'] = new DAttrHelp("Per Client Throttling", 'These are connection control settings are based on client IP.  These settings help to mitigate DoS (Denial of Service) and DDoS (Distributed Denial of Service) attacks.', '', '', '');

$_tipsdb['persistConn'] = new DAttrHelp("Persistent Connection", 'Specifies whether to keep the connection open after a request has been processed. Persistent connections can increase performance,  but some FastCGI external applications do not support persistent connections  fully. The default is &quot;On&quot;.', '', 'Select from radio box', '');

$_tipsdb['pid'] = new DAttrHelp("PID", 'PID (Process ID) of the current server process.', 'The PID will change each time the server is restarted.', '', '');

$_tipsdb['procHardLimit'] = new DAttrHelp("进程硬限制", '与&quot;进程软限制&quot;非常相同，但是，在用户进程中软限制 可以被放宽到硬限制的数值。硬限制可以在服务器级别或独立的外部应用程序级别设 置。如果未在独立的外部应用程序级别设定限制，将使用服务器级别的限制。 如果在两个级别都没有设置该限制，或者限制值设为0，将使用操 作系统的默认设置。', '', '无符号整数', '');

$_tipsdb['procSoftLimit'] = new DAttrHelp("进程软限制", '限制一个用户可以创建的进程总数。所有存在的进程都将被统计在内， 而不是只包括新启动的进程。如果限制被设置为10，并且一个用户下 有超过10个进程在运行，那么网站服务器将不会再为该用户（通过 suEXEC） 启动新进程。<br/><br/>此限制的主要目的是为了防范“fork炸弹”攻击或过量使用，而不是限制正常使用 （如果该限制被设置的过低，它将被服务器忽略）。确保留有足够空余。 本项目可以在服务器级别或独立的外部应用程序级别设置。如果未在独立的外部应用程 序级别设定限制，将使用服务器级别的限制。如果在两个级别都没有设置该限制， 或者限制值设为0，将使用操作系统的默认设置。', 'PHP scripts can call for forking processes. The main purpose of this limit is as a last line of defense to prevent fork bombs and  other attacks caused by PHP processes creating other processes. <br/>Setting this setting too low can severely hurt functionality. The setting will thus be ignored below certain levels.<br/>When using suEXEC Daemon mode, the actual process limit will be higher than this setting to make sure parent processes are not limited.', '无符号整数', '');

$_tipsdb['proxyContext'] = new DAttrHelp("Proxy Context", 'A Proxy Context enables this virtual host as a transparent reverse proxy server. This proxy server can run in front of any web  servers or application servers that support HTTP protocol. The External web server that this virtual host proxies for  has to be defined in &quot;External Application&quot;  before you can set up a Proxy Context.', '', '', '');

$_tipsdb['proxyWebServer'] = new DAttrHelp("Web Server", 'Specifies the name of the external web server. This external web server must be defined in the &quot;External Application&quot; section at the server or virtual host level.', '', 'Select from drop down list', '');

$_tipsdb['railsContext'] = new DAttrHelp("Rack/Rails Context", 'A Rack/Rails Context provides an easy way to configure a Ruby Rack/Rails application. To add a Rack/Rails application through a Rack/Rails Context,  only mounting the URL and the application&#039;s root directory is required. There is  no need to go through all the troubles to define an external application, add a 404 handler,  and rewrite rules, etc.', '', '', '');

$_tipsdb['railsDefault'] = new DAttrHelp("Ruby Rack/Rails Settings", 'Default configurations for Ruby Rack/Rails applications.', '', '', '');

$_tipsdb['railsEnv'] = new DAttrHelp("Run-Time Mode", 'Specifies which mode Rack/Rails will be running as: &quot;Development&quot;,  &quot;Production&quot;, or &quot;Staging&quot;. The default is &quot;Production&quot;.', '', 'Select from drop down list', '');

$_tipsdb['rails_location'] = new DAttrHelp("Location", 'Specifies the corresponding location of this context in the file system.', '', 'It can be an absolute path or path relative to $SERVER_ROOT, $VH_ROOT, or $DOC_ROOT.  $DOC_ROOT is the default relative path, and can be omitted.<br/><br/>If the &quot;URI&quot; is a regular expression, then the matched sub-string  can be used to form the &quot;Root&quot; string. The matched sub-string can be  referenced with the values &quot;$1&quot; - &quot;$9&quot;. &quot;$0&quot; and &quot;&&quot; can be used to reference the  whole matched string. Additionally, a query string can be set by  appending a &quot;?&quot; followed by the query string. Be careful. &quot;&&quot; should be escaped as &quot;\&&quot; in the query string.', 'A plain URI like /examples/ with &quot;Location&quot;  set to /home/john/web_examples will map the request &quot;/examples/foo/bar.html&quot;  to file &quot;/home/john/web_examples/foo/bar.html&quot;. <br/>To simulate Apache&#039;s mod_userdir,  set URI to exp: ^/~([A-Za-z0-9]+)(.*),  set &quot;Location&quot; to /home/$1/public_html$2. With these settings, a request of URI /~john/foo/bar.html will  map to file /home/john/public_html/foo/bar.html.');

$_tipsdb['rcvBufSize'] = new DAttrHelp("接收缓冲区大小", '每个TCP套接字的接收缓冲区的大小。设定值为0使用 操作系统默认的缓冲区大小。65535是允许的最大缓冲区大小。', '[性能建议] 处理大载荷入站请求，如文件上传时，大的接收缓冲区会提高性能。', '无符号整数', '');

$_tipsdb['realm'] = new DAttrHelp("Realm", '指定这个context下的realm授权。 当指定时，必须提供有效的用户和用户名来访问这个context。 &quot;Realms授权&quot;需要在&quot;Virtual Host Security&quot;部分进行设置。此设置使用每个realm的&quot;Realm名称&quot;。', '', '选项', '');

$_tipsdb['realmName'] = new DAttrHelp("Realm名称", '为Realm授权指定唯一的名称。', '', '文本', '');

$_tipsdb['realms'] = new DAttrHelp("Realms授权", '列出这个虚拟主机的所有Realm。 Realm授权可以阻止未授权用户访问受保护的网页。 Realm是一个用户名录，其中包含了用户名、密码、分组（可选）。授权是在context级别执行的。不同的context可以共享相同的Realm（用户数据库），所以Realm是与调用它的context分开定义的。你可以通过context配置中的名称识别Realm。', '', '', '');

$_tipsdb['realtimerpt'] = new DAttrHelp("Real-Time Statistics", 'The Real-Time Statistics link leads to a page with a real-time server status report. This is a convenient tool to monitor the system.    The report shows a snapshot of your server statistics. The refresh rate for this snapshot  is controlled by the Refresh Interval drop-down list in the upper righthand corner.   The report contains the following sections: <ul><li>Server Health shows the basic server statistics, uptime, load, and anti-DDoS blocked IPs.</li>   <li>Server lists current traffic throughput, connections, and requests statistics.</li>  <li>Virtual Host shows request processing statuses and external application statuses for each virtual host.</li>  <li>External Application lists the external applications currently running and their usage statistics.   The CGI daemon process lscgid is always running as an external application.</li> </ul>   Many of the rows in the Real-Time Statistics feature a graph icon.  Clicking on this icon will open a graph of that row&#039;s statistics updated in real-time.   In the Server section, next to Requests, there is a link labeled (Details).  This link takes you to the Requests Snapshot, where you can view detailed information  on which clients are making certain kinds of requests or which aspects of your site  are bottlenecking. The fields in the blue area allow you to filter the snapshot to isolate  certain parts of your server or look for clients that are performing certain actions.', '', '', '');

$_tipsdb['redirectContext'] = new DAttrHelp("Redirect Context", 'A Redirect Context can be used to forward one URI or a group of URIs to another location.  The destination URI can be either on the same web site (an internal redirect) or an absolute URI pointing to another web site (an external redirect).', '', '', '');

$_tipsdb['renegProtection'] = new DAttrHelp("SSL Renegotiation Protection", 'Specifies whether to enable SSL Renegotiation Protection to  defend against SSL handshake-based attacks. The default value is &quot;Yes&quot;.', 'This setting can be enabled at the listener and virtual host levels.', 'Select from radio box', '');

$_tipsdb['required'] = new DAttrHelp("Require（授权的用户/组）", '指定哪些用户/用户组可以访问此context。 这里允许你使用一个用户/组数据库(在 &quot;Realm&quot;中指定)访问多个context， 但只允许该数据库下特定的用户/组访问这个context。', '', '语法兼容Apache的Require指令。例如: <ul> <li>user username [username ...] <br/>只有列出的用户可以访问这个context;</li> <li> group groupid [groupid ...]<br/>用户必须属于列出的组才可以访问这个context。</li> </ul> 如果没有指定，所有有效的用户都可以访问这个资源。', '');

$_tipsdb['requiredPermissionMask'] = new DAttrHelp("Required Permission Mask", '为静态文件指定必需的权限掩码。 例如，如果只允许所有人都可读的文件可以被输出，将该值设置为0004。 用man 2 stat命令了解所有可选值。', '', '八进制数', '');

$_tipsdb['respBuffer'] = new DAttrHelp("Response Buffering", 'Specifies whether to buffer responses received from external applications. If a &quot;nph-&quot; (Non-Parsed-Header) script is detected,  buffering is turned off for responses with full HTTP headers.', '', 'Select from drop down list', '');

$_tipsdb['restart'] = new DAttrHelp("Apply Changes/Graceful Restart", 'By clicking Graceful Restart, a new server process will be started.  For Graceful Restart, the old server process will only exit after all requests  to it have been finished (or the &quot;平滑重启超时时长&quot; limit has been reached).   Configuration changes are applied at the next restart.  Graceful Restart will apply these changes without any server downtime.', 'Graceful restart takes less than 2 seconds to generate a new server process.', '', '');

$_tipsdb['restrained'] = new DAttrHelp("访问管制", '指定虚拟机根($VH_ROOT)以外的文件是否可以通过这个网站访问。 如果设置是Yes，只可以访问$VH_ROOT下的文件， 访问指向$VH_ROOT以外文件或目录的符号链接或context指向都将被阻止。 尽管如此，这里不会限制CGI脚本的访问。 这个选项在共享主机下非常有用。 &quot;跟随符号链接&quot;可以设置成Yes来允许用户使用在$VH_ROOT下的符号链接， $VH_ROOT以外的则不可以。', '[安全建议] 在共享主机环境下打开该功能。', '布尔值', '');

$_tipsdb['restrictedDirPermissionMask'] = new DAttrHelp("脚本目录限制权限掩码", '为不能服务的脚本文件父目录指定限制权限掩码。 例如，要禁止服务属组可写和全局可写的文件夹内的PHP脚本， 设置掩码为022。默认值是000。 此选项可用于防止执行文件上传目录内的脚本。<br/><br/>用man 2 stat命令了解所有可选值。', '', '八进制数', '');

$_tipsdb['restrictedPermissionMask'] = new DAttrHelp("限制权限掩码", '为不能输出的静态文件指定限制权限掩码。 例如，要禁止服务可执行文件，将掩码设置为0111。<br/><br/>用man 2 stat命令了解所有可选值。', '', '八进制数', '');

$_tipsdb['restrictedScriptPermissionMask'] = new DAttrHelp("脚本限制权限掩码", '为不能服务的脚本文件指定限制权限掩码。 例如，要禁止服务属组可写和全局可写的PHP脚本， 设置掩码为022。默认值是000。<br/><br/>用man 2 stat命令了解所有可选值。', '', '八进制数', '');

$_tipsdb['retryTimeout'] = new DAttrHelp("Retry Timeout (secs)", 'Specifies the period of time that the server waits before retrying an external application that had a prior communication problem.', '', '无符号整数', '');

$_tipsdb['rewriteBase'] = new DAttrHelp("重写基准", '指定重写规则的基准URL。', '', 'URL', '');

$_tipsdb['rewriteInherit'] = new DAttrHelp("重写继承", '指定是否从父级context继承重写规则。 如果启用重写但不继承，将启用本context的重写基准及重写规则。', '', '布尔值', '');

$_tipsdb['rewriteLogLevel'] = new DAttrHelp("Log Level", 'Specifies the level of detail of the rewrite engine&#039;s debug output. This value ranges from 0 - 9. 0 disables logging. 9 produces the most detailed log. The server and virtual host&#039;s error log &quot;日志级别&quot;  must be set to at least INFO for this option to take effect. This is useful when testing rewrite rules.', '', '无符号整数', '');

$_tipsdb['rewriteMapLocation'] = new DAttrHelp("Location", 'Specifies the location of the rewrite map using the syntax MapType:MapSource.<br/>LiteSpeed&#039;s rewrite engine supports three types of rewrite maps: <ul> 	<li><b>Standard Plain Text</b> <blockquote> 		<b>MapType:</b> txt; <br/>		<b>MapSource:</b> file path to a valid plain ASCII file.  </blockquote> 		Each line of this file should contain two elements separated  		by blank spaces. The first element is the key and the second 		element is the value. Comments can be added with a leading &quot;#&quot; 		sign.  	</li> 	<li><b>Randomized Plain Text</b> <blockquote> 		<b>MapType:</b> rnd;<br/>		<b>MapSource:</b> file path of a valid plain ASCII file. </blockquote> 		File format is similar to the Standard Plain Text file, except that the 		second element can contain multiple choices separated by a &quot;|&quot; 		sign and chosen randomly by the rewrite engine. 	</li> 	<li><b>Internal Function</b> <blockquote> 	    <b>MapType:</b> int;<br/>		<b>MapSource:</b> Internal string function  </blockquote> 		4 functions are available: 		<ul> 			<li><b>toupper:</b> converts lookup key to upper cases.</li> 			<li><b>tolower:</b> converts lookup key to lower cases.</li> 			<li><b>escape:</b> perform URL encoding on lookup key.</li> 			<li><b>unescape:</b> perform URL decoding on lookup key.</li> 		</ul> 	</li> 	The following map types available in Apache 	have not been implemented in LiteSpeed:<br/>Hash File and External Rewriting Program. </ul> The implementation of LiteSpeed&#039;s rewrite engine follows the specifications of Apache&#039;s rewrite engine. For more details about rewrite map, please refer to <a href="http://httpd.apache.org/docs/current/mod/mod_rewrite.html" target="_blank" rel="noopener noreferrer">Apache&#039;s mod_rewrite document</a>.', '', 'String', '');

$_tipsdb['rewriteMapName'] = new DAttrHelp("Name", 'Specifies a unique name for the rewrite map at the virtual host  level. This name will be used by a mapping-reference in rewrite rules. When referencing this name, one of the following syntaxes should be used: <blockquote><code> $\{MapName:LookupKey\}<br/>$\{MapName:LookupKey|DefaultValue\} </code></blockquote><br/>The implementation of LiteSpeed&#039;s rewrite engine follows the specifications of Apache&#039;s rewrite engine. For more details about rewrite maps, please refer to <a href="http://httpd.apache.org/docs/current/mod/mod_rewrite.html" target="_blank" rel="noopener noreferrer">Apache&#039;s mod_rewrite document</a>.', '', 'string', '');

$_tipsdb['rewriteRules'] = new DAttrHelp("Rewrite Rules", 'Specifies a list of rewrite rules at the virtual host or context level. A rewrite rule is comprised of one RewriteRule directive and optionally preceded by multiple RewriteCond directives.  <ul> <li>Each directive should take only one line. </li> <li>RewriteCond and RewriteRule follow Apache&#039;s rewrite directive syntax. Just copy and paste rewrite directives from your Apache configuration files.</li> <li>There are minor differences between LiteSpeed and Apache mod_rewrite implementation:  <ul><li>%\{LA-U:variable\} and %\{LA-F:variable\} are ignored by the LiteSpeed rewrite engine </li>   <li>two new server variables are added in the LiteSpeed rewrite engine:    %\{CURRENT_URI\} represents the current URI being processed by the rewrite engine and %\{SCRIPT_NAME\} has the same  meaning as the corresponding CGI environment variable. </li> </ul></li> </ul> The implementation of LiteSpeed&#039;s rewrite engine follows the  Apache&#039;s rewrite engine specifications. For more details about rewrite rules, please refer to <a href="http://httpd.apache.org/docs/current/mod/mod_rewrite.html" target="_blank" rel="noopener noreferrer">Apache&#039;s mod_rewrite document</a> and <a href="http://httpd.apache.org/docs/current/rewrite/" target="_blank" rel="noopener noreferrer">Apache&#039;s URL  rewriting guide</a>.', '', 'string', '');

$_tipsdb['rubyBin'] = new DAttrHelp("Ruby Path", 'Specifies path to Ruby executable. Generally, it is /usr/bin/ruby or /usr/local/bin/ruby depending on where Ruby has been installed to.', '', '绝对路径', '');

$_tipsdb['runOnStartUp'] = new DAttrHelp("Run On Start Up", 'Specifies whether to start the external application at server start up. Only applicable to external applications that can manage their own child processes and where  &quot;Instances&quot; value is set to &quot;1&quot;. If enabled, external processes will be created at server startup instead of run-time.', ' If the configured external process has significant startup overhead, like a Rails app, then  this option should be enabled to decrease first page response time.', 'Select from radio box', '');

$_tipsdb['runningAs'] = new DAttrHelp("Running As", 'Specifies the user/group that the server process runs as. This is set  using the parameters &quot;--with-user&quot; and &quot;--with-group&quot; when running the configure  command before installation. To reset these values, you must rerun the configure  command and reinstall.', ' Server should not run as a privileged user such as &quot;root&quot;.  It is critical that the server is configured to run with a un-privileged user/group combination  that does not have login/shell access. A user/group of nobody is generally a good choice.', '', '');

$_tipsdb['servAction'] = new DAttrHelp("Actions", 'Six actions are available from this menu: Graceful Restart, Toggle Debug Logging, Server Log Viewer, Real-Time Statistics,  Version Manager, and Compile PHP.  <ul><li>&quot;Apply Changes/Graceful Restart&quot; restarts server process gracefully without interrupting requests in process.</li> 	<li>&quot;Toggle Debug Logging&quot; turns debug logging on or off.</li> 	<li>&quot;Server Log Viewer&quot; allows you to view the server log through the log viewer.</li> 	<li>&quot;Real-Time Statistics&quot; allows you to view real-time server status.</li> 	<li>&quot;Version Management&quot; allows you to download new versions of LSWS and switch between different versions. 	<li>Compile PHP allows you to compile PHP for LiteSpeed Web Server. </ul>', 'The shell utility $SERVER_ROOT/bin/lswsctrl can be used to control the server processes as well,  but requires a login shell.', '', '');

$_tipsdb['servModules'] = new DAttrHelp("Server Modules", 'The Server module configuration globally defines the module configuration data.  Once defined, the Listeners and Virtual Hosts have access to the modules and module configurations. <br/><br/>All modules that are to be processed must be registered in the Server configuration. The Server configuration also  defines the default values for module parameter data.  These values can be inherited  or overridden by the Listener and Virtual Host configuration data.<br/><br/>Module priority is only defined at server level and is inherited by the Listener and Virtual Host configurations.', '', '', '');

$_tipsdb['serverName'] = new DAttrHelp("服务器名称", '该服务器的唯一名称。您可以在此填写 $HOSTNAME 。', '', '文本', '');

$_tipsdb['serverPriority'] = new DAttrHelp("优先级", '指定服务进程的优先级。数值范围从 -20 到 20。数值越小，优先级越高。', '[性能建议] 通常在繁忙的服务器上，较高的优先级会得到性能的小幅提升。 不要设置比数据库进程更高的优先级。', '整数', '');

$_tipsdb['servletContext'] = new DAttrHelp("Servlet Context", 'Servlets can be imported individually through Servlet Contexts.  A Servlet Context just specifies the URI for the servlet and the name of the servlet engine.  You only need to use this when you do not want to import the whole web application  or you want to protect different servlets with different authorization realms.  This URI has the same requirements as for a &quot;Java Web App Context&quot;.', '', '', '');

$_tipsdb['servletEngine'] = new DAttrHelp("Servlet Engine", 'Specifies the name of the servlet engine that serves this web application. Servlet engines must be defined in the &quot;External Application&quot; section at the server or virtual host level.', '', 'Select from drop down list', '');

$_tipsdb['setUidMode'] = new DAttrHelp("外部应用程序设置UID模式", '指定如何为外部程序进程设置用户ID。可以选择下面三种方式： <ul><li>Server UID: 为外部应用程序设置与服务器用户/组ID相同的用户/组ID。</li>     <li>CGI File UID: 为外部应用CGI程序设置基于可执行文件的用户/组ID。该选项仅适用于CGI，不适用于FastCGI或LSPHP。</li>     <li>Doc Root UID: 为外部应用程序设置基于当前虚拟机根目录的用户/组ID。</li> </ul>', '[安全建议] 在共享主机环境中，建议使用CGI File UID  或 Doc Root UID模式来防止一个虚拟主机下的文件被另一个虚拟主机的外部应用程序访问。', '选项', '');

$_tipsdb['shHandlerName'] = new DAttrHelp("处理器名称", '当处理器类型为FastCGI，Web服务器，LSAPI，负载均衡器或Servlet引擎时， 指定处理脚本文件的外部程序名称。', '', '选项', '');

$_tipsdb['shType'] = new DAttrHelp("类型", '指定处理这些脚本文件的外部程序类型。 可用类型有：CGI, FastCGI, Web服务器, LSAPI应用程序, 负载均衡器, 或 Servlet引擎。 对于FastCGI, Web服务器和Servlet引擎，需要指定&quot;处理器名称&quot;。 这是在&quot;External Application&quot;部分预设定的外部程序名称。', '', '选项', '');

$_tipsdb['shmDefaultDir'] = new DAttrHelp("Default SHM Directory", 'Changes shared memory&#039;s default directory to the specified path. If the directory does not exist, it will be created.  All SHM data will be stored in this directory unless otherwise specified.', '', 'Path', '');

$_tipsdb['showVersionNumber'] = new DAttrHelp("服务器签名", '指定是否在响应头的Server参数中显示服务器签名和版本号。 有三个选项: 当设置为Hide Version时、只显示LiteSpeed。当设置为 Show Version，显示LiteSpeed和版本号。  设置为Hide Full Header时，整个Server头都不会显示在响应报头中。', '[安全建议] 如果你不想暴露服务器的版本号，设置为Hide Version。', '布尔值', '');

$_tipsdb['smartKeepAlive'] = new DAttrHelp("智能持续连接", '指定是否启用智能持续连接。此选项只在&quot;最大持续连接请求数&quot;的值大于1 时有效。启用之后，您还可以在虚拟主机级别启用或禁用它。智能持久连接将只为 JavaScript、CSS样式表和图像文件请求建立持续连接。对于HTML页面，连接 不会被保持活跃。这有助于更高效地服务更多用户。通常包含多个图像和脚本的 网页将在初次请求之后被浏览器缓存。 通过一个持续连接来发送那些非HTML静态文件，同时通过另一非持续连接发送 text/html文件的做法更为高效。这种方法将减少闲置连接，进而提高处理并发请 求和更多用户的能力。', '[性能建议] 为高负载网站启用该功能。', '布尔值', '');

$_tipsdb['sname'] = new DAttrHelp("Name - Server", 'The unique name that identifies this server. This is the  &quot;服务器名称&quot; specified in the general configuration.', '', '', '');

$_tipsdb['sndBufSize'] = new DAttrHelp("发送缓冲区大小", '每个TCP套接字的发送缓冲区的大小。设定值为0使用 操作系统默认的缓冲区大小。65535是允许的最大缓冲区大小。', '[性能建议] 如果您的网站服务大量的静态文件，增加发送缓冲区 大小来提高性能。', '无符号整数', '');

$_tipsdb['softLimit'] = new DAttrHelp("连接软限制", '指定来自单个IP的并发连接的软限制。 并发连接数低于&quot;连接硬限制&quot;时，此软限制可以在&quot;宽限期（秒）&quot;期间临时超过， 但Keep-Alive连接将被尽快断开，直到连接数低于软限制。 如果&quot;宽限期（秒）&quot;之后，连接数仍然超过软限制，相应的IP将被封锁 &quot;禁止期（秒）&quot;所设置的时长。<br/><br/>例如，如果页面包含许多小图像，浏览器可能会尝试同时建立许多连接，尤其是HTTP/1.0客户端。你应当在短时间内允许这些连接。<br/><br/>HTTP/1.1客户端还可能建立多个连接，以加快下载，另外SSL需要为非SSL连接建立单独的连接。确保限制设置正确， 以免影响正常服务。建议限制在5与10之间。', '[安全建议] 一个较低的数字将使得服务器可以服务更多独立的客户。<br/>[安全建议] 受信任的IP或子网不受影响。<br/>[性能建议] 使用大量并发客户端进行性能评测时，请设置一个较高的值。', '无符号整数', '');

$_tipsdb['sslCert'] = new DAttrHelp("SSL Private Key & Certificate", 'Every SSL listener requires a paired SSL private key and SSL certificate.  Multiple SSL listeners can share the same key and certificate. <br/><br/>You can generate SSL private keys yourself using an SSL software package,  such as OpenSSL. SSL certificates can also be purchased from an authorized certificate  issuer like VeriSign or Thawte. You can also sign the certificate yourself.  Self-signed certificates will not be trusted by web browsers and should not be used on public websites  containing critical data. However, a self-signed certificate is good  enough for internal use, e.g. for encrypting traffic to LiteSpeed Web Server&#039;s WebAdmin Console.', '', '', '');

$_tipsdb['sslEnableMultiCerts'] = new DAttrHelp("Enable Multiple SSL Certificates", 'Allows listeners/vhosts to set multiple SSL certificates.  If multiple certificates are enabled, the certificates/keys  are expected to follow a naming scheme.  If the cert is named server.crt, other possible cert names are server.crt.rsa, server.crt.dsa, server.crt.ecc. If  &quot;Not Set&quot;, defaults to &quot;No&quot;.', '', 'Select from radio box', '');

$_tipsdb['sslOCSP'] = new DAttrHelp("OCSP Stapling", 'Online Certificate Status Protocol (OCSP) is a more efficient method  of checking whether a digital certificate is valid. It works by communicating  with another server — the OCSP responder — to get verification that the certificate  is valid instead of checking through certificate revocation lists (CRL).<br/><br/>OCSP stapling is a further improvement on this protocol, allowing the server to  check with the OCSP responder at regular intervals instead of every time a certificate  is requested. See the <a href=&quot;http://en.wikipedia.org/wiki/OCSP_Stapling&quot;>OCSP Wikipedia page</a> for more details.', '', '', '');

$_tipsdb['sslProtocol'] = new DAttrHelp("Protocol Version", 'Specifies which version of the SSL protocol will be used. You can choose from  SSL v3.0 and TLS v1.0. Since OpenSSL 1.0.1, TLS v1.1, TLS v1.2 are also supported. TLS v1.3  is also supported via BoringSSL.', 'Leaving this field blank will enable TLS v1.0, TLS v1.1, and TLS v1.2 by default. TLS v1.3 requires BoringSSL and will  also be enabled if the underlying SSL library supports it.', '', '');

$_tipsdb['sslProtocolSetting'] = new DAttrHelp("SSL Protocol", 'Customizes SSL protocols accepted by the listener.', '', '', '');

$_tipsdb['sslSessionCache'] = new DAttrHelp("Enable Session Cache", 'Enables session id caching. If &quot;Not Set&quot;, defaults to  &quot;No&quot;. (Openssl Default)', '', 'Select from radio box', '');

$_tipsdb['sslSessionCacheSize'] = new DAttrHelp("Session Cache Size (bytes)", 'Sets the maximum number of SSL session IDs to store in the cache. Default is 1,000,000.', '', 'Integer number', '');

$_tipsdb['sslSessionCacheTimeout'] = new DAttrHelp("Session Cache Timeout (secs)", 'This value determines how long a session ID will be valid within the cache before renegotiation is required. Default is 3,600.', '', 'Integer number', '');

$_tipsdb['sslSessionTicketKeyFile'] = new DAttrHelp("SSL Session Ticket Key File", 'Allows the SSL Ticket Key to be created/maintained by an administrator. The file must be 48 bytes long. If this option is left empty, the load balancer  will generate and rotate its own set of keys. <br/><br/>IMPORTANT: To maintain forward secrecy, it is strongly recommended to change the key every <b>SSL Session Ticket Lifetime</b>  seconds. If this cannot be done, it is recommended to leave this field empty.', '', 'Path', '');

$_tipsdb['sslSessionTicketLifetime'] = new DAttrHelp("SSL Session Ticket Lifetime (secs)", 'This value determines how long a session ticket will be valid before a renegotiation is required. Default is 3,600.', '', 'Integer number', '');

$_tipsdb['sslSessionTickets'] = new DAttrHelp("Enable Session Tickets", 'Enables session tickets. If &quot;Not Set&quot;, the server will use openSSL&#039;s default ticket.', '', 'Select from radio box', '');

$_tipsdb['statDir'] = new DAttrHelp("Statistics Output Directory", 'The directory where the Real-Time Stats report file will be written. The default directory is <b>/tmp/lshttpd/</b> .', 'During server operation, the .rtreport file will be written to every second.  To avoid unnecessary disk writes, set this to a RAM Disk.<br/>The .rtreport file can be used with 3rd party monitoring software to track server health.', '绝对路径', '');

$_tipsdb['staticReqPerSec'] = new DAttrHelp("静态请求/秒", '指定每秒可处理的来自单个IP的静态内容请求数量（无论与该IP之间建立了多少个连接）。<br/><br/>当达到此限制时，所有后来的请求将被延滞到下一秒。 对于动态内容请求的限制与本限制无关。 每个客户端的请求限制可以在服务器或虚拟主机级别设置。 虚拟主机级别的设置将覆盖服务器级别的设置。', '[安全] 受信任的IP或子网不受影响。', '无符号整数', '');

$_tipsdb['statuscode'] = new DAttrHelp("状态码", '指定外部重定向响应状态码。 如果状态码在300和399之间，可以指定&quot;目标URI&quot;。', '', '选择', '');

$_tipsdb['suffix'] = new DAttrHelp("Suffix", 'Specifies the script file suffixes that will be handled by this  script handler. Suffixes must be unique.', 'The server will automatically add a special MIME type (&quot;application/x-httpd-[suffix]&quot;) for the first  suffix in the list. For example, MIME type &quot;application/x-httpd-php53&quot; will be added  for suffix &quot;php53&quot;. Suffixes after the first need to set up in the &quot;MIME设置&quot; settings.<br/>Though we list suffixes in this field, the script handlers use MIME types, not suffixes,  to decide which scripts to handle. <br/> Only specify the suffixes you really need.', 'Comma delimited list with period &quot;.&quot; character prohibited.', '');

$_tipsdb['swappingDir'] = new DAttrHelp("交换目录", '指定交换文件的存放目录。 服务器在chroot模式启动时，该路径相对于新的根目录， 否则，它相对于真正的根目录。<br/><br/>Litespeed使用自己的虚拟内存 以降低系统的内存使用量。虚拟内存和磁盘交换会用来存储大的请求内容和 动态响应。交换目录应设置在有足够剩余空间的磁盘上。', '[性能建议] 将交换目录设置在一个单独的磁盘上，或者增加最大读写缓冲区大小以避免交换。', '绝对路径', '');

$_tipsdb['templateFile'] = new DAttrHelp("Template File", 'Specifies the path to the configuration file of this template.  The file must be located within $SERVER_ROOT/conf/templates/ with a &quot;.conf&quot; filename. If the file you designate does not exist, after trying to save the template  an error will appear with the link &quot;CLICK TO CREATE&quot;. This link will generate  a new empty template file. When you delete the template, the entry will be  removed from your configurations, but the actual template config file will not be deleted.', '', 'path', '');

$_tipsdb['templateFileRef'] = new DAttrHelp("File Name Used In Template", 'Specifies a path for the file to be used for member virtual hosts.   Variable $VH_NAME or $VH_ROOT must appear in the path so  each member virtual host will have its own file.', '', 'string', '');

$_tipsdb['templateName'] = new DAttrHelp("Template Name", 'A unique name for the template.', '', '', '');

$_tipsdb['templateVHAliases'] = new DAttrHelp("Aliases", 'Specifies alternate names for the virtual host. All possible hostnames and IP addresses should be added to this list. The wildcard characters * and ? are allowed in the name. Append :<port> for web sites not on port 80. <br/><br/>Aliases will be used in the following situations: <ol>   <li>To match the hostname in the Host header when processing a   request.</li>   <li>To populate domain name/alias configurations for add-ons    like FrontPage or AWstats.</li>   <li>To configure listener-to-virtual host mappings based on the virtual host template.</li> </ol>', '', 'Comma-separated list of domain names.', '');

$_tipsdb['templateVHConfigFile'] = new DAttrHelp("Instantiated VHost Config File", 'Specifies the location of the config file generated when you instantiate a member virtual host.  Variable $VH_NAME must appear in the path so each virtual host will have its own file. Must be located under  $SERVER_ROOT/conf/vhosts/. This config file will be created only after you move a member vhost out of the template  through instantiation.', '$VH_NAME/vhconf.conf is recommended for easy management.', 'String with $VH_NAME variable and .conf suffix', '');

$_tipsdb['templateVHDocRoot'] = new DAttrHelp("Document Root", 'Specifies the unique path for each member virtual host&#039;s document root.   Variable $VH_NAME or $VH_ROOT must appear in the path so  each member virtual host will have its own document root.', '', 'path with $VH_NAME or $VH_ROOT variable', '$VH_ROOT/public_html/ or $SERVER_ROOT/$VH_NAME/public_html.');

$_tipsdb['templateVHDomain'] = new DAttrHelp("Domain", 'Specifies the main domain name for this member virtual host.  If left blank, the virtual host name will be used. This should be a fully qualified domain name, but you can use an IP address as well.  It is recommended to append :<port> for web sites not on port 80.  For configurations containing domain names, this domain can be referenced  with variable $VH_DOMAIN. <br/><br/>This domain name will be used in the following situations: <ol>   <li>To match the hostname in the Host header when processing a   request.</li>   <li>To populate domain name configurations for add-ons    like FrontPage or AWstats.</li>  <li>To configure listener-to-virtual host mappings based on the virtual host template.</li> </ol>', '', 'domain name', '');

$_tipsdb['templateVHName'] = new DAttrHelp("Virtual Host Name", 'A unique name for this virtual host. This name must be unique among all  template member virtual hosts and standalone virtual hosts. Inside a directory  path configuration, this name can be referenced by the variable $VH_NAME.<br/><br/>If a standalone virtual host with the same name is also configured, then the member virtual host configuration will be ignored.', '', '', '');

$_tipsdb['templateVHRoot'] = new DAttrHelp("Default Virtual Host Root", 'Specifies the default root directory for member virtual hosts using this template.  Variable $VH_NAME must appear in the path. This will allow each member template  to be automatically assigned a separate root directory based on its name.', '', 'path', '');

$_tipsdb['toggleDebugLog'] = new DAttrHelp("Toggle Debug Logging", 'Toggle Debug Logging toggles the value of &quot;调试级别&quot; between NONE and HIGH.  As debug logging has an impact on performance and can fill up the hard drive quickly, so &quot;调试级别&quot; should usually be set to NONE on a production server.  This feature can be used instead to turn debug logging on and off quickly  in order to debug a problem on a production server. Debug logging turned on or  off in this way will not change anything shown in your server configurations.', '&quot;Toggle Debug Logging&quot; will only work if &quot;日志级别&quot;  is set to DEBUG.   Important! Debug logging includes detailed information for each  request and response. Active debug logging will severely degrade service performance and potentially saturate disk space in a very short time. This feature should only be  used for a short period of time when trying to diagnose server issues.', '', '');

$_tipsdb['totalInMemCacheSize'] = new DAttrHelp("小文件缓存总大小", '指定分配用于缓存/服务小静态文件的总内存。', '', '无符号整数', '');

$_tipsdb['totalMMapCacheSize'] = new DAttrHelp("总MMAP缓存大小", '指定分配用于缓存/服务中等大小静态文件的总内存。', '', '无符号整数', '');

$_tipsdb['umask'] = new DAttrHelp("umask", '设置CGI进程默认的umask。 通过 man 2 umask命令了解详细信息。这也可作为外部应用程序&quot;umask&quot;的默认值。', '', '数值有效范围为[000] - [777]。', '');

$_tipsdb['uploadPassByPath'] = new DAttrHelp("Pass Upload Data by File Path", 'Specify whether or not to pass upload file data by path. If enabled, file path along with  some other information is sent to backend handler instead of file itself when uploading.  This saves on CPU resources and file transfer time but requires some updates to  backend to implement. If disabled, file content will be transferred to backend handler,  request body is still parsed to files.', ' Enable this to speed up file upload processing if backward compatibility is not an issue.', 'Select from radio box', '');

$_tipsdb['uploadTmpDir'] = new DAttrHelp("Temporary File Path", 'Temporary directory where files being uploaded to server will be stored  while request body parser is working. Default value is /tmp/lshttpd/.', '', 'Absolute path or path starting with $SERVER_ROOT (for Server and VHost levels) or $VH_ROOT (for VHost levels).', '');

$_tipsdb['uploadTmpFilePermission'] = new DAttrHelp("Temporary File Permissions", 'Determines file permissions used for files stored in temporary directory.  Server level setting is global, can be overridden at VHost level.', '', '3 digits octet number. Default value is 666.', '');

$_tipsdb['uri'] = new DAttrHelp("URI", '指定此context下的URI。这个URI应该以&quot;/&quot;开始。 如果一个URI以&quot;/&quot;结束，那么该context将包含这个URI下的所有下级URI。', '', 'URI', '');

$_tipsdb['useIpInProxyHeader'] = new DAttrHelp("使用报头中的客户端IP", '指定是否将在HTTP请求报头中的X-Forwarded-For参数列出的IP地址，用于 所有的IP地址相关的功能，包括 连接/带宽限制、访问控制和IP地理定位。<br/><br/>如果你的Web服务器放置在负载均衡器或代理服务器之后，此功能非常有用。 如果您选择了“仅限受信任的IP”，只有在请求来自受信任IP时，X-Forwarded-For 中的IP才会被使用。受信任IP可在服务器级别的&quot;允许列表&quot;中定义。', '', '选项', '');

$_tipsdb['useSendfile'] = new DAttrHelp("使用sendfile()", '指定是否使用sendfile()系统调用来服务静态文件。静态文件 可以用四种不同的方式服务：内存缓存、内存映射缓存、直接读写和 sendfile()。 尺寸小于&quot;最大小文件缓存&quot;的文件将使用内存缓存服务。尺寸大于该限制、但小于 &quot;最大MMAP文件大小&quot;的文件，将使用内存映射缓存服务。 尺寸大于&quot;最大MMAP文件大小&quot;的文件将通过直接读写或sendfile() 服务。Sendfile()是一个“零拷贝”系统调用，可在服务非常大的 文件时大大减少CPU的使用率。Sendfile()需要一个优化的网卡内核驱动， 因此可能不适合某些小厂商的网络适配器。', '', '布尔值', '');

$_tipsdb['userDBCacheTimeout'] = new DAttrHelp("用户数据库缓存超时", '指定多久检查一次后端用户数据库变更。 在缓存中每个条目都有一个时间戳。 当缓存日期超过指定的超时时间时，将检查后端数据库是否有变化。 如果没有，时间戳将被重置为当前时间，否则会将新的数据载入。 服务器重载和平滑重启会立即清除缓存。', '[性能建议] 如果后端数据库不经常发生变更，设置较长的缓存时间来获得更好的性能。', '单元', '');

$_tipsdb['userDBLocation'] = new DAttrHelp("用户数据库地址", '指定用户数据库的地址。 对于类型为Password File的数据库，应设置为包含用户名/密码的展平文件的路径。 您可以在WebAdmin控制台中点击文件名来进行修改。<br/><br/>用户文件的每一行包含一个用户名，后面加上冒号，在跟上加密的密码，后面可选择添加冒号和用户所属组名。 多个组名通过逗号分隔。如果组信息在用户数据库中指定，那么组数据库将不被检查。<br/><br/>例如: <blockquote><code>john:HZ.U8kgjnMOHo:admin,user</code></blockquote><br/><br/>对于类型为LDAP的数据库，应该设置用于查询用户信息的LDAP URL。对于每个有效的用户，存储在LDAP服务器中的认证数据 应至少包含用户ID和用户密码。当根据HTTP认证报头中的信息通过指定URL进行LDAP查询请求时，应当有且仅有一个记录被返回。&quot;$k&quot;必须在URL中的过滤部分指定并且将用用户名来替代。用户密码属性名必须在查询中返回。用户密码属性名由&quot;密码属性名&quot;指定。组信息可以使用&quot;Member-of 属性&quot;来指定（可选）。<br/><br/>例如: 用户至少要在LDAP中通过以下对象类定义：uidObject, simpleSecurityObject和organizationalRole。可以使用如下URL：<br/><blockquote><code>ldap://localhost/ou=UserDB,dc=example,dc=com???(&(objectClass=*)(uid=$k))</code></blockquote>', '[安全建议] 建议在文档树以外保存用户密码文件。 如果用户密码文件被放置在文档树以内，只需要使用&quot;.ht&quot;作为文件名开头， 如.htuser，来防止被当做静态文件输出。LiteSpeed Web服务器不输出前缀为“.ht”的文件。', '到用户数据库文件的路径或LDAP URL（RFC 2255）。', '');

$_tipsdb['userDBMaxCacheSize'] = new DAttrHelp("用户数据库最大缓存大小", '指定用户数据库的最大缓存大小。 最近访问的用户认证信息会被缓存在内存中以提供最佳性能。', '[性能建议] 由于更大的缓存会消耗更多的内存，更高的值可能会也可能不会提供更好的性能。 请根据您的用户数据库大小和网站使用情况来设定一个合适的大小。', '无符号整数', '');

$_tipsdb['vaction'] = new DAttrHelp("Actions - Virtual Host", 'This field shows buttons to disable, enable, or restart the virtual host.   Actions taken on one virtual host do not affect the rest of the web server.', 'It is good idea to disable a virtual host temporarily when updating its content.', '', '');

$_tipsdb['vdisable'] = new DAttrHelp("Disable", 'The Disable action stops a running virtual host. New requests will not be accepted, but requests being processed will finish as usual.', '', '', '');

$_tipsdb['venable'] = new DAttrHelp("Enable", 'The Enable action starts up a stopped virtual host.   This allows new requests to be accepted.', '', '', '');

$_tipsdb['verifyDepth'] = new DAttrHelp("Verify Depth", ' Specifies how deeply a certificate should be verified before  determining that the client does not have a valid certificate. The default is &quot;1&quot;.', '', 'Select from drop down list', '');

$_tipsdb['vhEnableGzip'] = new DAttrHelp("Enable Compression", 'Specifies whether to enable GZIP compression for this virtual host.  This setting is only effective when GZIP compression is enabled at the server level.  Compression settings are configured at the server level (Tuning > GZIP).', '', 'Select from radio box', '');

$_tipsdb['vhMaxKeepAliveReq'] = new DAttrHelp("最大Keep-Alive请求数", '指定通过keep-alive(永久)连接服务的最大请求数量。当该限制值达到时连接将被断开。你可以为不同虚拟主机设置不同的数值。这个数值不能超过服务器级别的&quot;最大持续连接请求数&quot;限制值。', '[性能建议] 设置为一个合理的高数值。设置为1或比1更小的值将禁用keep-alive连接。', '无符号整数', '');

$_tipsdb['vhModuleUrlFilters'] = new DAttrHelp("Virtual Host Module Context", 'It&#039;s a centralized place to customize module settings for virtual host contexts. Settings for a context URI will override the virtual host or the server level settings.', '', '', '');

$_tipsdb['vhModules'] = new DAttrHelp("Virtual Host Modules", 'Virtual Host module configuration data is, by default inherited from the Server module configuration.   The Virtual Host Modules are limited to the HTTP level hooks.', '', '', '');

$_tipsdb['vhName'] = new DAttrHelp("虚拟主机名", '为虚拟主机的唯一名称。建议使用虚拟主机的域名作为虚拟主机名。 虚拟主机名参数可以使用$VH_NAME变量来引用。', '', '文本', '');

$_tipsdb['vhRoot'] = new DAttrHelp("虚拟主机根", '指定虚拟主机的根目录。 注：这<b>不是</b>目录根。 建议将所有与该虚拟主机相关的文件 (像日志文件，html文件，CGI脚本等)都放置在这个目录下。 虚拟主机根参数可以使用$VH_ROOT变量来引用。', '[性能建议] 在不同的硬盘放置不同的虚拟主机。', '路径2', '');

$_tipsdb['vhSmartKeepAlive'] = new DAttrHelp("智能Keep-Alive", '指定是否为虚拟主机启用智能Keep-Alive。这个选项仅在当&quot;智能持续连接&quot;启用并且&quot;最大Keep-Alive请求数&quot;大于1的时候生效。', '[性能建议] 为访问繁忙的网站启用此项。', '布尔值', '');

$_tipsdb['vhaccessLog_fileName'] = new DAttrHelp("File Name", 'The access log filename.', ' Put access log file on a separate disk.', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT, $VH_ROOT.', '');

$_tipsdb['vhadminEmails'] = new DAttrHelp("管理员邮箱", '指定这个虚拟主机管理员的电子邮箱地址。', '', 'Comma separated list of email addresses', '');

$_tipsdb['vhlog_fileName'] = new DAttrHelp("File Name", 'Specifies the path for the log file.', ' Place the log file on a separate disk.', 'Filename which can be an absolute path or a relative path to $SERVER_ROOT, $VH_ROOT.', '');

$_tipsdb['vhlog_logLevel'] = new DAttrHelp("日志级别", '指定日志记录级别。可用级别（从高到低）为ERROR,  WARNING, NOTICE, INFO, 和 DEBUG。 只有当消息等级高于或与当前设置相同时才被记录。 如果您希望将此设置为DEBUG，您也需要设置服务器日志级别为DEBUG。 调试的级别只能在服务器级别通过&quot;调试级别&quot;控制。', '[性能建议] 除非&quot;调试级别&quot;设置为NONE以外的日志级别, 否则DEBUG级别不会对性能产生任何影响，推荐采用。', '选项', '');

$_tipsdb['viewlog'] = new DAttrHelp("Server Log Viewer", 'The Server Log Viewer is a convenient tool for browsing the  current server log to check for errors or problems.  The log viewer  searches the server log file in blocks for the specified log level.    The default block size is 20KB. You can use the Begin,   End, Next, and Prev buttons to navigate a large log file.', 'The size of a dynamically generated page is limited by &quot;动态回应主内容最大大小&quot;.   So if the block is too big, the page might be truncated.', '', '');

$_tipsdb['virtualHostMapping'] = new DAttrHelp("Virtual Host Mappings", 'Specifies the relationship between the listener and virtual hosts.  Listeners and virtual hosts are associated by domain names.   An HTTP request will be routed to a virtual host with a matching domain name.   One listener can map to multiple virtual hosts for different domain names.   One virtual host can also be mapped from different listeners.  One listener can allow one catchall virtual host with the domain name value &quot;*&quot;.   When there is no explicitly matched domain name in the listener&#039;s mapping,  the listener will forward the request to that catchall virtual host.', ' Only add necessary mappings. If the listener is mapped   to only one virtual host, then only set up a catchall mapping &quot;*&quot;.', '', '');

$_tipsdb['virtualHostName'] = new DAttrHelp("Virtual Host", 'Specifies the name of a virtual host.', '', 'Select from drop down list', '');

$_tipsdb['vname'] = new DAttrHelp("Name - Virtual Host", 'The unique name that identifies this virtual host. This is the &quot;虚拟主机名&quot;  you specified when setting up this virtual host.', '', '', '');

$_tipsdb['vreload'] = new DAttrHelp("Restart - Virtual Host", 'The Restart action causes the web server to load the newest configuration  for this virtual host. Requests being processed will finish with the old configuration.  The new configuration will only apply for new requests. All changes to a virtual host  can be applied on the fly this way.', '', '', '');

$_tipsdb['vstatus'] = new DAttrHelp("Status - Virtual Host", 'The current status of a virtual host.   The status can be: Running, Stopped, Restart Required,   or Running - Removed from Configuration.  <ul>     <li>Running means the virtual host is loaded and in service.</li>     <li>Stopped means the virtual host is loaded but not in service (disabled). </li>     <li> Restart Required means this is a newly added virtual host and          the server has not yet loaded its configuration. </li>     <li>Running - Removed from Configuration means the virtual host has been deleted      from the server&#039;s configuration but it is still in service. </li> </ul>', '', '', '');

$_tipsdb['wsaddr'] = new DAttrHelp("Address", 'A unique socket address used by the WebSocket backend.  IPv4 sockets, IPv6 sockets, and Unix Domain Sockets (UDS) are supported.  IPv4 and IPv6 sockets can be used for communication over the network.  UDS can only be used when the WebSocket backend resides on the same machine as the server.', ' If the WebSocket backend runs on the same machine,  UDS is preferred. If you have to use an IPv4 or IPv6 socket,  set the IP address to localhost or 127.0.0.1, so the WebSocket backend  is inaccessible from other machines.<br/> Unix Domain Sockets generally provide higher performance than IPv4 or IPv6 sockets.', 'IPv4 or IPV6 address:port or UDS://path', '127.0.0.1:5434 <br/>UDS://tmp/lshttpd/php.sock.');

$_tipsdb['wsuri'] = new DAttrHelp("URI", 'Specifies the URI(s) that will use this WebSocket backend. Traffic to  this URI will only be forwarded to the WebSocket backend when it contains  a WebSocket upgrade request. <br/><br/>Traffic without this upgrade request will automatically be forwarded to the  Context that this URI belongs to. If no Context exists for this URI,  LSWS will treat this traffic as though it is accessing a static context with  the location $DOC_ROOT/URI.', '', 'The URI can be a plain URI (starting with &quot;/&quot;) or a Perl-compatible  regular expression URI (starting with &quot;exp:&quot;). If a plain URI ends with a &quot;/&quot;,  then this WebSocket backend will include all sub-URIs under this URI.', 'Using the WebSocket proxy in conjunction with a Context  allows you to serve different kinds of traffic in different ways  on the same page, thus optimizing performance. You can send WebSocket  traffic to the WebSocket backend, while setting up a static context so  that LSWS can serve the page&#039;s static content, or an LSAPI context so LSWS  will serve PHP content (both of which LSWS does more efficiently  than the WebSocket backend).');


$_tipsdb['EDTP:UDBgroup'] = array('If you enter group information here, the group DB will not be checked.','You can enter multiple groups, use comma to separate. Space will be treated as part of a group name.');

$_tipsdb['EDTP:accessControl_allow'] = array('You can set up access control at server, virtual host and context levels. If there is access control  at server level, the virtual host rules will be applied after the server rules are satisfied.','Input format can be an IP like 192.168.0.2, a sub-network like 192.168.*, or a subnet/netmask like 192.168.128.5/255.255.128.0.','If you have trusted IP or sub-network, then you must specify them in allowed list by adding a trailing &quot;T&quot; such as  192.168.1.*T. Trusted IP or sub-network is not limited by connection/throttling limit.');

$_tipsdb['EDTP:accessControl_deny'] = array('To deny access from certain address, put &quot;ALL&quot; in allowed list, and put subnet or IP in denied  list. To allow only certain IP or subnet to access the site, put &quot;ALL&quot; in denied list and specify the address in the allowed list.');

$_tipsdb['EDTP:accessDenyDir'] = array('Enter a full path if you want to deny access for specific directory; entering a path followed by * will disable all the sub directories.','Path can be either absolute or relative to $SERVER_ROOT, use comma to separate.','If both <b>Follow Symbolic Link</b> and <b>Check Symbolic Link</b> are enabled, symbolic links will be checked against the denied directories.');

$_tipsdb['EDTP:accessLog_fileName'] = array('Log file path can be an absolute path or relative to $SERVER_ROOT.');

$_tipsdb['EDTP:aclogUseServer'] = array('When required, you can disable access logging for this virtual host to save on disk i/o.');

$_tipsdb['EDTP:adminEmails'] = array('You can enter multiple admin emails: use comma to separate.');

$_tipsdb['EDTP:adminOldPass'] = array('For security reasons, if you forget the admin password, you will be unable to change it from the WebAdmin Console.  Please use the following shell command instead:  <br><br> /usr/local/lsws/admin/misc/admpass.sh.  <br><br> This script will remove all entered admin user IDs and overwrite them with a single admin user.');

$_tipsdb['EDTP:allowBrowse'] = array('Static context can be used to map a URI to a directory either outside document root or within it. The directory  can be absolute path or relative to document root(default), $VH_ROOT or $SERVER_ROOT.','Check &quot;Accessible&quot; will allow browsing static files in this context. You may want to disable it to prevent viewing static  files, for e.g. when you update the content.');

$_tipsdb['EDTP:autoFix503'] = array('When you enable <b>Auto Fix 503 Error</b>, the monitor process will automatically launch a new server process and service will resume instantly if a crash is detected.');

$_tipsdb['EDTP:backlog'] = array('Local applications can be started by the web server. In this case, you need to specify the path, backlog and number of instances.');

$_tipsdb['EDTP:cgi_path'] = array('A CGI context can be used to specify a directory only contains CGI scripts. Path can be absolute path or relative to $SERVER_ROOT, $VH_ROOT  or $DOC_ROOT(default). Path and URI must be ended with &quot;/&quot; for a cgi-bin directory.','If only a specific script is needed in that directory, it is recommended to create a CGI context for that script only. In this case, path and  URI need not be a directory. For e.g., path can be ~/myapp/myscript.pl, URI can be /myapp/myscript.pl. All other files will not be served as CGI.');

$_tipsdb['EDTP:checkSymbolLink'] = array('Check-Symbolic-Link control will take effect only if Follow-Symbolic-Link is turned on.  This controls whether symbolic links are checked against Access Denied Directories.');

$_tipsdb['EDTP:compressibleTypes'] = array('Compressible Types is a list of MIME types that are compressible, separated by commas. You can use wildcard &quot;*&quot; for MIME types, like */*, text/*. You  can put &quot;!&quot; in front to exclude certain types. The order of the list is important if you use &quot;!&quot;. For e.g., a list like &quot;text/*, !text/css, !text/js&quot; will  compress all text file except for css and js.');

$_tipsdb['EDTP:ctxType'] = array('<b>Static</b> context can be used to map a URI to a directory either outside document root or within it.','<b>Java Web App</b> context is used to automatically import a predefined Java Application in an AJPv13 compilant Java servlet engine.','<b>Servlet</b> context is used to import a specific servlet under a web application.','<b>Fast CGI</b> context is a mount point of Fast CGI application.','<b>LiteSpeed SAPI</b> context can be used to associate a URI with an LSAPI application.','<b>Proxy</b> context enables this virtual host to serve as a transparant reverse proxy server to an external web server or application server.','<b>CGI</b> context can be used to specify a directory only contains CGI scripts.','<b>Load Balancer</b> context can be used to assign a different cluster for that context.','<b>Redirect</b> context can set up an internal or external redirect URI.','<b>Rack/Rails</b> context is specifically used for Rack/Rails applications.','<b>Module handler</b> context is a mount point of hander type modules.');

$_tipsdb['EDTP:docRoot'] = array('Set up your document root here, which can be absolute path or relative to $SERV_ROOT or $VH_ROOT','Document root is referred as $DOC_ROOT in this virtual host, which can be used in other path configuration.');

$_tipsdb['EDTP:domainName'] = array('Enter all the domains that you want this listener to respond to. Use comma &quot;,&quot; to separate individual domain.','You can choose only one virtual host to handle all unspecified domains, put &quot;*&quot; in domains.');

$_tipsdb['EDTP:enableDynGzipCompress'] = array('Dynamic GZIP compression control will be effective only if GZIP Compression is enabled.');

$_tipsdb['EDTP:enableExpires'] = array('Expires can be set at the Server/Virtual Host/Context level. Lower level settings will override higher  level settings. In terms of overwrite priority: <br><br> Context Level > Virtual Host Level > Server Level <br><br>');

$_tipsdb['EDTP:errURL'] = array('You can set up customized error pages for different error codes.');

$_tipsdb['EDTP:expiresByType'] = array('Expires By Type will override default settings. Each entry is in the format of &quot;MIME-type=A|Mseconds&quot; with no space in between. You can input multiple entries  separated by comma.');

$_tipsdb['EDTP:expiresDefault'] = array('Expires syntax, &quot;A|Mseconds&quot; means after base time (A or M) plus the specified time in seconds, the file will expire. &quot;A&quot; means client access time, &quot;M&quot; means file  modified time. You can override this default setting by different MIME types: A86400 means the file will expire after 1 day based on client access time.','Here are some common numbers: 1 hour = 3600 sec, 1 day = 86400 sec, 1 week = 604800 sec, 1 month = 2592000 sec, 1 year = 31536000 sec.');

$_tipsdb['EDTP:extAppAddress'] = array('Address can be IPv4 socket address &quot;IP:PORT&quot;, like 192.168.1.3:7777 and localhost:7777 or Unix domain socket address &quot;UDS://path&quot; like UDS://tmp/lshttpd/myfcgi.sock.','UDS is chrooted in chroot environment.','For local applications, Unix domain socket is preferred due to security and better performance. If you have to use IPv4 socket, set the IP part  to localhost or 127.0.0.1, thus the application is inaccessible from other machines.');

$_tipsdb['EDTP:extAppName'] = array('Give a name that easy to remember, other places will refer to this app by its name.');

$_tipsdb['EDTP:extAppType'] = array('You can set up external Fast CGI application and AJPv13 (Apache JServ Protocol v1.3) compatible servlet engine.');

$_tipsdb['EDTP:extWorkers'] = array('Load balancing workers must be previously defined.','Available ExtApp Types are fcgi(Fast CGI App), lsapi(LSAPI App), servlet(Servlet/JSP Engine), proxy(Web Server).','Different types of external applications can be mixed in one load balancing cluster.');

$_tipsdb['EDTP:externalredirect'] = array('Set up redirect URI here. If it is an external redirect, you can specify the status code. Internal  redirect has to start with &quot;/&quot;, external redirect can either start with &quot;/&quot; or with &quot;http(s)://&quot;.');

$_tipsdb['EDTP:fcgiapp'] = array('Fast CGI context is a mount point of Fast CGI application. The Fast CGI Application must be pre-defined at server level or virtual host level.');

$_tipsdb['EDTP:followSymbolLink'] = array('If Follow-Symbolic-Link is enabled, you can still disable it at virtual host level.');

$_tipsdb['EDTP:gzipCompressLevel'] = array('GZIP Compression level ranges from 1 (Minimum) to 9 (Maximum).');

$_tipsdb['EDTP:hardLimit'] = array('Set concurrent connection Limits coming from one client (per IP address). This helps against DoS attack.');

$_tipsdb['EDTP:indexUseServer'] = array('You can use default server level settings for index files or use your own.','You can use your settings in addition to the server level settings.','You can disable index files by choosing not to use server level settings and leaving vhost level settings blank.','You can enable/disable &quot;auto index&quot; at the context level.');

$_tipsdb['EDTP:javaServletEngine'] = array('If the servlet engine runs on a different machine, it is recommended to make a copy of webapps directory locally. Otherwise you must put the  files in a common accessible network drive, which may affect performance.');

$_tipsdb['EDTP:javaWebApp_location'] = array('Java web app context is used to automatically import a predefined Java Application in an AJPv13 compilant Java servlet engine, the  servlet engine should be set up in external app section (either server or virtual host level).','Location is the directory that contains web application files, which includes WEB-INF/ sub directory.','The web server will automatically import configuration file of web application, which usually is WEB-INF/web.xml under the driectory specified by &quot;location&quot;.');

$_tipsdb['EDTP:listenerIP'] = array('Select an IP address from the list, if you don&#039;t specify a particular address, the system will bind to all the available IP address on this machine.');

$_tipsdb['EDTP:listenerName'] = array('Give listener a name that is easy to understand and remember.');

$_tipsdb['EDTP:listenerPort'] = array('Input a unique port number on this IP for this listener. Only super user (root) can use ports lower than 1024. Port 80 is the default HTTP port; port  443 is the default HTTPS port.');

$_tipsdb['EDTP:listenerSecure'] = array('Selecting &quot;Yes&quot; for <b>Secure</b> will make this listener use https. You must then configure this further in SSL settings.');

$_tipsdb['EDTP:logUseServer'] = array('If you select &quot;Yes&quot; for <b>Use Server&#039;s Log</b>, the log will be written to the server file set up at the server level.');

$_tipsdb['EDTP:log_enableStderrLog'] = array('Stderr Log is located in the same directory as the Server Log. If enabled, all External Application output to stderr will be logged in this file.');

$_tipsdb['EDTP:log_fileName'] = array('Log file path can be an absolute path or relative to $SERVER_ROOT.');

$_tipsdb['EDTP:log_rollingSize'] = array('A new log file will be created if current log file exceeds the rolling size. File size is in bytes and can be in multiple input formats: 10240, 10K or 1M.');

$_tipsdb['EDTP:maxCGIInstances'] = array('Limits resources that a CGI program can use. This helps against DoS attacks.','Max CGI Instances controls how many CGI processes the web server can launch.');

$_tipsdb['EDTP:maxReqHeaderSize'] = array('Numbers can be represented as 10240, 10K or 1M.');

$_tipsdb['EDTP:mime'] = array('MIME settings can be edited from the previous page. You can specify the mime configuration file location which can be either be an absolute path or relative  to $SERVER_ROOT.');

$_tipsdb['EDTP:procSoftLimit'] = array('Process soft/hard limit controls how many processes are allowed for one user. This includes all the processes spawned by CGI application. OS level limit is used if not set.','Set to 0 or empty will use operation system default value for all soft/hard limits.','The soft limit is the value that the kernel enforces for the corresponding resource. The hard limit acts as a ceiling for the soft limit');

$_tipsdb['EDTP:proxyWebServer'] = array('Proxy context enables this virtual host serving as a transparent reverse proxy server to an external web server or application server.','External web server must be pre-defined under External App at server or virtual host level.');

$_tipsdb['EDTP:rails_location'] = array('Rack/Rails context is for easy configuration of running Rack/Rails application. You  only need to specify the root location of your rack/rails application in the &quot;Location&quot; field.');

$_tipsdb['EDTP:realm'] = array('A Context can be protected with a predefined realm, which is set up in the virtual host security section. Optionally, an alternative name and  additional requirements can be specified.');

$_tipsdb['EDTP:realmName'] = array('Define your HT Access realm here, this can be used for contexts.');

$_tipsdb['EDTP:restrained'] = array('Turn on Restrained in a shared hosting enviroment.');

$_tipsdb['EDTP:rewriteMapLocation'] = array('Enter URI for location. URI must start with &quot;/&quot;.');

$_tipsdb['EDTP:rubyBin'] = array('<b>Ruby Path</b> is the absolute path of a ruby executable. For e.g., /usr/local/bin/ruby.');

$_tipsdb['EDTP:serverName'] = array('The user and group setting of the server process cannot be modified. This was set up during installation. You have to reinstall to change this option.');

$_tipsdb['EDTP:servletEngine'] = array('If the servlet engine runs on a different machine, it is recommended to make a copy of webapps directory locally. Otherwise you must put the  files in a common accessible network drive, which may affect performance.');

$_tipsdb['EDTP:shHandlerName'] = array('Except CGI, other handlers need to be predefined in the &quot;External App&quot; section.');

$_tipsdb['EDTP:shType'] = array('Script handler can be a CGI, an FCGI app, a module handler, a Servlet engine, or a proxy to Web server.');

$_tipsdb['EDTP:sndBufSize'] = array('Numbers can be represented as 10240, 10K or 1M.','If send/receive buffer size is 0, OS default TCP buffer size will be used.');

$_tipsdb['EDTP:softLimit'] = array('Set IP level throttle limit here. The number will be rounded up to 4K units. Set to &quot;0&quot; to disable throttling.','Number of connections can temporarily exceed Soft Limit during Grace Period as long as under Hard Limit. After Grace Period, if it is  still above Soft Limit, then no more connections will be allowed from that IP for time of Banned Period.');

$_tipsdb['EDTP:sslProtocol'] = array('&quot;Yes&quot; must be selected for <b>Secure</b> in General > Address Settings.','For SSL versions and encryption levels, please select all you want to accept.');

$_tipsdb['EDTP:sslSessionCache'] = array('Session caching allows a client to resume a session within a set amount of time without having to re-perform an SSL handshake. You can do this by assigning clients a  session ID using  <b>Enable Session Cache</b>, or by creating and using session tickets.');

$_tipsdb['EDTP:sslSessionTicketKeyFile'] = array('Session tickets will be rotated automatically if the tickets are being generated by the server. If using the <b>SSL Session Ticket Key File</b> option to create and manage your own session tickets, you must be rotate the tickets yourself using a cron job.');

$_tipsdb['EDTP:swappingDir'] = array('Swapping directory is recommended to be placed on a local disk such as /tmp. Network drive should be avoided at all cost. Swap  will be when configured memory i/o buffer is exhausted.');

$_tipsdb['EDTP:users'] = array('Group DB will be checked only if the user in the user DB does not contain group information..','Use comma to separate multiple users.');

$_tipsdb['EDTP:vhRoot'] = array('All directories must pre-exist. This web interface will not create the directory for you. If you are creating a new virtual host, you  can create an empty root directory and set it up from the beginning; or you can copy the &quot;Example&quot; virtual root that shipped with the package to this virtual  host root and modify it.','Virtual host root ($VH_ROOT) can be absolute path or relative to $SERVER_ROOT.');

$_tipsdb['EDTP:vhaccessLog_fileName'] = array('Log file path can be an absolute path or a relative path to $SERVER_ROOT, $VH_ROOT.');

$_tipsdb['EDTP:vhadminEmails'] = array('You can enter multiple admin emails, separated by commas.');

$_tipsdb['EDTP:vhlog_fileName'] = array('Log file path can be an absolute path or relative to $SERVER_ROOT, $VH_ROOT.','If you want to set Log Level to DEBUG, you must set the server log level to DEBUG as well. The level of  debugging is controlled by Server DEBUG Level. Use DEBUG only if you have to as it has a large impact on server performance and can fill up disk space quickly.');

$_tipsdb['EDTP:virtualHostName'] = array('Select the virtual hosts that you want to map to this listener.','If you have not set up the virtual host you want to map, you can skip this step and come back later.');
