####### kdevelop will overwrite this part!!! (begin)##########
noinst_LIBRARIES = libextensions.a

AM_CPPFLAGS =  -I$(top_srcdir)/openssl/include/ -I$(top_srcdir)/include -I$(top_srcdir)/src

libextensions_a_METASOURCES = AUTO

libextensions_a_SOURCES = loadbalancer.cpp localworkerconfig.cpp localworker.cpp pidlist.cpp iprocessortimer.cpp httpextprocessor.cpp \
  extrequest.cpp extworker.cpp extconn.cpp extworkerconfig.cpp l4conn.cpp \
  cgi/lscgid.cpp cgi/suexec.cpp cgi/cgidreq.cpp cgi/cgidconfig.cpp cgi/cgidworker.cpp cgi/cgidconn.cpp \
  fcgi/fcgienv.cpp fcgi/fcgiappconfig.cpp fcgi/fcgiapp.cpp fcgi/fcginamevaluepair.cpp fcgi/fcgiconnection.cpp fcgi/fcgirecord.cpp \
  jk/jkajp13.cpp jk/jworker.cpp jk/jworkerconfig.cpp jk/jconn.cpp \
  proxy/proxyconfig.cpp proxy/proxyworker.cpp proxy/proxyconn.cpp \
  registry/extappregistry.cpp registry/railsappconfig.cpp\
  lsapi/lsapiworker.cpp lsapi/lsapireq.cpp lsapi/lsapiconn.cpp lsapi/lsapiconfig.cpp 

####### kdevelop will overwrite this part!!! (end)############
#noinst_HEADERS = localworkerconfig.h localworker.h loadbalancer.h
