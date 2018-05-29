####### kdevelop will overwrite this part!!! (begin)##########

####### kdevelop will overwrite this part!!! (begin)##########
noinst_LIBRARIES = libmodules.a

# AM_CPPFLAGS =  -I$(top_srcdir)/openssl/include/ -I$(top_srcdir)/include -I$(top_srcdir)/src
AM_CPPFLAGS = -I$(top_srcdir)/openssl/include/ -I$(top_srcdir)/include -I$(top_srcdir)/src

libmodules_a_METASOURCES = AUTO

libmodules_a_SOURCES = modgzip/modgzip.cpp

if HAVE_LIBLUA
SUBDIRS = cache uploadprogress lua modinspector modreqparser
else
SUBDIRS = cache uploadprogress modinspector modreqparser
endif

#noinst_HEADERS = 

