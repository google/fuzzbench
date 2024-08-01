rm -rf  corpus
#HEAPCHECK=normal LD_PRELOAD="/usr/local/lib/libtcmalloc.so" RUST_LOG=info ../target/debug/fastgen -i input -o output -t ./objdump.track -- ./objdump.fast -D @@
pro=$1
opt=$2
LD_PRELOAD="/usr/local/lib/libtcmalloc.so" RUST_LOG=info ../target/release/fastgen --sync_afl -i input_${pro} -o corpus -t ./${pro}.track -- ./${pro}.fast ${opt} @@
