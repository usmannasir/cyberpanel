cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(ssi_STAT_SRCS
   ssiengine.cpp
   ssiconfig.cpp
   ssiruntime.cpp
   ssiscript.cpp
   ../http/requestvars.cpp
)

add_library(ssi STATIC ${ssi_STAT_SRCS})
