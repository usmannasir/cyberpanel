cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(proxy_STAT_SRCS
   proxyconfig.cpp
   proxyworker.cpp
   proxyconn.cpp
)

add_library(proxy STATIC ${proxy_STAT_SRCS})


########### install files ###############




#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = libproxy.a
#
#INCLUDES = $(all_includes)
#
#libproxy_a_METASOURCES = AUTO
#
#libproxy_a_SOURCES = proxyconfig.cpp proxyworker.cpp proxyconn.cpp 
#
#
#EXTRA_DIST = proxyconn.cpp proxyconn.h proxyworker.cpp proxyworker.h proxyconfig.cpp proxyconfig.h 
#
######## kdevelop will overwrite this part!!! (end)############
