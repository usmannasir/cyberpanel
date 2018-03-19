cmake_minimum_required(VERSION 2.8)
INCLUDE( ${PROJECT_SOURCE_DIR}/CMakeModules/common.cmake)

cmake_policy(SET CMP0002 OLD)

########### next target ###############

SET(socket_STAT_SRCS
   gsockaddr.cpp
   hostinfo.cpp
   tcpsockopt.cpp
   tcpserversocket.cpp
   tcpconnection.cpp
   streamsocket.cpp
   serversocket.cpp
   coresocket.cpp
)

add_library(socket STATIC ${socket_STAT_SRCS})


########### install files ###############




#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = libsocket.a
#
#INCLUDES = $(all_includes)
#
#libsocket_a_METASOURCES = AUTO
#
#libsocket_a_SOURCES = gsockaddr.cpp hostinfo.cpp tcpsockopt.cpp tcpserversocket.cpp tcpconnection.cpp streamsocket.cpp serversocket.cpp coresocket.cpp 
#
#
#EXTRA_DIST = coresocket.cpp coresocket.h serversocket.cpp serversocket.h streamsocket.cpp streamsocket.h tcpconnection.cpp tcpconnection.h sockdef.h tcpserversocket.cpp tcpserversocket.h tcpsockopt.cpp tcpsockopt.h hostinfo.cpp hostinfo.h gsockaddr.cpp gsockaddr.h 
#
######## kdevelop will overwrite this part!!! (end)############
