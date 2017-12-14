cmake_minimum_required(VERSION 2.8)
INCLUDE( ${PROJECT_SOURCE_DIR}/CMakeModules/common.cmake)

cmake_policy(SET CMP0002 OLD)


########### next target ###############

SET(edio_STAT_SRCS
#    eventnotifier.cpp
   reactorindex.cpp
   fdindex.cpp
   kqueuer.cpp
   epoll.cpp
   rtsigio.cpp
   ediostream.cpp
   outputbuf.cpp
   cacheos.cpp
   inputstream.cpp
   bufferedos.cpp
   outputstream.cpp
   flowcontrol.cpp
   iochain.cpp
   multiplexerfactory.cpp
   eventreactor.cpp
   poller.cpp
   multiplexer.cpp
   pollfdreactor.cpp
   lookupfd.cpp
   devpoller.cpp
   aioeventhandler.cpp
   sigeventdispatcher.cpp
   aiooutputstream.cpp
   aiosendfile.cpp
   eventnotifier.cpp
   eventprocessor.cpp
   evtcbque.cpp
)

add_library(edio STATIC ${edio_STAT_SRCS})


########### install files ###############
                 



#original Makefile.am contents follow:

######## kdevelop will overwrite this part!!! (begin)##########
#noinst_LIBRARIES = libedio.a
#
#INCLUDES = $(all_includes)
#
#libedio_a_METASOURCES = AUTO
#
#libedio_a_SOURCES = reactorindex.cpp fdindex.cpp kqueuer.cpp epoll.cpp rtsigio.cpp ediostream.cpp outputbuf.cpp cacheos.cpp inputstream.cpp bufferedos.cpp outputstream.cpp flowcontrol.cpp iochain.cpp multiplexerfactory.cpp eventreactor.cpp poller.cpp multiplexer.cpp pollfdreactor.cpp lookupfd.cpp devpoller.cpp 
#
#
#EXTRA_DIST = devpoller.cpp lookupfd.cpp lookupfd.h pollfdreactor.cpp pollfdreactor.h multiplexer.cpp multiplexer.h poller.cpp poller.h eventreactor.cpp eventreactor.h multiplexerfactory.cpp multiplexerfactory.h iochain.cpp iochain.h flowcontrol.cpp flowcontrol.h outputstream.cpp outputstream.h bufferedos.cpp bufferedos.h inputstream.cpp inputstream.h cacheos.h cacheos.cpp outputbuf.cpp outputbuf.h ediostream.cpp ediostream.h rtsigio.cpp rtsigio.h epoll.cpp epoll.h kqueuer.cpp kqueuer.h devpoller.h fdindex.cpp fdindex.h reactorindex.cpp reactorindex.h 
#
######## kdevelop will overwrite this part!!! (end)############
