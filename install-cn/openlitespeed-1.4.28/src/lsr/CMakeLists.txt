
cmake_minimum_required(VERSION 2.8)


########### next target ###############

SET(lsr_STAT_SRCS 
   ls_aho.c
   ls_base64.c
   ls_buf.c
   ls_confparser.c
   ls_crc64.c
   ls_dlinkq.c
   ls_fileio.c
   ls_hash.c
   ls_lfqueue.c
   ls_lfstack.c
   ls_link.c
   ls_llmq.c
   ls_llxq.c
   ls_lock.c
   ls_loopbuf.c
   ls_map.c
   ls_md5.c
   ls_mpscq.c
   ls_objarray.c
   ls_objpool.c
   ls_pcreg.c
   ls_pool.c
   ls_ptrlist.c
   ls_sha1.c
   ls_shm.cpp
   ls_stack.c
   ls_str.c
   ls_strlist.c
   ls_strtool.c
   ls_time.c
   ls_tsstack.c
   ls_xpool.c
   xxhash.c
)

add_library(lsr STATIC ${lsr_STAT_SRCS} )

