cmake_minimum_required(VERSION 2.8)

SET(modgzip_STAT_SRCS 
modgzip.cpp
)

add_library(modgzip STATIC  ${modgzip_STAT_SRCS})

