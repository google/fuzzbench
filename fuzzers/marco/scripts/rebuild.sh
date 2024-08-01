#!/bin/bash
# --------------------------- libpng ---------------------------
# if [ ! -d "./libpng-1.2.56" ]; then
#     wget https://downloads.sourceforge.net/project/libpng/libpng12/older-releases/1.2.56/libpng-1.2.56.tar.gz
#     tar -xvf libpng-1.2.56.tar.gz
#     cp -r libpng-1.2.56 libpng-1.2.56_cov
#     rm libpng-1.2.56.tar.gz
# fi
# pushd libpng-1.2.56
#     cp ../targets/libpng-1.2.56/build.sh ./build.sh
#     bash build.sh
#     bash build.sh _ori
# popd

# pushd libpng-1.2.56_ori
#     cp ../targets/libpng-1.2.56/build_cov.sh ./build_cov.sh
#     bash build_cov.sh
# popd


# --------------------------- libjpeg ---------------------------
# if [ ! -d "./libjpeg-turbo" ]; then
#     git clone https://github.com/libjpeg-turbo/libjpeg-turbo.git
# fi

# if [ ! -d "./libjpeg-turbo_cov" ]; then
#     git clone https://github.com/libjpeg-turbo/libjpeg-turbo.git libjpeg-turbo_cov
# fi
# pushd libjpeg-turbo
#     cp ../targets/libjpeg-turbo/build.sh ./build.sh
#     bash build.sh
#     bash build.sh _ori
# popd

# pushd libjpeg-turbo_cov
#     cp ../targets/libjpeg-turbo/build_cov.sh ./build_cov.sh
#     bash build_cov.sh
# popd

# --------------------------- libxml2 ---------------------------
# git clone https://gitlab.gnome.org/GNOME/libxml2.git libxml2-v2.9.2_ori
# cd libxml2-v2.9.2
# git checkout -f v2.9.2
# cd ../
# cp -r libxml2-v2.9.2 libxml2-v2.9.2_cov
# cp -r libxml2-v2.9.2 libxml2-v2.9.2_ori
# pushd libxml2-v2.9.2
#     cp ../targets/libxml2-v2.9.2/build.sh ./build.sh
#     bash build.sh
#     bash build.sh _ori
# popd
# pushd libxml2-v2.9.2_cov
#     cp ../targets/libxml2-v2.9.2/build_cov.sh ./build_cov.sh
#     bash build_cov.sh
# popd


# ----- file -----
# git clone https://github.com/file/file.git file
# pushd file
#     git checkout FILE5_42
# popd

# ----tiff2pdf ---
# git clone --no-checkout https://gitlab.com/libtiff/libtiff.git libtiff
# git -C libtiff checkout 2e822691d750c01cec5b5cc4ee73567a204ab2a3


# --- openssl ----
# git clone --depth 1 https://github.com/openssl/openssl.git openssl
# cp -r openssl openssl_cov
# cp -r openssl openssl_ori

# ---- sqlite3 ----
# apt-get update && apt-get install -y make autoconf automake libtool curl tcl zlib1g-dev

# mkdir sqlite3
# cd sqlite3
# curl 'https://sqlite.org/src/tarball/sqlite.tar.gz?r=c78cbf2e86850cc6' -o sqlite3.tar.gz && \
#         tar xzf sqlite3.tar.gz --strip-components 1


# tcpdump
# wget https://www.tcpdump.org/release/tcpdump-4.99.1.tar.gz
# git clone https://github.com/the-tcpdump-group/libpcap.git

# vorbis 
# git clone https://github.com/xiph/ogg.git
# git clone https://github.com/xiph/vorbis.git
# wget -qO ./decode_fuzzer.cc https://raw.githubusercontent.com/google/oss-fuzz/688aadaf44499ddada755562109e5ca5eb3c5662/projects/vorbis/decode_fuzzer.cc


# mbedtls
# git clone --recursive --depth 1 https://github.com/ARMmbed/mbedtls.git mbedtls
# git clone --depth 1 https://github.com/google/boringssl.git boringssl
# git clone --depth 1 https://github.com/openssl/openssl.git openssl
# git clone https://github.com/ARMmbed/mbed-crypto mbedtls/crypto

# curl 
# git clone --depth 1 https://github.com/curl/curl.git curl
# git clone https://github.com/curl/curl-fuzzer.git curl_fuzzer
# git -C curl_fuzzer checkout -f 9a48d437484b5ad5f2a97c0cab0d8bcbb5d058de


# freetype  - change the zlib version 11->12 . nolzma
# # git clone git://git.sv.nongnu.org/freetype/freetype2.git
# git clone https://skia.googlesource.com/third_party/freetype2
# git clone https://github.com/unicode-org/text-rendering-tests.git TRT
# wget https://github.com/libarchive/libarchive/releases/download/v3.4.3/libarchive-3.4.3.tar.xz


# harfbuzz
# git clone https://github.com/behdad/harfbuzz.git

# lcms
# git clone https://github.com/mm2/Little-CMS.git
# copy the cms_transform_fuzzer.cc file from fuzzbench folder 


# proj4
# git clone https://github.com/OSGeo/PROJ

# re2 
# git clone https://github.com/google/re2.git

# woff 
# git clone https://github.com/google/woff2.git
# git clone https://github.com/google/brotli.git
# git clone https://github.com/google/oss-fuzz.git

# libxslt 
# git clone --depth 1 https://gitlab.gnome.org/GNOME/libxml2.git
# git clone --depth 1 https://gitlab.gnome.org/GNOME/libxslt.git

# openthread
# git clone https://github.com/openthread/openthread.git

# php
# mkdir php 
# cd php
# git clone --no-checkout https://github.com/php/php-src.git 
# git -C php-src checkout 39532f9c52ef39c629deab3a30c1e56612387396

# git clone --no-checkout https://github.com/kkos/oniguruma.git
# git -C oniguruma checkout 7c190e81397b7c37ec0e899df10be04a8eec5d4b


# poppler 
# mkdir poppler 
# cd poppler 
# git clone --no-checkout https://gitlab.freedesktop.org/poppler/poppler.git
# git -C poppler checkout 2706eca3ad3af99fa6551b9d6fcdc69eb0a0aa4e

# # git clone --no-checkout git://git.sv.nongnu.org/freetype/freetype2.git 
# git clone https://skia.googlesource.com/third_party/freetype2
# git -C freetype2 checkout 804e625def2cfb64ef2f4c8877cd3fa11e86e208

# lua:
# git clone --no-checkout https://github.com/lua/lua.git 
# git -C lua checkout dbdc74dc5502c2e05e1c1e2ac894943f418c8431