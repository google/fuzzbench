#!/bin/bash

# e.g. : bash run.sh 0 0 1 objdump
CONF=${1}
TRIAL=${2}
# USEPP=${3}
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
if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
    # SEEDDIR="${TARGDIR[${PROGRAM}]}/seed_${PROGRAM}"
    SEEDDIR="${TARGDIR[${PROGRAM}]}/seed"
else
    SEEDDIR="${TARGDIR[${PROGRAM}]}/seed"
fi

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



if [ "$CONF" == "10" ]; then
    mkdir aflin
    cp $SEEDDIR/* aflin/
else
    mkdir -p tree
    mkdir -p tree0
    mkdir -p tree1
    mkdir -p deps
    mkdir -p ce_output/queue
    mkdir -p fifo/queue
    mkdir -p afl-slave/queue
    mkdir -p pcsets

    # prep the initial corpus
    if [[ "$CONF" == "18" || "$CONF" == "19" || "$CONF" == "20" || "$CONF" == "30" ]]; then
        mkdir aflin
        cp $SEEDDIR/* aflin/
    else
        cp $SEEDDIR/* afl-slave/queue/
        # cp $SEEDDIR/* fifo/queue/ # conf4 only?
    fi

    INITCOUNT=$(ls fifo/queue/ | wc -l)

    # prep the /outroot for trials
    cp /data/src/scheduler/main.py ./
fi

if [[ "$CONF" == "18" || "$CONF" == "30" ]]; then
    # fuzzer setup
    cp /data/src/AFLplusplus/afl-fuzz ./
    FZ_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_afl/${PROGRAM}"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-slave  -i ./aflin -o ./ -- "$FZ_TARG" "${OPT[${PROGRAM}]}" @@ &
    else
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-slave  -i ./aflin -o ./ -- "$FZ_TARG" @@ &
    fi
    # cp /workdir/testinput/* afl-slave/queue/

    # use full-fledged CE; 1: only unvisited; 2: all; pp policy
    cp /data/src/CE/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log &
    else
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" @@  &> run_ce.log &
    fi

    if [ "$CONF" == "18" ]; then
        python3.7 main.py -m 2 -i $INITCOUNT &> debug.log
    else 
        python3.7 main.py -d 1 -m 2 -i $INITCOUNT &> debug.log
    fi 
fi

if [ "$CONF" == "19" ]; then
    # pure fuzzing of 3 instances
    cp /data/src/AFLplusplus/afl-fuzz ./
    FZ_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_afl/${PROGRAM}"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        AFL_NO_AFFINITY=1 ./afl-fuzz -M afl-master -i ./aflin -o ./ -- "$FZ_TARG" "${OPT[${PROGRAM}]}" @@ &
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-slave  -i ./aflin -o ./ -- "$FZ_TARG" "${OPT[${PROGRAM}]}" @@ &
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-secondary  -i ./aflin -o ./ -- "$FZ_TARG" "${OPT[${PROGRAM}]}" @@

    else
        AFL_NO_AFFINITY=1 ./afl-fuzz -M afl-master -i ./aflin -o ./ -- "$FZ_TARG" @@ &
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-slave  -i ./aflin -o ./ -- "$FZ_TARG" @@ &
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-secondary  -i ./aflin -o ./ -- "$FZ_TARG" @@
    fi
fi

if [ "$CONF" == "20" ]; then
    # use original CE - brc policy with an afl-slave instance and a master node 

    # fuzzer setup
    cp /data/src/AFLplusplus/afl-fuzz ./
    FZ_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_afl/${PROGRAM}"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        AFL_NO_AFFINITY=1 ./afl-fuzz -M afl-master -i ./aflin -o ./ -- "$FZ_TARG" "${OPT[${PROGRAM}]}" @@ &
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-slave  -i ./aflin -o ./ -- "$FZ_TARG" "${OPT[${PROGRAM}]}" @@ &
    else
        AFL_NO_AFFINITY=1 ./afl-fuzz -M afl-master  -i ./aflin -o ./ -- "$FZ_TARG" @@ &
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-slave  -i ./aflin -o ./ -- "$FZ_TARG" @@ &
    fi

    # QSYM CE
    cp /data/src/CE_ori/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_ori/${PROGRAM}"
    USEPP="0"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log
    else
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" @@  &> run_ce.log
    fi

fi


if [ "$CONF" == "10" ]; then
    cp /data/src/AFLplusplus/afl-fuzz ./
    FZ_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_afl/${PROGRAM}"
    cp -r fifo/queue ./aflin
    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-slave1  -i ./aflin -o ./ -- "$FZ_TARG" "${OPT[${PROGRAM}]}" @@
    else
        AFL_NO_AFFINITY=1 ./afl-fuzz -S afl-slave1  -i ./aflin -o ./ -- "$FZ_TARG" @@
    fi
fi

# redis-server &
# -----------------------

if [ "$CONF" == "0" ]; then
    # use original CE - brc policy
    cp /data/src/CE_ori/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_ori/${PROGRAM}"
    USEPP="0"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log
    else
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" @@  &> run_ce.log
    fi
fi

if [[ "$CONF" == "1"  ||  "$CONF" == "2"  ||  "$CONF" == "5" || "$CONF" == "6" || "$CONF" == "7" || "$CONF" == "8" || "$CONF" == "16" || "$CONF" == "21" ]]; then

    # use full-fledged CE; 1: only unvisited; 2: all; pp policy
    cp /data/src/CE/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then

        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log &
    else
        LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libprotobuf.so.10" RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" @@  &> run_ce.log &
    fi

    if [ "$CONF" == "5" ]; then
        python3.7 main.py -m 2 -i $INITCOUNT -e 1 &> debug.log
    elif [ "$CONF" == "6" ]; then
        python3.7 main.py -m 2 -i $INITCOUNT &> debug.log
    elif [ "$CONF" == "8" || "$CONF" == "16" || "$CONF" == "21" ]; then
        python3.7 main.py -m 2 -i $INITCOUNT &> debug.log
    elif [ "$CONF" == "1" ]; then
        python3.7 main.py -m 1 -i $INITCOUNT &> debug.log
    elif [ "$CONF" == "7" ]; then
        python3.7 main.py -m 2 -i $INITCOUNT &> debug.log
    else
        python3.7 main.py -m $CONF -i $INITCOUNT &> debug.log
    fi
fi

if [ "$CONF" == "3" ]; then

    # use full-fledged CE; brc policy
    cp /data/src/CE/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets/${PROGRAM}"
    USEPP="0"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log &
    else
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" @@  &> run_ce.log &
    fi
    python3.7 main.py -m 2 -i $INITCOUNT &> debug.log
fi


if [ "$CONF" == "17" ]; then

    # use original CE - our policy
    cp /data/src/CE_new/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_ori/${PROGRAM}"
    USEPP="1"
    # USEPP=1 actually will be our policy

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log
    else
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" @@  &> run_ce.log
    fi
fi


if [ "$CONF" == "4" ]; then

    # use original CE - pp policy
    cp /data/src/CE_ori/target/release/fastgen ./
    CE_TARG="${TARGDIR[${PROGRAM}]}/ce_targets_ori/${PROGRAM}"
    USEPP="1"

    if [ "$PROGRAM" == "objdump" -o "$PROGRAM" == "size" -o "$PROGRAM" == "nm-new" -o "$PROGRAM" == "readelf" -o "$PROGRAM" == "tcpdump" ]; then
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" "${OPT[${PROGRAM}]}" @@  &> run_ce.log
    else
        RUST_BACKTRACE=1 RUST_LOG=info ./fastgen --sync_afl -i "$INPUT" -o "$OUT" -t "$CE_TARG" -b "$USEPP" -f "$do_fifo" -c "$INITCOUNT" -- "$CE_TARG" @@  &> run_ce.log
    fi
fi

