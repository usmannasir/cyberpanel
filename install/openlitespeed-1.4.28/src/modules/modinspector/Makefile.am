modulesdir=$(prefix)/modules

modules_LTLIBRARIES=modinspector.la
modinspector_la_LDFLAGS= -module -avoid-version -shared

AM_CPPFLAGS =  -I$(top_srcdir)/openssl/include/ -I$(top_srcdir)/include -I$(top_srcdir)/src
modinspector_la_METASOURCES= AUTO

modinspector_la_SOURCES=modinspector.cpp

#noinst_HEADERS = 

