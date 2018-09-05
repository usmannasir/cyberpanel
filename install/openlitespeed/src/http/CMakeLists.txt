cmake_minimum_required(VERSION 2.8)

#include_directories ("/usr/include/openssl")

cmake_policy(SET CMP0002 OLD)


########### next target ###############

SET(http_STAT_SRCS
   moduserdir.cpp
   contextnode.cpp
   phpconfig.cpp
   pipeappender.cpp
   awstats.cpp
   rewriterulelist.cpp
   throttlecontrol.cpp
   rewriteengine.cpp
   rewritemap.cpp
   rewriterule.cpp
   reqstats.cpp
   hotlinkctrl.cpp
   contextlist.cpp
   urimatch.cpp
   expiresctrl.cpp
   stderrlogger.cpp
   htauth.cpp
   userdir.cpp
   authuser.cpp
   httplistenerlist.cpp
   httpvhostlist.cpp
   htpasswd.cpp
   httphandler.cpp
   httplogsource.cpp
   accesslog.cpp
   accesscache.cpp
   clientinfo.cpp
   clientcache.cpp
   httprange.cpp
   connlimitctrl.cpp
   denieddir.cpp
   httpserverconfig.cpp
   httpextconnector.cpp
   statusurlmap.cpp
   contexttree.cpp
   httpcgitool.cpp
   httpsignals.cpp
   handlertype.cpp
   handlerfactory.cpp
   staticfilecachedata.cpp
   staticfilecache.cpp
   cacheelement.cpp
   httpcache.cpp
   chunkoutputstream.cpp
   chunkinputstream.cpp
   httplog.cpp
   httpmime.cpp
   sendfileinfo.cpp
   httpcontext.cpp
   httpserverversion.cpp
   vhostmap.cpp
   eventdispatcher.cpp
   staticfilehandler.cpp
   reqhandler.cpp
   httpvhost.cpp
   httpresourcemanager.cpp
   ntwkiolink.cpp
   httpmethod.cpp
   httpver.cpp
   httpstatuscode.cpp
   httpstatusline.cpp
   httpheader.cpp
   smartsettings.cpp
   httplistener.cpp
   httpresp.cpp
   httpreq.cpp
   httpsession.cpp
   iptogeo.cpp
   iptoloc.cpp
   moov.cpp
   #requestvars.cpp
   hiostream.cpp
   hiohandlerfactory.cpp
   httprespheaders.cpp
   l4handler.cpp
   httpaiosendfile.cpp
   serverprocessconfig.cpp
   httpstats.cpp
   reqparser.cpp
)

add_library(http STATIC ${http_STAT_SRCS})

target_link_libraries(http -lpcre -lz -lcrypt -lssl -lcrypto -lexpat)

