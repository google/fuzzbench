#!/bin/bash
set -e # exit on error

# Build clang & LLVM
LLVM_DEP_PACKAGES="build-essential make cmake ninja-build git binutils-gold binutils-dev curl wget"
apt-get install -y $LLVM_DEP_PACKAGES

UBUNTU_VERSION=`cat /etc/os-release | grep VERSION_ID | cut -d= -f 2`
UBUNTU_YEAR=`echo $UBUNTU_VERSION | cut -d. -f 1`
UBUNTU_MONTH=`echo $UBUNTU_VERSION | cut -d. -f 2`

if [[ "$UBUNTU_YEAR" > "16" || "$UBUNTU_MONTH" > "04" ]]
then
    apt-get install -y python3-distutils
fi

export CXX=g++
export CC=gcc
unset CFLAGS
unset CXXFLAGS

mkdir ~/build; cd ~/build
mkdir llvm_tools; cd llvm_tools
wget https://github.com/llvm/llvm-project/releases/download/llvmorg-11.0.0/llvm-11.0.0.src.tar.xz
wget https://github.com/llvm/llvm-project/releases/download/llvmorg-11.0.0/clang-11.0.0.src.tar.xz
wget https://github.com/llvm/llvm-project/releases/download/llvmorg-11.0.0/compiler-rt-11.0.0.src.tar.xz
wget https://github.com/llvm/llvm-project/releases/download/llvmorg-11.0.0/libcxx-11.0.0.src.tar.xz
wget https://github.com/llvm/llvm-project/releases/download/llvmorg-11.0.0/libcxxabi-11.0.0.src.tar.xz
tar xf llvm-11.0.0.src.tar.xz
tar xf clang-11.0.0.src.tar.xz
tar xf compiler-rt-11.0.0.src.tar.xz
tar xf libcxx-11.0.0.src.tar.xz
tar xf libcxxabi-11.0.0.src.tar.xz
mv clang-11.0.0.src ~/build/llvm_tools/llvm-11.0.0.src/tools/clang
mv compiler-rt-11.0.0.src ~/build/llvm_tools/llvm-11.0.0.src/projects/compiler-rt
mv libcxx-11.0.0.src ~/build/llvm_tools/llvm-11.0.0.src/projects/libcxx
mv libcxxabi-11.0.0.src ~/build/llvm_tools/llvm-11.0.0.src/projects/libcxxabi

mkdir -p build-llvm/llvm; cd build-llvm/llvm
cmake -G "Ninja" \
      -DLIBCXX_ENABLE_SHARED=OFF -DLIBCXX_ENABLE_STATIC_ABI_LIBRARY=ON \
      -DCMAKE_BUILD_TYPE=Release -DLLVM_TARGETS_TO_BUILD="X86" \
      -DLLVM_BINUTILS_INCDIR=/usr/include ~/build/llvm_tools/llvm-11.0.0.src
ninja; ninja install

cd ~/build/llvm_tools
mkdir -p build-llvm/msan; cd build-llvm/msan
cmake -G "Ninja" \
      -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
      -DLLVM_USE_SANITIZER=Memory -DCMAKE_INSTALL_PREFIX=/usr/msan/ \
      -DLIBCXX_ENABLE_SHARED=OFF -DLIBCXX_ENABLE_STATIC_ABI_LIBRARY=ON \
      -DCMAKE_BUILD_TYPE=Release -DLLVM_TARGETS_TO_BUILD="X86" \
       ~/build/llvm_tools/llvm-11.0.0.src
ninja cxx; ninja install-cxx

# Install LLVMgold in bfd-plugins
mkdir -p /usr/lib/bfd-plugins
cp /usr/local/lib/libLTO.so /usr/lib/bfd-plugins
cp /usr/local/lib/LLVMgold.so /usr/lib/bfd-plugins

# install some packages
export LC_ALL=C
apt-get update
apt install -y python-dev python3 python3-dev python3-pip autoconf automake libtool-bin python-bs4 libboost-all-dev # libclang-11.0-dev
python3 -m pip install --upgrade pip
python3 -m pip install networkx pydot pydotplus

export CXX=clang++
export CC=clang
# build AFLGo
cd /afl
make clean all
pushd llvm_mode; make clean all; popd
pushd distance_calculator; cmake -G Ninja ./; cmake --build ./; popd
export AFLGO=/afl
