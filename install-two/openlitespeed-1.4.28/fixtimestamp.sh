#When using git clone to get the source code, the timestamp will be lost.
#then when run make, it will cause re-config issue.

#!/bin/sh


touch  aclocal.m4
sleep 2

touch Makefile.in
touch src/Makefile.in
touch src/edio/Makefile.in
touch src/extensions/Makefile.in
touch src/http/Makefile.in
touch src/spdy/Makefile.in
touch src/log4cxx/Makefile.in
touch src/main/Makefile.in
touch src/socket/Makefile.in
touch src/sslpp/Makefile.in
touch src/ssi/Makefile.in
touch src/lsiapi/Makefile.in
touch src/modules/Makefile.in
touch src/shm/Makefile.in
touch src/modules/cache/Makefile.in
sleep 2 

touch configure
touch src/config.h.in
