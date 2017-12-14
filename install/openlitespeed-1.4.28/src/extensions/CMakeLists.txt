cmake_minimum_required(VERSION 2.8)

cmake_policy(SET CMP0002 OLD)

add_subdirectory(fcgi)
add_subdirectory(cgi)
add_subdirectory(jk)
add_subdirectory(proxy)
add_subdirectory(registry)
add_subdirectory(lsapi)


########### next target ###############

SET(extensions_STAT_SRCS
   loadbalancer.cpp
   localworkerconfig.cpp
   localworker.cpp
   pidlist.cpp
   iprocessortimer.cpp
   httpextprocessor.cpp
   extrequest.cpp
   extworker.cpp
   extconn.cpp
   extworkerconfig.cpp
   l4conn.cpp
)

add_library(extensions STATIC ${extensions_STAT_SRCS})


########### install files ###############




#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = libextensions.a
#
#INCLUDES = $(all_includes)
#
#libextensions_a_METASOURCES = AUTO
#
#libextensions_a_SOURCES = loadbalancer.cpp localworkerconfig.cpp localworker.cpp pidlist.cpp iprocessortimer.cpp httpextprocessor.cpp extrequest.cpp extworker.cpp extconn.cpp extworkerconfig.cpp 
#
#SUBDIRS = fcgi cgi jk proxy registry lsapi 
#
#EXTRA_DIST = extworkerconfig.cpp extworkerconfig.h extconn.cpp extconn.h extworker.cpp extworker.h extrequest.cpp extrequest.h httpextprocessor.cpp httpextprocessor.h iprocessortimer.cpp iprocessortimer.h pidlist.cpp pidlist.h localworker.cpp localworker.h localworkerconfig.cpp localworkerconfig.h loadbalancer.cpp loadbalancer.h 
#
######## kdevelop will overwrite this part!!! (end)############
#noinst_HEADERS = localworkerconfig.h localworker.h loadbalancer.h
