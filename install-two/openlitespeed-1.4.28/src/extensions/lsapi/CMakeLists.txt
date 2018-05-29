cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(lsapi_STAT_SRCS
   lsapiworker.cpp
   lsapireq.cpp
   lsapiconn.cpp
   lsapiconfig.cpp
)

add_library(lsapi STATIC ${lsapi_STAT_SRCS})


########### install files ###############




#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = liblsapi.a
#
#INCLUDES = $(all_includes)
#
#liblsapi_a_METASOURCES = AUTO
#
#liblsapi_a_SOURCES = lsapiworker.cpp lsapireq.cpp lsapiconn.cpp lsapiconfig.cpp 
#
#
#EXTRA_DIST = lsapiconfig.cpp lsapiconfig.h lsapiconn.cpp lsapiconn.h lsapireq.cpp lsapireq.h lsapidef.h lsapiworker.cpp lsapiworker.h 
#
######## kdevelop will overwrite this part!!! (end)############
