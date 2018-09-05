CC=g++
OS := $(shell uname)
MACHINE_TYPE := $(shell uname -m)
LFSFLAGS= $(shell getconf LFS_CFLAGS) -D_GLIBCXX_USE_CXX11_ABI=0

INCLUDE_ARCH=
PSOLPATH=

ifeq ($(OS), Darwin)
        LDFLAGS= -fPIC -g -undefined dynamic_lookup  -Wall $(LFSFLAGS) -shared
	INCLUDE_ARCH=arch/mac/ia32
	$(shell echo Sorry, pagespeed does not support MAC OS)

else
	ifeq ($(MACHINE_TYPE), x86_64)
	    INCLUDE_ARCH = arch/linux/x64
	    PSOLPATH = $(shell pwd)/psol/lib/Release/linux/x64/
	    CFLAGS= -fPIC -fvisibility=hidden -g -O2 -Wall -c -D_REENTRANT $(LFSFLAGS)
	else
	    INCLUDE_ARCH = arch/linux/ia32
	    PSOLPATH = $(shell pwd)/psol/lib/Release/linux/ia32/
	    CFLAGS= -fPIC -fvisibility=hidden -g -O2 -Wall -c -D_REENTRANT $(LFSFLAGS) -march=$(MACHINE_TYPE)
	endif
	LDFLAGS= -fPIC -g -O2 -Wall $(LFSFLAGS) -shared
endif

INCLUDEFILES =-I. -I../.. -I.. -I../../util -I../../../  -I../../../include \
          -I./psol/include \
          -I./psol/include/url \
          -I./psol/include/third_party/chromium/src \
	      -I./psol/include/third_party/protobuf/src \
	      -I./psol/include/third_party/protobuf/src/src \
	      -I./psol/include/third_party/google-sparsehash/src/ \
	      -I./psol/include/third_party/re2/src/ \
	      -I./psol/include/out/Debug/obj/gen/protoc_out/instaweb/ \
	      -I./psol/include/third_party/apr/src/include/ \
	      -I./psol/include/third_party/google-sparsehash/gen/$(INCLUDE_ARCH)/include/ \
	      -I./psol/include/third_party/apr/gen/$(INCLUDE_ARCH)/include/ \
	      -I./psol/include/third_party/css_parser/src/ \
	      -I./psol/include/third_party/aprutil/src/include/ \
	      -I./psol/include/third_party/aprutil/gen/$(INCLUDE_ARCH)/include/

	      
	      
SOURCES =pagespeed.cpp log_message_handler.cpp ls_message_handler.cpp \
        ls_server_context.cpp \
        ls_rewrite_driver_factory.cpp \
        ls_caching_headers.cpp \
        ls_rewrite_options.cpp  \
        ls_base_fetch.cpp \
        ls_uamatcher.cpp
        
DLPSOL:= $(shell ./dlpsol.sh 1)
$(shell rm *.o ../../util/*.o)

OBJECTS=$(SOURCES:.cpp=.o)
TARGET  = modpagespeed.so

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(OBJECTS) $(PSOLPATH)pagespeed_automatic.a $(INCLUDEFILES) -o $@  $(LDFLAGS)

.cpp.o:
	$(CC)  $(INCLUDEFILES) $(CFLAGS)  $< -o $@
        
clean:
	rm *.o ../../util/*.o
