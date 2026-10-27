#!/bin/bash
set -euo pipefail
test -f /.dockerenv || { echo "Run only inside the disposable EL8 builder" >&2; exit 1; }
cd /work
mkdir -p build evidence artifacts
printf '%s  %s\n' dd54693aa334c5c4d72e9aee96b082c2473750a18a6c1d105789c93a3b1692fd downloads/php-8.3.36.tar.xz | sha256sum -c -
expected=603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a
printf '%s  %s\n' "$expected" downloads/openssl-3.5.9.tar.gz | sha256sum -c -
printf '%s  %s\n' 78262a6e7ac170d6528ebfe2efccdf220191a5af6a6cd61ea4a9a9a5042c7a07 downloads/libxml2-2.15.3.tar.xz | sha256sum -c -
dnf -y install gcc make perl-core pkgconf-pkg-config tar xz bison diffutils findutils > evidence/build-packages.log 2>&1
cd build
prefix=/work/build/deps
tar -xf ../downloads/openssl-3.5.9.tar.gz
cd openssl-3.5.9
./Configure linux-x86_64 no-shared no-module no-tests --prefix="$prefix" --libdir=lib --openssldir=/etc/ssl > /work/evidence/openssl-configure.log 2>&1
make -j4 > /work/evidence/openssl-make.log 2>&1
make install_sw > /work/evidence/openssl-install.log 2>&1
cd ..
tar -xf ../downloads/libxml2-2.15.3.tar.xz
cd libxml2-2.15.3
./configure --prefix="$prefix" --disable-shared --enable-static --without-python --without-zlib --without-lzma --without-readline --without-history > /work/evidence/libxml-configure.log 2>&1
make -j4 > /work/evidence/libxml-make.log 2>&1
make install > /work/evidence/libxml-install.log 2>&1
cd ..
tar -xf ../downloads/php-8.3.36.tar.xz
cd php-8.3.36
export PKG_CONFIG_PATH="$prefix/lib/pkgconfig"
export CPPFLAGS="-I$prefix/include"
export LDFLAGS="-L$prefix/lib"
./configure --prefix=/usr/local/lsws/admin/cyberpanel-php --with-config-file-path=/usr/local/lsws/admin/cyberpanel-php/etc --with-config-file-scan-dir=/usr/local/lsws/admin/cyberpanel-php/etc/php.d --disable-all --enable-cli --disable-cgi --enable-litespeed --enable-session --enable-posix --enable-xml --enable-dom --with-libxml --enable-sockets --enable-bcmath --enable-filter --enable-ctype --with-openssl --disable-opcache > /work/evidence/php-configure.log 2>&1
make -j4 > /work/evidence/php-make.log 2>&1
cp sapi/litespeed/lsphp /work/artifacts/admin_php-8.3.36-cp1-x86_64
strip /work/artifacts/admin_php-8.3.36-cp1-x86_64
chmod 755 /work/artifacts/admin_php-8.3.36-cp1-x86_64
ldd /work/artifacts/admin_php-8.3.36-cp1-x86_64 > /work/evidence/admin-ldd.txt
sha256sum /work/artifacts/admin_php-8.3.36-cp1-x86_64 > /work/artifacts/admin_php-8.3.36-cp1-x86_64.sha256
