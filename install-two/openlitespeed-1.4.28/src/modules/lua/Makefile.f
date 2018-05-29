CC=g++
LFSFLAGS= $(shell getconf LFS_CFLAGS) -D_GLIBCXX_USE_CXX11_ABI=0
CFLAGS= -fPIC -g  -Wall -c -D_REENTRANT  -I../../../include/ -I./ -I../ -I../../  -I/usr/local/include/luajit-2.0/  $(LFSFLAGS)


OS := $(shell uname)
ifeq ($(OS), Darwin)
        LDFLAGS= -fPIC -g -undefined dynamic_lookup  -Wall $(LFSFLAGS) -shared
else
        LDFLAGS= -fPIC -g -Wall $(LFSFLAGS) -shared
endif

SOURCES =lsluaengine.cpp edluastream.cpp lsluaapi.cpp \
    lsluasession.cpp lsluaheader.cpp lsluashared.cpp lsluaregex.cpp modlua.cpp

$(shell rm *.o)

OBJECTS=$(SOURCES:.cpp=.o)
TARGET  = mod_lua.so

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC)  $(OBJECTS) -o $@  $(LDFLAGS)

.cpp.o:
	$(CC) $(CFLAGS) $< -o $@
        
clean:
	rm *.o
