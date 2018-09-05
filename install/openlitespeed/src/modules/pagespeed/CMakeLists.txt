cmake_minimum_required(VERSION 2.8)

#set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -Wall -O2 -g")
#set(CMAKE_CSS_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -Wall -O2 -g")

execute_process( COMMAND ${PROJECT_SOURCE_DIR}/src/modules/pagespeed/dlpsol.sh )

execute_process( COMMAND uname -m
                OUTPUT_VARIABLE  MACHINE_TYPE )
string(STRIP ${MACHINE_TYPE} MACHINE_TYPE)

if( "${MACHINE_TYPE}" STREQUAL "x86_64" )
    set(OSVERSION "x64")
else()
    set(OSVERSION "ia32")
endif()

set(PSOL_VER 1.11.33.4)
set(PSOL_LIB ${PROJECT_SOURCE_DIR}/../thirdparty/psol-${PSOL_VER})

include_directories(
                ${PSOL_LIB}/include
                ${PSOL_LIB}/include/url
                ${PSOL_LIB}/include/third_party/apr/src/include
                ${PSOL_LIB}/include/third_party/chromium/src
                ${PSOL_LIB}/include/third_party/protobuf/src/src
                ${PSOL_LIB}/include/third_party/google-sparsehash/src
                ${PSOL_LIB}/include/third_party/re2/src
                ${PSOL_LIB}/include/out/Debug/obj/gen/protoc_out/instaweb
                ${PSOL_LIB}/include/third_party/apr/gen/arch/linux/${OSVERSION}/include
                ${PSOL_LIB}/include/third_party/css_parser/src
                ${PSOL_LIB}/include/third_party/google-sparsehash/gen/arch/linux/${OSVERSION}/include/)

execute_process( COMMAND getconf LFS_CFLAGS
            OUTPUT_VARIABLE  LFS_CFLAGS )

add_definitions( ${LFS_CFLAGS} )

add_library(modpagespeed SHARED  pagespeed.cpp  log_message_handler.cpp
            ls_message_handler.cpp
            ls_server_context.cpp
            ls_rewrite_driver_factory.cpp
            ls_caching_headers.cpp
            ls_rewrite_options.cpp 
            ls_base_fetch.cpp
            ls_uamatcher.cpp
            )

target_link_libraries(modpagespeed ${PSOL_LIB}/lib/Debug/linux/${OSVERSION}/pagespeed_automatic.a)
set_target_properties(modpagespeed PROPERTIES PREFIX "")

