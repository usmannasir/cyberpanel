#!/bin/bash
# Build the ModSecurity 3.0.17 adapter paired with CyberPanel OLS 2.5.6.
# Run only inside a disposable native x86_64 Ubuntu/AlmaLinux container.
# Mount writable /work, pinned tarball inputs /dl, and the verified custom
# source archive at /candidate-core (read-only). PLAT is ubuntu, ubuntu26,
# rhel8, rhel9, or rhel10. Outputs are written below /work/out.
# Engine dependencies retain the published 3.0.17 source pins. The adapter
# keeps WAF request/response policies active and bypasses LSCache only when
# response-body inspection explicitly requires a buffered response.
# /dl inputs: official modsecurity-v3.0.17.tar.gz, pcre-8.45.tar.gz,
# pcre2-10.45.tar.gz, libxml2-2.15.3.tar.xz and yajl-2.1.0.tar.gz.
# Each tarball is checked against a literal SHA256 below. Git inputs are
# checked out at exact commits. Preserve build logs and output checksums.
set -euo pipefail
test -f /.dockerenv || { echo "Use a disposable build container" >&2; exit 2; }
test "$(uname -m)" = x86_64 || { echo "Unsupported build architecture" >&2; exit 2; }
JOBS=${JOBS:-8}
export DEBIAN_FRONTEND=noninteractive
# CMake 4 (Ubuntu 26.04) refuses yajl's cmake_minimum_required(2.6); older CMake ignores this.
export CMAKE_POLICY_VERSION_MINIMUM=3.5

PLAT=${PLAT:?set PLAT=ubuntu|ubuntu26|rhel8|rhel9|rhel10}
case $PLAT in
  ubuntu|ubuntu26)
    apt-get update -qq
    apt-get install -y -qq build-essential cmake git autoconf automake libtool pkg-config \
        perl golang-go wget ca-certificates xz-utils python3 flex bison file binutils >/dev/null
    EXTRA_LIBS=""; MMDB_CFLAGS="" ;;
  rhel8|rhel9|rhel10)
    CRB=crb; [ $PLAT = rhel8 ] && CRB=powertools
    dnf -y -q install dnf-plugins-core >/dev/null
    dnf config-manager --set-enabled $CRB
    dnf -y -q install gcc gcc-c++ make cmake git autoconf automake libtool pkgconf-pkg-config perl \
        golang wget ca-certificates xz python3 flex bison file binutils patch tar gzip diffutils which \
        libstdc++-static libxcrypt-devel >/dev/null
    # The published 3.0.15 EL artifacts carry NEEDED librt/libcrypt (EL links without --as-needed).
    EXTRA_LIBS="-lrt -lcrypt"
    # Ubuntu GCC defaults to PIE (position-independent code); EL GCC does not, and
    # libmaxminddb's configure adds no -fPIC of its own (autoconf default CFLAGS + -fPIC).
    MMDB_CFLAGS="-g -O2 -fPIC" ;;
  *) echo "unknown PLAT"; exit 1;;
esac
gcc --version | head -1

W=/work
TP=$W/third-party
mkdir -p $TP/src $TP/include $TP/lib $TP/lib64 $TP/bin
cd $TP

# ---- litespeedtech/third-party (patches + libtool .la shims) -------------------
fetch_git() { # bounded history at exact pinned commit
  if [ ! -d "$1/.git" ]; then mkdir -p "$1"; git -C "$1" init -q; git -C "$1" remote add origin "$2"; fi
  git -C "$1" fetch -q --depth=1 origin "$3"
  git -C "$1" checkout -q -f "$3"
  test "$(git -C "$1" rev-parse HEAD)" = "$3"
}
fetch_git $W/tp-repo https://github.com/litespeedtech/third-party.git 7297c534b844d808fce7ec42798ef2b1f3aa5259
cp -r $W/tp-repo/patches $TP/

check_sha() { echo "$2  $1" | sha256sum -c - ; }

cd $TP/src
# ---- zlib (pinned e3dc0a85) ---------------------------------------------------
fetch_git zlib https://github.com/madler/zlib.git e3dc0a85b7032e98380dec011bc8f2c2ee0d8fca
(cd zlib && CFLAGS="-fPIC -O3" ./configure --prefix=$TP --static && make -j$JOBS && make install)

# ---- BoringSSL (pinned 9fc1c33e + LiteSpeed patches) ---------------------------
# Release (-O3), as recorded in the 3.0.15 artifact DWARF producer strings.
fetch_git boringssl https://github.com/google/boringssl.git 9fc1c33e9c21439ce5f87855a6591a9324e569fd
(cd boringssl && git reset -q --hard && rm -rf build \
  && patch -p1 < $TP/patches/boringssl/bssl_lstls.patch \
  && patch -p1 < $TP/patches/boringssl/bssl_inttypes.patch \
  && sed -i -e "s/-Werror//" CMakeLists.txt \
  && mkdir build && cd build \
  && cmake ../ -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_FLAGS="-fPIC" -DCMAKE_CXX_FLAGS="-fPIC" >/dev/null \
  && make -j$JOBS crypto ssl decrepit \
  && cp crypto/libcrypto.a ssl/libssl.a decrepit/libdecrepit.a $TP/lib/ \
  && cd .. && cp -r include/openssl $TP/include/)

# ---- PCRE 8.45 (linked by name in the OLS CMakeLists) / PCRE2 10.45 -----------
cp /dl/pcre-8.45.tar.gz /dl/pcre2-10.45.tar.gz .
check_sha pcre-8.45.tar.gz 4e6ce03e0336e8b4a3d6c2b70b1c5e18590a5673a98186da90d4f33c23defc09
check_sha pcre2-10.45.tar.gz 0e138387df7835d7403b8351e2226c1377da804e0737db0e071b48f07c9d12ee
tar xzf pcre-8.45.tar.gz && (cd pcre-8.45 && ./configure --prefix=$TP --enable-jit --enable-unicode-properties --enable-utf --with-pic --with-match-limit=100000 --enable-shared=no >/dev/null && make -j$JOBS install >/dev/null)
tar xzf pcre2-10.45.tar.gz && (cd pcre2-10.45 && ./configure --prefix=$TP --enable-jit --enable-pcre2-8 --enable-unicode --with-pic --with-match-limit=100000 --enable-shared=no --enable-static >/dev/null && make -j$JOBS install >/dev/null)

# ---- LuaJIT (pinned 5c8cee3d, third-party submodule revision) ------------------
fetch_git luajit https://github.com/LuaJIT/LuaJIT.git 5c8cee3dffdb3bc6239ecdf48ce9afeb0fb68250
(cd luajit && make -j$JOBS install PREFIX=$TP CFLAGS="-fPIC -O3" >/dev/null)
cp $TP/patches/libtool/libluajit-5.1.la $TP/lib/libluajit-5.1.la
echo "libdir='$TP/lib'" >> $TP/lib/libluajit-5.1.la
ln -sf libluajit-5.1.a $TP/lib/libluajit.a
rm -f $TP/lib/libluajit*.so*

# ---- LMDB (openldap master liblmdb tree = "LMDB 1.0.0: (June 30, 2026)") -------
fetch_git lmdb https://github.com/openldap/openldap.git bf1b579a17e9e3654a786eca14016651dd01af5b
(cd lmdb/libraries/liblmdb && XCFLAGS=-fPIC make -j$JOBS liblmdb.a && cp *.h $TP/include/ && cp liblmdb.a $TP/lib/)
cp $TP/patches/libtool/liblmdb.la $TP/lib/liblmdb.la
echo "libdir='$TP/lib'" >> $TP/lib/liblmdb.la

# ---- curl 7.88.1 (pinned 046209e5) against BoringSSL ---------------------------
fetch_git curl https://github.com/curl/curl.git 046209e561b7e9b5aab1aef7daebf29ee6e6e8c7
# zlib from $TP (the 3.0.15 artifact carries curl with zlib inflate support)
(cd curl && autoreconf -fi >/dev/null 2>&1 && CFLAGS="-fPIC" CPPFLAGS="-I$TP/include" LDFLAGS="-L$TP/lib" LIBS=-lpthread ./configure --prefix=$TP --with-ssl=$TP \
   --with-brotli=no --enable-shared=no --enable-ldap=no --without-nghttp2 --without-nghttp3 --without-libpsl \
   --without-libidn2 --without-zstd --without-librtmp --without-libssh2 >/dev/null && make -j$JOBS >/dev/null && make install >/dev/null)

# ---- libxml2 2.15.3 -----------------------------------------------------------
cp /dl/libxml2-2.15.3.tar.xz .
check_sha libxml2-2.15.3.tar.xz 78262a6e7ac170d6528ebfe2efccdf220191a5af6a6cd61ea4a9a9a5042c7a07
tar xJf libxml2-2.15.3.tar.xz && ln -sfn libxml2-2.15.3 libxml2
(cd libxml2 && CPPFLAGS="-fPIC" ./configure --prefix=$TP --with-python=no --disable-shared --with-lzma=no >/dev/null && make -j$JOBS >/dev/null && make install >/dev/null)

# ---- yajl 2.1.0 ---------------------------------------------------------------
cp /dl/yajl-2.1.0.tar.gz .
check_sha yajl-2.1.0.tar.gz 3fb73364a5a30efe615046d07e6db9d09fd2b41c763c5f7d3bfb121cd5c5ac5a
rm -rf yajl-2.1.0 && tar xzf yajl-2.1.0.tar.gz
# CMake 4 (Ubuntu 26.04) hard-errors on the LOCATION reads in yajl's reformatter/verify
# tool dirs (policy CMP0026 removed). Those are CLI tools, not part of libyajl; skip them there.
if [ "$(cmake --version | awk 'NR==1{split($3,v,".");print v[1]}')" -ge 4 ]; then
  sed -i -E '/ADD_SUBDIRECTORY\((reformatter|verify|test|example|perf)\)/Id' yajl-2.1.0/CMakeLists.txt
fi
(cd yajl-2.1.0 && ./configure -p $TP >/dev/null && cd build && cmake -DCMAKE_INSTALL_PREFIX="$TP" -DCMAKE_C_FLAGS="-fPIC" .. >/dev/null && make -j$JOBS install >/dev/null)
cp $TP/patches/libtool/libyajl.la $TP/lib/libyajl.la
echo "libdir='$TP/lib'" >> $TP/lib/libyajl.la
mv -f $TP/lib/libyajl_s.a $TP/lib/libyajl.a
rm -f $TP/lib/libyajl.so*

# ---- libmaxminddb 1.12.2 (pinned cba618d6) ------------------------------------
fetch_git libmaxminddb https://github.com/maxmind/libmaxminddb.git cba618d6581b7dbe83478c798d9e58faeaa6b582
(cd libmaxminddb && git submodule update -q --init --recursive && ./bootstrap >/dev/null 2>&1 \
  && CPPFLAGS="-I../include" ./configure ${MMDB_CFLAGS:+"CFLAGS=$MMDB_CFLAGS"} --disable-tests --prefix=$TP --enable-shared=no --disable-binaries >/dev/null \
  && make -j$JOBS install >/dev/null && cp src/libmaxminddb.la $TP/lib && cp include/maxminddb_config.h $TP/include)

# ---- libmodsecurity 3.0.17 (official signed release tarball) ------------------
cp /dl/modsecurity-v3.0.17.tar.gz .
check_sha modsecurity-v3.0.17.tar.gz f283b33d5c21130fd3a15c84a93a1abe12bd1949edaf44288b12af571b671a50
rm -rf ModSecurity modsecurity-v3.0.17 && tar xzf modsecurity-v3.0.17.tar.gz && mv modsecurity-v3.0.17 ModSecurity
(cd ModSecurity && CPPFLAGS="-fPIC" ./configure --with-yajl=$TP --with-maxmind=$TP --disable-shared --enable-static \
   --with-pcre2=$TP --with-curl=$TP --with-libxml=$TP --with-lmdb=$TP --with-lua=$TP --disable-examples 2>&1 | tee $W/modsec-configure.log | tail -40 \
  && make -j$JOBS >/dev/null && cp -r headers/modsecurity $TP/include/ && cp src/.libs/libmodsecurity.a $TP/lib/)
grep -q 'MODSECURITY_PATCHLEVEL "17"' $TP/include/modsecurity/modsecurity.h

# Candidate core headers and corrected upstream 1.9.4 adapter, mounted read-only.
CORE=/candidate-core
check_sha "$CORE/src/modules/modsecurity-ls/mod_security.cpp" 060b125146372543c47414d8649a9fdc5fffca1c54ce9e2c3f6d0b0cffedb177
echo "a969e1bacc9eb842bd88f476654d1c849604b2dfd087656fd701523a123344cc  $CORE/include/ls.h" | sha256sum -c -
# The 3.0.15 artifact's DWARF shows mod_security.cpp compiled standalone (cwd
# third-party/src/ModSecurity, "g++ -g -O2 -std=c++17 -fPIC", no SONAME), not through
# the OLS CMake target (which adds -D_GLIBCXX_USE_CXX11_ABI=0 / gnu++17). Reproduce that.
# libstdc++/libgcc static -> artifact needs only libc/libm/ld-linux, like 3.0.15.
mkdir -p $W/out $W/obj
cd $TP/src/ModSecurity
g++ -g -O2 -std=c++17 -fPIC -I$CORE/include -I$CORE/src -I$TP/include \
    -c $CORE/src/modules/modsecurity-ls/mod_security.cpp -o $W/obj/mod_security.o
g++ -shared -fPIC -g -O2 -o $W/out/mod_security-2.5.6-x86_64-$PLAT.so $W/obj/mod_security.o \
    $TP/lib/libmodsecurity.a -L$TP/lib -llmdb -lxml2 -lcurl -lssl -lcrypto -lz -lpcre2-8 \
    -lyajl -lmaxminddb -lluajit-5.1 -static-libstdc++ -static-libgcc -lpthread -lm -ldl $EXTRA_LIBS
sha256sum $W/out/mod_security-2.5.6-x86_64-$PLAT.so
readelf -d $W/out/mod_security-2.5.6-x86_64-$PLAT.so | grep -E "NEEDED|SONAME"
# Undefined dynamic symbols without a version tag must be the LSI API / weak runtime hooks.
# (readelf, not nm: binutils 2.30 on EL8 nm omits the @GLIBC_x suffix.)
if readelf --dyn-syms -W $W/out/mod_security-2.5.6-x86_64-$PLAT.so | awk '$7=="UND" && $8!="" {print $8}' | grep -v '@' \
   | grep -vxE 'g_api|ls_confparser(_d|_line)?|__cxa_pure_virtual|__gmon_start__|_ITM_.*|OPENSSL_memory_(alloc|free|get_size)|sdallocx|_ZGTtdlPv|_ZGTtnam'; then
  echo "Unexpected unresolved symbols"; exit 1
fi
