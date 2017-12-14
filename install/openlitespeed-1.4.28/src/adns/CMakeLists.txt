
cmake_minimum_required(VERSION 2.8)
cmake_policy(SET CMP0002 OLD)



########### next target ###############

SET(adns_STAT_SRCS 
    adns.cpp
)

add_library(adns STATIC ${adns_STAT_SRCS} )
