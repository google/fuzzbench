#!/bin/bash

# e.g. : bash run.sh 0 0 1 objdump
CONF=${1}
TRIAL=${2}
PROGRAM=${3}

do_fifo="1"

sudo apt-get install libprotobuf-dev protobuf-compiler

export AFL_SKIP_CPUFREQ=1
export AFL_NO_AFFINITY=1
export AFL_NO_UI=1
export LD_LIBRARY_PATH=/usr/local/lib
export PATH=$PATH:/usr/local/lib

# cleanup stuff:
rm -rf /tmp/wp2
rm -rf /tmp/wp3
mkfifo /tmp/wp2
mkfifo /tmp/wp3

# for grader & tracer communication
rm -rf /tmp/myfifo
rm -rf /tmp/pcpipe
mkfifo /tmp/myfifo
mkfifo /tmp/pcpipe

rm -rf /dev/shm/sem.fuzzer
rm -rf /dev/shm/sem.ce
rm -rf /dev/shm/sem.grader

declare -A OPT=(
    ["tcpdump"]="-r" \
    ["objdump"]="-D" \
    ["size"]="" \
    ["readelf"]="-a" \
    ["nm-new"]="-C" \
    ["libjpeg_turbo_fuzzer"]="" \
    ["libpng_read_fuzzer"]="" \
    ["xml"]="" \
    ["magic_fuzzer"]="" \
    ["tiffcp"]="" \
    ["tiff_read_rgba_fuzzer"]="" \
    ["x509"]="" \
    ["ossfuzz"]="" \
    ["decode_fuzzer"]="" \
    ["fuzz_dtlsclient"]="" \
    ["ftfuzzer"]="" \
    ["curl_fuzzer_http"]="" \
    ["hb-shape-fuzzer"]="" \
    ["cms_transform_fuzzer"]="" \
    ["standard_fuzzer"]="" \
    ["fuzzer"]="" \
    ["convert_woff2ttf_fuzzer"]="" \
)

declare -A TARGDIR=(
    ["convert_woff2ttf_fuzzer"]="/workdir/targets/woff" \
    ["fuzzer"]="/workdir/targets/re2" \
    ["standard_fuzzer"]="/workdir/targets/proj4" \
    ["cms_transform_fuzzer"]="/workdir/targets/lcms" \
    ["hb-shape-fuzzer"]="/workdir/targets/harfbuzz" \
    ["decode_fuzzer"]="/workdir/targets/vorbis" \
    ["fuzz_dtlsclient"]="/workdir/targets/mbedtls" \
    ["tcpdump"]="/workdir/targets/tcpdump-4.99.1" \
    ["objdump"]="/workdir/targets/binutils" \
    ["size"]="/workdir/targets/binutils" \
    ["readelf"]="/workdir/targets/binutils" \
    ["nm-new"]="/workdir/targets/binutils" \
    ["libjpeg_turbo_fuzzer"]="/workdir/targets/libjpeg-turbo" \
    ["libpng_read_fuzzer"]="/workdir/targets/libpng-1.2.56" \
    ["xml"]="/workdir/targets/libxml2-v2.9.2" \
    ["magic_fuzzer"]="/workdir/targets/file" \
    ["tiffcp"]="/workdir/targets/libtiff" \
    ["tiff_read_rgba_fuzzer"]="/workdir/targets/libtiff" \
    ["x509"]="/workdir/targets/openssl" \
    ["ossfuzz"]="/workdir/targets/sqlite3" \
    ["ftfuzzer"]="/workdir/targets/freetype" \
    ["curl_fuzzer_http"]="/workdir/targets/curl" \
)

OUT="/outroot"
INPUT="/workdir/input"

SEEDDIR="${TARGDIR[${PROGRAM}]}/seed"

if [ -d "$OUT" ]; then
    rm -rf $OUT/*
fi

cd $OUT


mkdir tmpin
tmpcount=0
for oldname in $SEEDDIR/* ; do
    newname=$(printf "id:%06d,orig\n" $tmpcount)
    cp $oldname /outroot/tmpin/$newname
    tmpcount=$((tmpcount+1))
done
SEEDDIR="/outroot/tmpin/"

# pure fuzz
if [ "$CONF" == "10" ]; then
    mkdir aflin
    cp $SEEDDIR/* aflin/
# CE in the house
else
    mkdir -p tree
    mkdir -p tree0
    mkdir -p tree1
    mkdir -p deps
    mkdir -p ce_output/queue
    mkdir -p fifo/queue
    mkdir -p afl-slave/queue
    mkdir -p pcsets

    cp $SEEDDIR/* afl-slave/queue/

    # use marco scheduler
    cp /data/src/scheduler/main.py ./
fi



# symsan; use original CE - brc policy
if [ "$CONF" == "0" ]; then
    cp /data/src/CE_ori/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_ori/${PROGRAM}"
    USEPP="0"
    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log
    else
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" @@  &> run_ce.log
    fi
fi

if [ "$CONF" == "1" ]; then
    cp /data/src/CE_ori/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_ori/${PROGRAM}"
    USEPP="1"
    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log
    else
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" @@  &> run_ce.log
    fi
fi


if [ "$CONF" == "2" ]; then
    cp /data/src/CE_new/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_ori/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log
    else
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" @@  &> run_ce.log
    fi
fi


if [ "$CONF" == "3" ]; then
    cp /data/src/CE/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log &
    else
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" @@  &> run_ce.log &
    fi

    python3.7 main.py -d 0 -m 1 &> debug.log

fi


if [ "$CONF" == "4" ]; then
    cp /data/src/CE/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log &
    else
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" @@  &> run_ce.log &
    fi

    python3.7 main.py -d 0 -m 3 &> debug.log

fi


if [ "$CONF" == "5" ]; then
    cp /data/src/CE/target/release/fastgen ./

    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log &
    else
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" @@  &> run_ce.log &
    fi

    python3.7 main.py -d 0 -m 2 &> debug.log
fi



if [ "$CONF" == "20" ]; then
    cp /data/src/CE/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log &
    else
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" @@  &> run_ce.log &
    fi

    python3.7 main.py -d 0 -m 4 &> debug.log
fi 

if [ "$CONF" == "21" ]; then
    cp /data/src/CE/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log &
    else
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c 0 -- "$CE_TARG" @@  &> run_ce.log &
    fi

    python3.7 main.py -d 0 -m 5 &> debug.log
fi 