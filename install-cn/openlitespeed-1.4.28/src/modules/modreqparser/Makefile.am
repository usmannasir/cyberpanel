modulesdir=$(prefix)/modules

modules_LTLIBRARIES=modreqparser.la
modreqparser_la_LDFLAGS= -module -avoid-version -shared

AM_CPPFLAGS =  -I$(top_srcdir)/include -I$(top_srcdir)/src

modreqparser_la_METASOURCES= AUTO

modreqparser_la_SOURCES=modreqparser.cpp

#noinst_HEADERS = 

