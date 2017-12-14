cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(main_STAT_SRCS
   mainserverconfig.cpp
   lshttpdmain.cpp
   serverinfo.cpp
   httpconfigloader.cpp
   httpserver.cpp
   plainconf.cpp
   configctx.cpp
)

add_library(main STATIC ${main_STAT_SRCS})


########### install files ###############




#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = libmain.a
#
#INCLUDES = $(all_includes)
#
#libmain_a_METASOURCES = AUTO
#
#libmain_a_SOURCES = lshttpdmain.cpp serverinfo.cpp httpserverbuilder.cpp \
#	httpserver.cpp
#
#
#EXTRA_DIST = license.cpp license.h httpserver.cpp httpserver.h httpserverbuilder.cpp httpserverbuilder.h serverinfo.cpp serverinfo.h lshttpdmain.cpp lshttpdmain.h timestamp.h
#
######## kdevelop will overwrite this part!!! (end)############
