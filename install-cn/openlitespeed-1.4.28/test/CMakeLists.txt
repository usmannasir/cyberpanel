cmake_minimum_required(VERSION 2.8)





########### next target ###############



SET(unittest_STAT_SRCS
   edio/bufferedostest.cpp
   edio/multiplexertest.cpp
#   extensions/fcgistartertest.cpp
   http/expirestest.cpp
   http/rewritetest.cpp
   http/httprequestlinetest.cpp
   http/httprangetest.cpp
   http/denieddirtest.cpp
   http/statusurlmaptest.cpp
   http/contexttreetest.cpp
   http/httpmimetest.cpp
   http/httpcgitooltest.cpp
   http/chunkostest.cpp
   http/chunkistest.cpp
   http/httplistenerstest.cpp
   http/httpvhostlisttest.cpp
   http/httpreqtest.cpp
   http/httpreqheaderstest.cpp
   http/httpbuftest.cpp
   http/httpheadertest.cpp
   http/datetimetest.cpp
   http/reqparsertest.cpp
   socket/hostinfotest.cpp
   socket/tcpsockettest.cpp
   socket/coresockettest.cpp
   util/pcregextest.cpp
   util/ghashtest.cpp
   util/linkedobjtest.cpp
   util/gzipbuftest.cpp
   util/brotlibuftest.cpp
   util/vmembuftest.cpp
   util/gpathtest.cpp
   util/poolalloctest.cpp
   util/xmlnodetest.cpp
   util/accesscontroltest.cpp
   util/loopbuftest.cpp
   util/logfiletest.cpp
   util/stringmaptest.cpp
   util/httpfetchtest.cpp
   util/partitioninfotest.cpp
   util/gmaptest.cpp
   util/ahotest.cpp
   util/stringtooltest.cpp
   util/gpointerlisttest.cpp
   util/objarraytest.cpp
   util/objpooltest.cpp
   util/radixtreetest.cpp
   spdy/huffmantest.cpp
   spdy/hpacktest.cpp
   spdy/spdyzlibfiltertest.cpp
   spdy/spdyconnectiontest.cpp
   spdy/dummiostream.cpp
   lsiapi/moduledata.cpp
   lsiapi/moduletimertest.cpp
   lsiapi/lsiapihookstest.cpp
   lsiapi/envhandler.cpp
   lsiapi/moduleconf.cpp
   lsr/ls_ahotest.cpp
   lsr/ls_confparsertest.cpp
   lsr/ls_base64test.cpp
   lsr/ls_buftest.cpp
   lsr/ls_dlinkqtest.cpp
   lsr/ls_hashtest.cpp
   lsr/ls_linktest.cpp
   lsr/ls_loopbuftest.cpp
   lsr/ls_maptest.cpp
   lsr/ls_md5test.cpp
   lsr/ls_objarraytest.cpp
   lsr/ls_objpooltest.cpp
   lsr/ls_pcregtest.cpp
   lsr/ls_pooltest.cpp
   lsr/ls_ptrlisttest.cpp
   lsr/ls_sha1test.cpp
   lsr/ls_strtest.cpp
   lsr/ls_strlisttest.cpp
   lsr/ls_strtooltest.cpp
   lsr/ls_xpooltest.cpp
   thread/pthreadworkqueuetest.cpp
   thread/threadtest.cpp
   thread/workcrewtest.cpp
   shm/shmbaselrutest.cpp
   shm/shmxtest.cpp
   unittest_main.cpp
)

link_directories(${PROJECT_SOURCE_DIR}/ssl/ /usr/local/lib ${PROJECT_SOURCE_DIR}/test/unittest-cpp/UnitTest++)

add_executable(ols_unittest 
    ../src/httpdtest.cpp
    ../src/modules/prelinkedmods.cpp
    ../src/main/configctx.cpp
    ${unittest_STAT_SRCS}
)


# add_executable(ctbench
#     modules/prelinkedmods.cpp
#     http/contexttreebench.cpp
#     httpdtest.cpp
# )

#add_executable(luatest
#modules/prelinkedmods.cpp
#lua/luatest.cpp
#httpdtest.cpp
#)

# add_executable(shmlru_test
# shm/shmlru_test.c
# modules/prelinkedmods.cpp
# httpdtest.cpp
# ${util_SRCS}
# ${lsr_SRCS}
# ${thread_SRCS}
# ${http_STAT_SRCS}
# )

# add_executable(shmtest
# shm/testshmapi.cpp
# shm/shmtest.cpp
# shm/lsshmdebug.cpp
# shm/testshm.cpp
# shm/testshmreg.cpp
# shm/testshmhash.cpp
# modules/prelinkedmods.cpp
# httpdtest.cpp
# ${lsr_SRCS}
# ${thread_SRCS}
# ${util_SRCS}
# )









# NOTE: When creating a new directory, the order it is placed in this list
# matters.  Everything listed depends on things listed AFTER it, though
# it won't depend on everything after it.  Inter-dependency may be fixed
# by listing one directory twice, though this isn't recommended.
# So for example, if edio depends on your new directory, your directory
# should be listed AFTER edio.  PLEASE TRY TO KEEP THIS NEAT!
SET( unittestlib
    modgzip lsiapi main http lsiapi spdy ssi
    registry cgi fcgi jk extensions lsapi proxy
    edio socket sslpp lsshm thread log4cxx GeoIP adns
    -Wl,--whole-archive util lsr -Wl,--no-whole-archive
    udns pthread rt ${CMAKE_DL_LIBS} ${libUnitTest} libssl.a libcrypto.a ${BSSL_ADD_LIB}
    ${BROTLI_ADD_LIB} ${IP2LOC_ADD_LIB})

target_link_libraries(ols_unittest ${unittestlib} )

# target_link_libraries(ctbench ${litespeedlib} )

# target_link_libraries(shmtest ${litespeedlib} )

# target_link_libraries(shmlru_test ${litespeedlib} )

add_executable(ls_lfqueuetest
lsr/ls_lfqueuetest.c
${lsr_SRCS}
)
target_link_libraries(ls_lfqueuetest lsr pthread pcre )

add_executable(ls_lfstacktest
lsr/ls_lfstacktest.cpp
../src/util/misc/profiletime.cpp
${lsr_SRCS}
${test_SRCS}
)
target_link_libraries(ls_lfstacktest lsr pthread pcre )

add_executable(ls_llmqtest
lsr/ls_llmqtest.c
${lsr_SRCS}
)
target_link_libraries(ls_llmqtest lsr pthread pcre )

add_executable(ls_locktest
lsr/ls_locktest.cpp
${lsr_SRCS}
)
target_link_libraries(ls_locktest lsr pthread pcre )

add_executable(ls_stacktest
lsr/ls_stacktest.cpp
../src/util/misc/profiletime.cpp
${lsr_SRCS}
${test_SRCS}
)
target_link_libraries(ls_stacktest lsr pthread pcre )

add_executable(ls_thrsafetest
lsr/ls_thrsafetest.cpp
${lsr_SRCS}
)
target_link_libraries(ls_thrsafetest lsr pthread pcre )

add_executable(ls_valgrindtest
lsr/ls_valgrindtest.c
${lsr_SRCS}
)
target_link_libraries(ls_valgrindtest lsr pthread pcre )


