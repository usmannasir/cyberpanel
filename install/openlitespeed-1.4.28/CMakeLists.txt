cmake_minimum_required(VERSION 2.8)

Project(openlitespeed)
INCLUDE( ${PROJECT_SOURCE_DIR}/CMakeModules/common.cmake)

set(openlitespeed_MAJOR_VERSION 1)
set(openlitespeed_MINOR_VERSION 4)
set(openlitespeed_PATCH_VERSION 0)
set(openlitespeed_VERSION
  ${FOOBAR_MAJOR_VERSION}.${FOOBAR_MINOR_VERSION}.${FOOBAR_PATCH_VERSION})

SET(CMAKE_INCLUDE_CURRENT_DIR ON)

include_directories( include ${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/include/)
link_directories( ${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/lib/)

SET (CMAKE_C_COMPILER         "/usr/bin/clang")
SET (CMAKE_CXX_COMPILER       "/usr/bin/clang++")

#set(MY_CMAKE_WARNING_FLAG  " -Wall -Wextra -Wno-unused-parameter")
#set(MY_CMAKE_WARNING_FLAG  " -Wall -Wextra -Wno-unused-parameter -fsanitize=address -fno-omit-frame-pointer")
#set(MY_CMAKE_WARNING_FLAG  " -Wall -Wextra -Wno-unused-parameter -fno-omit-frame-pointer")
set(MY_CMAKE_WARNING_FLAG  " -Wall -Wextra -Wno-unused-parameter -fsanitize=address -fsanitize-recover=address -fno-omit-frame-pointer")
#set(MY_CMAKE_WARNING_FLAG  " -Wall -Wextra -Wno-unused-parameter")
set(MY_CMAKE_POOL_FLAG  " -DPOOL_TESTING -DUSE_VALGRIND")
#set(MY_CMAKE_POOL_FLAG  " -DPOOL_TESTING")

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS}  ${MY_CMAKE_WARNING_FLAG} ${MY_CMAKE_POOL_FLAG}")
#set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} ${MY_CMAKE_WARNING_FLAG}")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}  ${MY_CMAKE_WARNING_FLAG} ${MY_CMAKE_POOL_FLAG}")
#set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} ${MY_CMAKE_WARNING_FLAG}")


configure_file(${CMAKE_CURRENT_SOURCE_DIR}/src/config.h.cmake ${CMAKE_CURRENT_BINARY_DIR}/src/config.h)

SET(CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/CMakeModules)
find_package(ZLIB REQUIRED)
##find_package(LibLdap REQUIRED)
find_package(PCRE REQUIRED)
find_package(EXPAT REQUIRED)
#find_package(OpenSSL REQUIRED)


execute_process( COMMAND ${PROJECT_SOURCE_DIR}/dlossl.sh )
execute_process( COMMAND ${PROJECT_SOURCE_DIR}/src/modules/pagespeed/dlpsol.sh )

##########################################################################################
#If you want to link libUnitTest++, just un-comment out the following commands
#AND YOU NEED TO INSTALL it to the directory /src/test/unittest-cpp/UnitTest++/
add_definitions(-DRUN_TEST)
set(libUnitTest  libUnitTest++.a)
##########################################################################################
#If you want to use BoringSSL, just un-comment out the following commands
#AND YOU NEED TO HAVE THE files ready in openlitespeed/ssl
#You can run the dlbssl.sh to make them ready
set(BSSL_ADD_LIB  libdecrepit.a)
##########################################################################################
#If you want to use Brotli Compression, just un-comment out the following commands
#set(BROTLI_ADD_LIB  libbrotlidec.a libbrotlienc.a libbrotlicommon.a)
#add_definitions(-DUSE_BROTLI)
##########################################################################################
#If you want to use IP2Location, just un-comment out the following commands
set(IP2LOC_ADD_LIB  libIP2Location.a)
add_definitions(-DUSE_IP2LOCATION)
##########################################################################################


add_definitions(-DTEST_OUTPUT_PLAIN_CONF)
#add_definitions(-DLS_VG_DEBUG)
#add_definitions(-DDEBUG_POOL)
add_definitions(-DOPENSSL_NO_CXX)

execute_process( COMMAND getconf LFS_CFLAGS
            OUTPUT_VARIABLE  LFS_CFLAGS )

add_definitions( ${LFS_CFLAGS} )
add_definitions(-DUSE_UDNS)

add_subdirectory(src)
add_subdirectory(test)
