cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(fcgi_STAT_SRCS
   fcgienv.cpp
   fcgiappconfig.cpp
   fcgiapp.cpp
   fcginamevaluepair.cpp
   fcgiconnection.cpp
   fcgirecord.cpp
)

add_library(fcgi STATIC ${fcgi_STAT_SRCS})


########### install files ###############




#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = libfcgi.a
#
#INCLUDES = $(all_includes)
#
#libfcgi_a_METASOURCES = AUTO
#
#libfcgi_a_SOURCES = fcgienv.cpp fcgiappconfig.cpp fcgiapp.cpp fcginamevaluepair.cpp fcgiconnection.cpp fcgirecord.cpp 
#
#
#EXTRA_DIST = fcgirecord.cpp fcgirecord.h fcgiconnection.cpp fcgiconnection.h fcginamevaluepair.cpp fcginamevaluepair.h fcgiapp.cpp fcgiapp.h fcgidef.h fcgiappconfig.cpp fcgiappconfig.h fcgienv.cpp fcgienv.h 
#
######## kdevelop will overwrite this part!!! (end)############
