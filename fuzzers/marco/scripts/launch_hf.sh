#!/bin/bash
# ./launch_hf.sh 1024-1 0
# ./launch_hf.sh 1128-1 42
# ./launch_hf.sh 1129-1 42
# ./launch_hf.sh 0202-1 0
# OROOT="/home/jie/proj-reach/exp-hf/outroot${1}"
OROOT="/hyper/jie/hfexp/outroot${1}"
CPU_COUNT=${2}

start=0
end=2

mkdir -p "$OROOT"
DKIMG="coco_design2"
TOUT="12h"

declare -a TARG=(
    "objdump" \
    "nm-new" \
    "size" \
    "readelf" \
    # "magic_fuzzer" \
    "libjpeg_turbo_fuzzer" \
    # "libpng_read_fuzzer" \
    "ossfuzz" \
    # "tcpdump" \
    # "decode_fuzzer" \
)

declare -A CONF=(
    ["18"]="hybridfuzz" \
    ["19"]="purefuzz" \
    ["20"]="hybridqsym" \
    ["30"]="hybridnew" \
)

for PROGRAM in "${TARG[@]}"; do
    echo "$PROGRAM"
    for CONFN in "18" "19" "20" "30" ; do
        CONFIG="${CONF[${CONFN}]}"
        TRIAL=$start
        while [ $TRIAL -ne $end ]; do
            DOCKERNAME="${DKIMG}_${PROGRAM}_conf${CONFN}_${TRIAL}_${1}"
            DATADIR="$OROOT/conf${CONFN}_${PROGRAM}_${TRIAL}"
            echo ${CPU_COUNT} $TOUT $CONFIG $TRIAL $PROGRAM $DOCKERNAME $DATADIR
            docker stop $DOCKERNAME
            docker rm $DOCKERNAME

            sudo rm -rf $DATADIR
            mkdir -p $DATADIR

            docker run --ulimit core=0 -d --name $DOCKERNAME \
                    --cpuset-cpus "${CPU_COUNT}" \
                    -v $DATADIR:/outroot \
                    -v `pwd`/exp-hf/afl-slave/queue:/workdir/testinput \
                    -v `pwd`/src/benchmarks/targets:/workdir/targets \
                    -v `pwd`/src/CE:/data/src/CE \
                    -v `pwd`/src/AFLplusplus:/data/src/AFLplusplus \
                    -v `pwd`/src/CE_ori:/data/src/CE_ori \
                    -v `pwd`/src/CE_new:/data/src/CE_new \
                    -v `pwd`/src/scheduler/main.py:/data/src/scheduler/main.py \
                    -v `pwd`/runall.sh:/workdir/run.sh \
                    -v `pwd`/small_exec.elf:/workdir/small_exec.elf \
                    $DKIMG timeout $TOUT /bin/bash run.sh $CONFN $TRIAL $PROGRAM
                    # "${TOUTS[${PROGRAM}]}"

            TRIAL=$(($TRIAL+1))
            CPU_COUNT=$((CPU_COUNT+1))
        done
        echo ""
    done
done