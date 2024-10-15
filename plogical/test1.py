import xml.etree.ElementTree as ET

xml_string = '''<?xml version="1.0" encoding="UTF-8"?>
<httpServerConfig>
  <serverName>$HOSTNAME</serverName>
  <workerProcesses>2</workerProcesses>
  <user>nobody</user>
  <group>nobody</group>
  <priority>0</priority>
  <chrootPath>/</chrootPath>
  <enableChroot>0</enableChroot>
  <inMemBufSize>120M</inMemBufSize>
  <swappingDir>/tmp/lshttpd/swap</swappingDir>
  <autoFix503>1</autoFix503>
  <loadApacheConf>1</loadApacheConf>
  <autoReloadApacheConf>0</autoReloadApacheConf>
  <apacheConfFile>/usr/local/lsws/conf/httpd.conf</apacheConfFile>
  <apachePortOffset>0</apachePortOffset>
  <apacheIpOffset>0</apacheIpOffset>
  <phpSuExec>1</phpSuExec>
  <phpSuExecMaxConn>5</phpSuExecMaxConn>
  <mime>$SERVER_ROOT/conf/mime.properties</mime>
  <showVersionNumber>0</showVersionNumber>
  <useIpInProxyHeader>0</useIpInProxyHeader>
  <autoUpdateInterval>86400</autoUpdateInterval>
  <autoUpdateDownloadPkg>1</autoUpdateDownloadPkg>
  <adminEmails>usman@cyberpersons.com</adminEmails>
  <logging>
    <log>
      <fileName>$SERVER_ROOT/logs/error.log</fileName>
      <logLevel>DEBUG</logLevel>
      <debugLevel>0</debugLevel>
      <rollingSize>10M</rollingSize>
      <enableStderrLog>1</enableStderrLog>
      <enableAioLog>1</enableAioLog>
    </log>
    <accessLog>
      <fileName>$SERVER_ROOT/logs/access.log</fileName>
      <logFormat>%h %l %u %t \&quot;%r\&quot; %&gt;s %b \&quot;%{Referer}i\&quot; \&quot;%{User-Agent}i\&quot;</logFormat>
      <rollingSize>10M</rollingSize>
      <keepDays>30</keepDays>
      <compressArchive>1</compressArchive>
    </accessLog>
  </logging>
  <indexFiles>index.html, index.php</indexFiles>
  <htAccess>
    <allowOverride>0</allowOverride>
    <accessFileName>.htaccess</accessFileName>
  </htAccess>
  <expires>
    <enableExpires>1</enableExpires>
    <expiresByType>image/*=A604800, text/css=A604800, application/x-javascript=A604800, application/javascript=A604800</expiresByType>
  </expires>
  <tuning>
    <maxConnections>10000</maxConnections>
    <maxSSLConnections>10000</maxSSLConnections>
    <connTimeout>300</connTimeout>
    <maxKeepAliveReq>1000</maxKeepAliveReq>
    <keepAliveTimeout>5</keepAliveTimeout>
    <sndBufSize>0</sndBufSize>
    <rcvBufSize>0</rcvBufSize>
    <maxReqURLLen>8192</maxReqURLLen>
    <maxReqHeaderSize>16380</maxReqHeaderSize>
    <maxReqBodySize>500M</maxReqBodySize>
    <maxDynRespHeaderSize>8K</maxDynRespHeaderSize>
    <maxDynRespSize>500M</maxDynRespSize>
    <maxCachedFileSize>4096</maxCachedFileSize>
    <totalInMemCacheSize>20M</totalInMemCacheSize>
    <maxMMapFileSize>256K</maxMMapFileSize>
    <totalMMapCacheSize>40M</totalMMapCacheSize>
    <useSendfile>1</useSendfile>
    <useAIO>1</useAIO>
    <AIOBlockSize>4</AIOBlockSize>
    <enableGzipCompress>1</enableGzipCompress>
    <compressibleTypes>text/*,application/x-javascript,application/javascript,application/xml, image/svg+xml</compressibleTypes>
    <enableDynGzipCompress>1</enableDynGzipCompress>
    <gzipCompressLevel>1</gzipCompressLevel>
    <gzipAutoUpdateStatic>1</gzipAutoUpdateStatic>
    <gzipStaticCompressLevel>6</gzipStaticCompressLevel>
    <gzipMaxFileSize>1M</gzipMaxFileSize>
    <gzipMinFileSize>300</gzipMinFileSize>
  </tuning>
  <quic>
    <quicEnable>1</quicEnable>
  </quic>
  <security>
    <fileAccessControl>
      <followSymbolLink>1</followSymbolLink>
      <checkSymbolLink>0</checkSymbolLink>
      <requiredPermissionMask>000</requiredPermissionMask>
      <restrictedPermissionMask>000</restrictedPermissionMask>
    </fileAccessControl>
    <perClientConnLimit>
      <staticReqPerSec>0</staticReqPerSec>
      <dynReqPerSec>0</dynReqPerSec>
      <outBandwidth>0</outBandwidth>
      <inBandwidth>0</inBandwidth>
      <softLimit>10000</softLimit>
      <hardLimit>10000</hardLimit>
      <gracePeriod>15</gracePeriod>
      <banPeriod>300</banPeriod>
    </perClientConnLimit>
    <CGIRLimit>
      <maxCGIInstances>200</maxCGIInstances>
      <minUID>11</minUID>
      <minGID>10</minGID>
      <priority>0</priority>
      <CPUSoftLimit>300</CPUSoftLimit>
      <CPUHardLimit>600</CPUHardLimit>
      <memSoftLimit>1450M</memSoftLimit>
      <memHardLimit>1500M</memHardLimit>
      <procSoftLimit>1400</procSoftLimit>
      <procHardLimit>1450</procHardLimit>
    </CGIRLimit>
    <censorshipControl>
      <enableCensorship>0</enableCensorship>
      <logLevel>0</logLevel>
      <defaultAction>deny,log,status:403</defaultAction>
      <scanPOST>1</scanPOST>
      <uploadTmpDir>/tmp</uploadTmpDir>
      <secAuditLog>$SERVER_ROOT/logs/security_audit.log</secAuditLog>
    </censorshipControl>
    <censorshipRuleSet>
      <name>XSS attack</name>
      <ruleSetAction>log,deny,status:403,msg:'XSS attack'</ruleSetAction>
      <enabled>1</enabled>
    </censorshipRuleSet>
    <accessDenyDir>
      <dir>/</dir>
      <dir>/etc/*</dir>
      <dir>/dev/*</dir>
      <dir>$SERVER_ROOT/conf/*</dir>
      <dir>$SERVER_ROOT/admin/conf/*</dir>
    </accessDenyDir>
    <accessControl>
      <allow>ALL, 127.0.0.1T, 103.21.244.0/22T, 103.22.200.0/22T, 103.31.4.0/22T, 104.16.0.0/12T, 108.162.192.0/18T, 131.0.72.0/22T, 141.101.64.0/18T, 162.158.0.0/15T, 172.64.0.0/13T, 173.245.48.0/20T, 188.114.96.0/20T, 190.93.240.0/20T, 197.234.240.0/22T, 198.41.128.0/17T, 2400:cb00::/32T, 2405:8100::/32T, 2405:b500::/32T, 2606:4700::/32T, 2803:f800::/32T, 2a06:98c0::/29T, 2c0f:f248::/32T, 192.88.134.0/23T, 185.93.228.0/22, 66.248.200.0/22T, 208.109.0.0/22T, 2a02:fe80::/29T</allow>
    </accessControl>
  </security>
  <extProcessorList>
    <extProcessor>
      <type>lsapi</type>
      <name>lsphp5</name>
      <address>uds://tmp/lshttpd/lsphp5.sock</address>
      <maxConns>35</maxConns>
      <env>PHP_LSAPI_CHILDREN=35</env>
      <initTimeout>60</initTimeout>
      <retryTimeout>0</retryTimeout>
      <persistConn>1</persistConn>
      <respBuffer>0</respBuffer>
      <autoStart>3</autoStart>
      <path>$SERVER_ROOT/fcgi-bin/lsphp5</path>
      <backlog>100</backlog>
      <instances>1</instances>
      <priority>0</priority>
      <memSoftLimit>2047M</memSoftLimit>
      <memHardLimit>2047M</memHardLimit>
      <procSoftLimit>400</procSoftLimit>
      <procHardLimit>500</procHardLimit>
    </extProcessor>

    <extProcessor>
      <type>proxy</type>
      <name>docker100</name>
      <address>127.0.0.1:1100</address>
      <maxConns>60</maxConns>
      <pcKeepAliveTimeout>-1</pcKeepAliveTimeout>
      <initTimeout>60</initTimeout>
      <retryTimeout>60</retryTimeout>
      <respBuffer>0</respBuffer>
    </extProcessor>
  </extProcessorList>
</httpServerConfig>'''

# Parse the XML content

root = ET.fromstring(xml_string)

# Find the <extProcessorList> node
ext_processor_list = root.find('extProcessorList')

# Create the new <extProcessor> node
new_ext_processor = ET.Element('extProcessor')
port = '200'

# Add child elements to the new <extProcessor>
ET.SubElement(new_ext_processor, 'type').text = 'proxy'
ET.SubElement(new_ext_processor, 'name').text = f'docker{port}'
ET.SubElement(new_ext_processor, 'address').text = f'127.0.0.1:{port}'
ET.SubElement(new_ext_processor, 'maxConns').text = '35'
ET.SubElement(new_ext_processor, 'pcKeepAliveTimeout').text = '60'
ET.SubElement(new_ext_processor, 'initTimeout').text = '60'
ET.SubElement(new_ext_processor, 'retryTimeout').text = '60'
ET.SubElement(new_ext_processor, 'respBuffer').text = '0'

# Append the new <extProcessor> to the <extProcessorList>
ext_processor_list.append(new_ext_processor)

# Write the updated XML content to a new file or print it out
tree = ET.ElementTree(root)
# tree.write(ConfPath, encoding='UTF-8', xml_declaration=True)
from xml.dom import minidom

rough_string = ET.tostring(root, 'utf-8')
reparsed = minidom.parseString(rough_string)
print(reparsed.toprettyxml(indent="  "))

# Optionally, print the updated XML
# ET.dump(root)
