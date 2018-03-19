
cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(util_STAT_SRCS
   httpfetchdriver.cpp
   httpfetch.cpp
   linkobjpool.cpp
   pidfile.cpp
   hashdatacache.cpp
   keydata.cpp
   tlinklist.cpp
   rlimits.cpp
   duplicable.cpp
   gfactory.cpp
   fdpass.cpp
   pcregex.cpp
   autostr.cpp
   staticobj.cpp
   pool.cpp
   hashstringmap.cpp
   ghash.cpp
   emailsender.cpp
   guardedapp.cpp
   crashguard.cpp
   iconnection.cpp
   dlinkqueue.cpp
   connpool.cpp
   compressor.cpp
   gzipbuf.cpp
   brotlibuf.cpp
   vmembuf.cpp
   blockbuf.cpp
   stringlist.cpp
   semaphore.cpp
   refcounter.cpp
   gpointerlist.cpp
   linkedobj.cpp
   objpool.cpp
   gpath.cpp
   poolalloc.cpp
   env.cpp
   xmlnode.cpp
   iovec.cpp
   accesscontrol.cpp
   signalutil.cpp
   loopbuf.cpp
   stringtool.cpp
   tsingleton.cpp
   pcutil.cpp
   daemonize.cpp
   configentry.cpp
   datetime.cpp
   resourcepool.cpp
   linkedqueue.cpp
   httputil.cpp
   radixtree.cpp
   misc/profiletime.cpp
   sysinfo/partitioninfo.cpp
   sysinfo/nicdetect.cpp
   sysinfo/systeminfo.cpp
   ni_fio.c
)

add_library(util STATIC ${util_STAT_SRCS} )

