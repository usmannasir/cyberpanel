modulesdir=$(prefix)/modules

modules_LTLIBRARIES=mod_lua.la
mod_lua_la_LDFLAGS= -module -avoid-version -shared

AM_CPPFLAGS= -I$(top_srcdir)/include -I$(top_srcdir)/src -I$(LUA_INCLUDES)

mod_lua_la_METASOURCES= AUTO

mod_lua_la_SOURCES=lsluaengine.cpp edluastream.cpp lsluaapi.cpp \
    lsluasession.cpp lsluaheader.cpp lsluashared.cpp lsluaregex.cpp modlua.cpp

#noinst_HEADERS =
