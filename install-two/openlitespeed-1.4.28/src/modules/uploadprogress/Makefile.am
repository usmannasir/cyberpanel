modulesdir=$(prefix)/modules

modules_LTLIBRARIES=uploadprogress.la
uploadprogress_la_LDFLAGS= -module -avoid-version -shared
AM_CPPFLAGS =  -I$(top_srcdir)/openssl/include/ -I$(top_srcdir)/include -I$(top_srcdir)/src

uploadprogress_la_METASOURCES= AUTO

uploadprogress_la_SOURCES=uploadprogress.cpp

#noinst_HEADERS = 

