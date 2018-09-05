CC=g++
LFSFLAGS= $(shell getconf LFS_CFLAGS) -D_GLIBCXX_USE_CXX11_ABI=0 -std=gnu++11
INCLUDEPATH= -I../../util/ -I./ -I../../../include  -I../ -I../../ -I./ModSecurity/headers/
CFLAGS= -fPIC -fvisibility=hidden -g  -Wall -c -D_REENTRANT $(INCLUDEPATH)  $(LFSFLAGS)


OS := $(shell uname)
ifeq ($(OS), Darwin)
        LDFLAGS= -fPIC -g -undefined dynamic_lookup  -Wall  -lxml2 -lcurl $(LFSFLAGS) -shared
else
        LDFLAGS= -fPIC -pg -O2  -g -Wall  -lxml2 -lcurl $(LFSFLAGS) -shared
endif

SOURCES = mod_security.cpp
$(shell ./dllibmodsecurity.sh >&2)
$(shell rm *.o )

OBJECTS=$(SOURCES:.cpp=.o)
TARGET  = mod_security.so

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(INCLUDEPATH) $(OBJECTS) $(shell pwd)/ModSecurity/src/.libs/libmodsecurity.a -o $@  $(LDFLAGS)

.cpp.o:
	$(CC) $(CFLAGS)  $< -o $@
        
clean:
	rm *.o

