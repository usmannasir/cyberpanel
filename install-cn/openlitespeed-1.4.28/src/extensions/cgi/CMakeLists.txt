cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(cgi_STAT_SRCS
   suexec.cpp
   cgidreq.cpp
   cgidconfig.cpp
   cgidworker.cpp
   cgidconn.cpp
   lscgid.cpp
)

add_library(cgi STATIC ${cgi_STAT_SRCS})


########### install files ###############




#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = libcgi.a
#
#INCLUDES = $(all_includes)
#
#libcgi_a_METASOURCES = AUTO
#
#libcgi_a_SOURCES = suexec.cpp cgidreq.cpp cgidconfig.cpp cgidworker.cpp cgidconn.cpp 
#
#
#EXTRA_DIST = cgidconn.cpp cgidconn.h cgidworker.cpp cgidworker.h cgidconfig.cpp cgidconfig.h cgidreq.cpp cgidreq.h lscgiddef.h suexec.cpp suexec.h 
#
######## kdevelop will overwrite this part!!! (end)############
