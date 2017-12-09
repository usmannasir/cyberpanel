cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(jk_STAT_SRCS
   jkajp13.cpp
   jworker.cpp
   jworkerconfig.cpp
   jconn.cpp
)

add_library(jk STATIC ${jk_STAT_SRCS})


########### install files ###############




#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = libjk.a
#
#INCLUDES = $(all_includes)
#
#libjk_a_METASOURCES = AUTO
#
#libjk_a_SOURCES = jkajp13.cpp jworker.cpp jworkerconfig.cpp jconn.cpp 
#
#
#EXTRA_DIST = jconn.cpp jconn.h jworkerconfig.cpp jworkerconfig.h jworker.cpp jworker.h jkajp13.cpp jkajp13.h 
#
######## kdevelop will overwrite this part!!! (end)############
