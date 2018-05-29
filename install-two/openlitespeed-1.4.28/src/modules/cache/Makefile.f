CC=g++
LFSFLAGS= $(shell getconf LFS_CFLAGS) -D_GLIBCXX_USE_CXX11_ABI=0
INCLUDEPATH= -I../../util/ -I./ -I../../../include  -I../ -I../../
CFLAGS= -fPIC -g  -Wall -c -D_REENTRANT $(INCLUDEPATH)  $(LFSFLAGS)


OS := $(shell uname)
ifeq ($(OS), Darwin)
        LDFLAGS= -fPIC -g -undefined dynamic_lookup  -Wall $(LFSFLAGS) -shared
else
        LDFLAGS= -fPIC -pg -O2  -g -Wall $(LFSFLAGS) -shared
endif

SOURCES =cache.cpp cacheentry.cpp cachehash.cpp cachestore.cpp \
        ceheader.cpp dirhashcacheentry.cpp dirhashcachestore.cpp \
        cacheconfig.cpp cachectrl.cpp  \
        cachemanager.cpp shmcachemanager.cpp

$(shell rm *.o )

OBJECTS=$(SOURCES:.cpp=.o)
TARGET  = cache.so

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(INCLUDEPATH) $(OBJECTS)  -o $@  $(LDFLAGS)

.cpp.o:
	$(CC) $(CFLAGS)  $< -o $@
        
clean:
	rm *.o
