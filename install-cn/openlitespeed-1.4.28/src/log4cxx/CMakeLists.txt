cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(log4cxx_STAT_SRCS
   appendermanager.cpp
   fileappender.cpp
   logrotate.cpp
   patternlayout.cpp
   loggingevent.cpp
   ilog.cpp
   bench.cpp
   layout.cpp
   appender.cpp
   logger.cpp
   level.cpp
   logsession.cpp
   tmplogid.cpp
)

add_library(log4cxx STATIC ${log4cxx_STAT_SRCS})


