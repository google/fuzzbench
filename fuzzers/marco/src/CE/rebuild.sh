#!/bin/bash

sed -i 's/return __builtin_is_constant_evaluated();/return false;/g' /usr/local/include/c++/v1/type_traits
rm -rf /usr/bin/cc

cat <<EOF > /usr/bin/cc
#!/bin/bash

set -euxo pipefail

clang++-6.0 "\$@" -Wl,-L/usr/local/lib -Wl,-l:libc++.a
EOF
chmod +x /usr/bin/cc

CC=clang-6.0 \
CXX=clang++-6.0 \
LD=clang++-6.0 \
AR=llvm-ar-6.0 \
./build/build.sh
